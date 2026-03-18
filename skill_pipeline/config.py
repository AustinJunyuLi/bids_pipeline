from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DEALS_DIR = DATA_DIR / "deals"
SKILL_DIR = DATA_DIR / "skill"
RAW_DIR = PROJECT_ROOT / "raw"
SEEDS_PATH = DATA_DIR / "seeds.csv"

SKILL_PIPELINE_VERSION = "0.1.0"
