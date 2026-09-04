"""Generates the initial "Совет директоров" tree. Idempotent by design (skips
if a root node already exists), so it's safe to call unconditionally from
app.main's startup hook the same way app.users.service.bootstrap_admin is:
it actually does something exactly once, right after the first deploy, and
is a no-op on every restart after that. Nothing here is AI-authored - it's a
fixed starting point for the tree; the council and "актуализировать" take it
from here.
"""

from sqlalchemy.orm import Session

from app.board.models import BoardNode, BoardNodeColor

ROOT_TITLE = "durov.house"
ROOT_DESCRIPTION = (
    "Компания строит и продаёт модульные дома, развивает собственные туристические базы и "
    "сопутствующие направления бизнеса. Здесь собраны стратегические направления развития и текущее "
    "положение дел по каждому из них."
)

# (title, description, color, [(sub_title, sub_description, sub_color), ...])
DIRECTIONS: list[tuple[str, str, BoardNodeColor, list[tuple[str, str, BoardNodeColor]]]] = [
    (
        "Маркетинг",
        "Продвижение компании и привлечение клиентов через контент и мероприятия.",
        BoardNodeColor.GREEN,
        [
            ("Инстаграм", "Общий подход к контенту в Instagram: формат, регулярность, тон общения.", BoardNodeColor.GREEN),
            ("Телеграм", "Ведение канала и чатов компании в Telegram.", BoardNodeColor.GREEN),
            ("Макс", "Присутствие компании в мессенджере MAX.", BoardNodeColor.YELLOW),
            ("Розыгрыши", "Проведение конкурсов и розыгрышей для привлечения внимания к бренду.", BoardNodeColor.GREEN),
            ("Выставки и мероприятия", "Участие в отраслевых выставках и собственные офлайн-мероприятия.", BoardNodeColor.GREEN),
        ],
    ),
    (
        "Производство",
        "Изготовление модульных домов: мощности, процессы, качество.",
        BoardNodeColor.GREEN,
        [
            ("Мощности", "Текущая производственная мощность и её загрузка.", BoardNodeColor.GREEN),
            ("Качество", "Контроль качества модулей и материалов.", BoardNodeColor.GREEN),
            ("Поставщики", "Работа с поставщиками материалов и комплектующих.", BoardNodeColor.YELLOW),
        ],
    ),
    (
        "Тур-базы",
        "Собственные туристические базы компании: эксплуатация и развитие.",
        BoardNodeColor.YELLOW,
        [
            ("Действующие объекты", "Текущее состояние и загрузка уже открытых тур-баз.", BoardNodeColor.GREEN),
            ("Новые объекты", "Планы по открытию новых туристических баз.", BoardNodeColor.YELLOW),
        ],
    ),
    (
        "Новые рынки",
        "Необходимость и приоритетность выхода компании на другие рынки (регионы, страны, сегменты).",
        BoardNodeColor.YELLOW,
        [
            ("Регионы РФ", "Приоритетность выхода в новые регионы России.", BoardNodeColor.YELLOW),
            ("Зарубежные рынки", "Оценка перспектив выхода за рубеж.", BoardNodeColor.RED),
        ],
    ),
]


def ensure_seed(db: Session) -> BoardNode | None:
    """Creates the initial tree if the board is empty. Returns the root node
    if it just created one, None if the board already had a root (i.e. this
    already ran before, or the tree was populated some other way)."""
    if db.query(BoardNode).filter(BoardNode.parent_id.is_(None)).first() is not None:
        return None

    root = BoardNode(parent_id=None, level=0, sort_order=0, title=ROOT_TITLE, description=ROOT_DESCRIPTION, color=BoardNodeColor.GREEN)
    db.add(root)
    db.flush()

    for i, (title, description, color, subdirections) in enumerate(DIRECTIONS):
        direction = BoardNode(
            parent_id=root.id, level=1, sort_order=i, title=title, description=description, color=color,
        )
        db.add(direction)
        db.flush()

        for j, (sub_title, sub_description, sub_color) in enumerate(subdirections):
            db.add(
                BoardNode(
                    parent_id=direction.id, level=2, sort_order=j,
                    title=sub_title, description=sub_description, color=sub_color,
                )
            )

    db.commit()
    db.refresh(root)
    return root
