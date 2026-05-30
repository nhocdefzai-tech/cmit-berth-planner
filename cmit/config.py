from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"
DATA_DIR = PROJECT_ROOT / "data"
SOURCE_DIR = DATA_DIR / "sources"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
DB_PATH = DATA_DIR / "cmit_shift_reports.sqlite3"
TEMPLATE_PATH = DOCS_DIR / "SHIFT_REPORT_2026-05-28_D2.xlsx"
SAMPLE_MOVE_EVENT_PATH = SAMPLE_DATA_DIR / "MoveEvent_20260526_2203.xlsx"


def ensure_runtime_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    SOURCE_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
