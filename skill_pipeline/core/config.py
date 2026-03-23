from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DEALS_DIR = DATA_DIR / "deals"
SKILL_DIR = DATA_DIR / "skill"
RAW_DIR = PROJECT_ROOT / "raw"
SEEDS_PATH = DATA_DIR / "seeds.csv"

PRIMARY_FILING_TYPES = (
    "DEFM14A",
    "PREM14A",
    "SC 14D-9",
    "SC 13E-3",
    "S-4",
    "SC TO-T",
)
SUPPLEMENTARY_FILING_TYPES = ("SC 13D", "DEFA14A", "8-K")

PRIMARY_PREFERENCE = {ft: i for i, ft in enumerate(PRIMARY_FILING_TYPES)}

SKILL_PIPELINE_VERSION = "0.1.0"
