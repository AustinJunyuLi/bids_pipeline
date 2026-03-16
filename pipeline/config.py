from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DEALS_DIR = DATA_DIR / "deals"
RAW_DIR = PROJECT_ROOT / "raw"
EXAMPLE_DIR = PROJECT_ROOT / "example"
SEEDS_PATH = DATA_DIR / "seeds.csv"
STATUS_PATH = DATA_DIR / "status.json"
OUTPUT_DIR = DATA_DIR / "output"
RUNS_DIR = DATA_DIR / "runs"
STATE_DB_PATH = RUNS_DIR / "pipeline_state.sqlite"

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"
DEFAULT_CONCURRENCY_LIMIT = 8
LLM_MAX_RETRIES = 3

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
