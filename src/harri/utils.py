from pathlib import Path

SRC_HARRI = Path(__file__).parent.resolve()
REPO_ROOT = SRC_HARRI.parent.parent
PROD_DB = REPO_ROOT / "secrets" / "db" / "harri.db"
