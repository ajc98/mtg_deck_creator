from pathlib import Path

DATA_DIR = Path.home() / ".mtgdeck"
DB_PATH = DATA_DIR / "mtgdeck.duckdb"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
