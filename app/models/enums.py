import enum


class Module(str, enum.Enum):
    CLIENTS = "clients"
    PRODUCTION = "production"
    INSTALLATION = "installation"
    CYCLE = "cycle"
    WAREHOUSE = "warehouse"
    MARKETING = "marketing"
    TASKS = "tasks"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    WORKER = "worker"


class CycleStatus(str, enum.Enum):
    CLIENT = "client"
    PRODUCTION = "production"
    INSTALLATION = "installation"
    COMPLETED = "completed"


class ClientStage(str, enum.Enum):
    LEAD = "lead"
    DISCUSSION = "discussion"
    APPROVAL = "approval"
    PAYMENT = "payment"
    POSTPAYMENT = "postpayment"


CLIENT_STAGE_ORDER = [
    ClientStage.LEAD,
    ClientStage.DISCUSSION,
    ClientStage.APPROVAL,
    ClientStage.PAYMENT,
    ClientStage.POSTPAYMENT,
]


class InstallationStage(str, enum.Enum):
    DELIVERY = "delivery"
    INSTALLATION = "installation"
    FOLLOWUP = "followup"


INSTALLATION_STAGE_ORDER = [
    InstallationStage.DELIVERY,
    InstallationStage.INSTALLATION,
    InstallationStage.FOLLOWUP,
]


class ContentStage(str, enum.Enum):
    IDEA = "idea"
    GATHERING = "gathering"
    EDITING = "editing"
    RELEASE = "release"
    ANALYSIS = "analysis"


CONTENT_STAGE_ORDER = [
    ContentStage.IDEA,
    ContentStage.GATHERING,
    ContentStage.EDITING,
    ContentStage.RELEASE,
    ContentStage.ANALYSIS,
]


class TaskStatus(str, enum.Enum):
    NOT_READY = "not_ready"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class TaskLinkType(str, enum.Enum):
    NONE = "none"
    CLIENT_STAGE = "client_stage"
    CONTENT_STAGE = "content_stage"
    WAREHOUSE_REQUEST = "warehouse_request"
    WAREHOUSE_SHORTAGE = "warehouse_shortage"


class MaterialRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class StockMovementReason(str, enum.Enum):
    SUPPLY = "supply"
    ISSUED = "issued"
    REQUIRED_ADJUSTED_UP = "required_adjusted_up"
    REQUEST_REJECTED_RETURN = "request_rejected_return"
    MANUAL_ADJUST = "manual_adjust"


class FilePurpose(str, enum.Enum):
    CONTRACT = "contract"
    HOUSE_PROJECT = "house_project"
    TASK_IMAGE = "task_image"
    MARKETING_RAW = "marketing_raw"
    MARKETING_FINAL = "marketing_final"
