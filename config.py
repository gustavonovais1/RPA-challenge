from __future__ import annotations
import os
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent


def _first_env_str(*keys: str, default: str) -> str:
    for key in keys:
        val = os.environ.get(key)
        if val is not None and str(val).strip() != "":
            return str(val).strip()
    return default


def _first_env_int(*keys: str, default: int) -> int:
    raw = _first_env_str(*keys, default=str(default))
    return int(raw)


def _first_env_float(*keys: str, default: float) -> float:
    raw = _first_env_str(*keys, default=str(default))
    return float(raw)


def _first_env_bool(*keys: str) -> bool:
    for key in keys:
        if key not in os.environ:
            continue
        val = os.environ.get(key, "").lower()
        if val in ("1", "true", "yes", "on"):
            return True
        if val in ("0", "false", "no", "off"):
            return False
    return False


CHALLENGE_URL: str = _first_env_str(
    "CHALLENGE_URL",
    "RPA_CHALLENGE_URL",
    default="https://rpachallenge.com/",
)

DEFAULT_WAIT_TIMEOUT: int = _first_env_int(
    "TIMEOUT",
    "RPA_WAIT_TIMEOUT",
    default=25,
)

IMPLICIT_WAIT_SECONDS: float = _first_env_float(
    "IMPLICIT_WAIT",
    "RPA_IMPLICIT_WAIT",
    default=1.0,
)

HEADLESS: bool = _first_env_bool("HEADLESS", "RPA_HEADLESS")

DATABASE_DIR: Path = PROJECT_ROOT / "database"
DATABASE_PATH: Path = DATABASE_DIR / _first_env_str(
    "RPA_DB_NAME",
    default="rpa_challenge.db",
)

DATA_DIR: Path = PROJECT_ROOT / "data"
EXCEL_PATH: Path = DATA_DIR / "challenge.xlsx"

CHALLENGE_EXCEL_DOWNLOAD_URL: str = _first_env_str(
    "CHALLENGE_EXCEL_URL",
    "RPA_CHALLENGE_EXCEL_URL",
    default="https://rpachallenge.com/assets/downloadFiles/challenge.xlsx",
)

LOGS_DIR: Path = PROJECT_ROOT / "logs"
SCREENSHOTS_DIR: Path = PROJECT_ROOT / "screenshots"
OUTPUT_DIR: Path = PROJECT_ROOT / "output"

FINAL_SCREENSHOT_FILENAME: str = "resultado_final_score.png"
MAX_SCREENSHOT_FILES: int = _first_env_int(
    "RPA_MAX_SCREENSHOTS",
    default=3,
)

MAX_RUN_RESULTS_CSV_FILES: int = _first_env_int(
    "RPA_MAX_RUN_RESULTS_CSV",
    default=5,
)
