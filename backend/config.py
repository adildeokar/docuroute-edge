"""
config.py - Central configuration for the Edge Document Classification & Routing System.

Everything that you might want to tweak (folders, thresholds, departments) lives here,
so the rest of the code stays clean and easy to explain.
"""
import os
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BACKEND_DIR)

load_dotenv(os.path.join(BACKEND_DIR, ".env"))

# Runtime data (history DB, uploads, routed folders). Can be overridden for tests.
DATA_DIR = os.environ.get("EDGE_DATA_DIR", os.path.join(PROJECT_DIR, "data"))
DATASET_DIR = os.path.join(PROJECT_DIR, "data", "dataset")          # training corpus
DATASET_CSV = os.path.join(DATASET_DIR, "documents.csv")
OCR_TEST_DIR = os.path.join(DATASET_DIR, "ocr_test_images")         # held-out scanned images
MODEL_DIR = os.path.join(PROJECT_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "document_classifier.joblib")
METRICS_PATH = os.path.join(MODEL_DIR, "metrics.json")
SAMPLES_DIR = os.path.join(PROJECT_DIR, "sample_documents")         # demo files for the jury
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
REPORTS_DIR = os.path.join(PROJECT_DIR, "reports")

UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
ROUTED_DIR = os.path.join(DATA_DIR, "routed")
DB_PATH = os.path.join(DATA_DIR, "history.db")

# ---------------------------------------------------------------------------
# Edge service settings
# ---------------------------------------------------------------------------
HOST = os.environ.get("EDGE_HOST", "0.0.0.0")
PORT = int(os.environ.get("EDGE_PORT", 5000))
MAX_UPLOAD_MB = 15
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp", "pdf", "txt", "docx"}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp"}

# ---------------------------------------------------------------------------
# Decision thresholds
# ---------------------------------------------------------------------------
CONFIDENCE_THRESHOLD = 0.70   # below this -> "needs review" (sent to Manual Review desk)
MIN_TEXT_CHARS = 25           # less readable text than this -> blank / non-document
MIN_KNOWN_WORD_RATIO = 0.35   # share of words the model has seen before (out-of-domain check)
LOW_OCR_QUALITY = 0.75        # average OCR confidence below this -> "poor scan" warning

# ---------------------------------------------------------------------------
# Optional cloud AI assistant (OpenAI). Core classification never needs it.
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
AI_ENABLED = bool(OPENAI_API_KEY)

# ---------------------------------------------------------------------------
# Document categories  ->  departments (routing table)
# ---------------------------------------------------------------------------
CATEGORIES = {
    "invoice": {
        "label": "Invoice",
        "department": "Finance - Accounts Payable",
        "folder": "Finance_Accounts_Payable",
        "color": "#2a78d6",
        "color_dark": "#3987e5",
        "description": "Vendor bills that must be verified and paid.",
    },
    "receipt": {
        "label": "Receipt",
        "department": "Finance - Expense Claims",
        "folder": "Finance_Expense_Claims",
        "color": "#eb6834",
        "color_dark": "#d95926",
        "description": "Proof of payment submitted for reimbursement.",
    },
    "identity_document": {
        "label": "Identity Document",
        "department": "HR - KYC & Verification",
        "folder": "HR_KYC_Verification",
        "color": "#1baf7a",
        "color_dark": "#199e70",
        "description": "Passports, licences and ID cards (restricted access).",
    },
    "application_form": {
        "label": "Application Form",
        "department": "Admissions & Applications Desk",
        "folder": "Applications_Desk",
        "color": "#eda100",
        "color_dark": "#c98500",
        "description": "Admission, loan, job and membership applications.",
    },
    "bank_statement": {
        "label": "Bank Statement",
        "department": "Finance - Accounts & Audit",
        "folder": "Finance_Accounts_Audit",
        "color": "#e87ba4",
        "color_dark": "#d55181",
        "description": "Account statements used for audit and reconciliation.",
    },
    "medical_report": {
        "label": "Medical Report",
        "department": "Health & Insurance Claims",
        "folder": "Health_Insurance_Claims",
        "color": "#008300",
        "color_dark": "#0ca30c",
        "description": "Lab reports, prescriptions and discharge summaries.",
    },
    "resume": {
        "label": "Resume / CV",
        "department": "HR - Recruitment",
        "folder": "HR_Recruitment",
        "color": "#6250d6",
        "color_dark": "#9085e9",
        "description": "Candidate CVs for open positions.",
    },
    "legal_contract": {
        "label": "Legal Contract",
        "department": "Legal & Compliance",
        "folder": "Legal_Compliance",
        "color": "#e34948",
        "color_dark": "#e66767",
        "description": "Agreements, NDAs and contracts for legal review.",
    },
}

# Fallback destination when the model is not sure or the input is not a document.
UNKNOWN_CATEGORY = "unknown"
MANUAL_REVIEW = {
    "label": "Unclassified",
    "department": "Manual Review Desk",
    "folder": "Manual_Review",
    "color": "#64748b",
    "color_dark": "#94a3b8",
    "description": "Low-confidence or unreadable documents checked by a human.",
}


def category_info(category):
    """Return label/department/folder/color for a category (or the manual review desk)."""
    return CATEGORIES.get(category, MANUAL_REVIEW)


def ensure_dirs():
    """Create all runtime folders (called once at start-up)."""
    for path in [DATA_DIR, UPLOAD_DIR, ROUTED_DIR, MODEL_DIR, REPORTS_DIR]:
        os.makedirs(path, exist_ok=True)
    for info in list(CATEGORIES.values()) + [MANUAL_REVIEW]:
        os.makedirs(os.path.join(ROUTED_DIR, info["folder"]), exist_ok=True)
