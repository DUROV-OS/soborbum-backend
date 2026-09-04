import io

from fastapi import HTTPException, UploadFile, status
from openpyxl import Workbook, load_workbook

TEMPLATE_HEADERS = [
    "ID материала (если уже есть на складе)",
    "Тип",
    "Размер",
    "Название",
    "Единица измерения",
    "Количество поставки",
]


def generate_template() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Поставка"
    ws.append(TEMPLATE_HEADERS)
    ws.append([None, "Доска", "150x50x6000", "Доска обрезная", "шт", 100])
    ws.append([1, None, None, None, None, 50])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def parse_supply_rows(file: UploadFile) -> list[dict]:
    try:
        content = file.file.read()
        wb = load_workbook(filename=io.BytesIO(content), data_only=True)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не удалось прочитать excel-файл")

    ws = wb.active
    rows: list[dict] = []
    for idx, row in enumerate(ws.iter_rows(min_row=2, max_col=6, values_only=True), start=2):
        if row is None or all(v is None for v in row):
            continue
        material_id, material_type, size, title, unit, quantity = (list(row) + [None] * 6)[:6]
        if quantity is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Строка {idx}: не указано количество")
        if material_id in (None, ""):
            if not title:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Строка {idx}: для нового материала нужно указать название",
                )
        rows.append(
            {
                "warehouse_material_id": int(material_id) if material_id not in (None, "") else None,
                "material_type": material_type,
                "size": size,
                "title": title,
                "unit": unit,
                "quantity": float(quantity),
            }
        )
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="В файле нет ни одной строки с данными")
    return rows
