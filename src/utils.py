from __future__ import annotations

import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


APP_NAME = "ExtratorPDF"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_distribution_base_path() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def get_app_base_path() -> Path:
    if not is_frozen():
        return Path(__file__).resolve().parents[1]

    distribution_path = get_distribution_base_path()
    if any((distribution_path / name).exists() for name in ("app.py", "src", "assets", ".streamlit")):
        return distribution_path

    bundled_path = getattr(sys, "_MEIPASS", "")
    if bundled_path:
        return Path(bundled_path)

    return distribution_path


def get_user_data_dir() -> Path:
    appdata = os.environ.get("APPDATA", "").strip()
    if appdata:
        base_path = Path(appdata) / APP_NAME
    else:
        base_path = Path.home() / ".extrator_pdf"
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path


def get_data_dir() -> Path:
    if is_frozen():
        data_dir = get_user_data_dir() / "data"
    else:
        data_dir = get_app_base_path() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_logs_dir() -> Path:
    if is_frozen():
        logs_dir = get_user_data_dir() / "logs"
    else:
        logs_dir = get_app_base_path() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def configure_file_logging(name: str = "extrator_pdf") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    log_file = get_logs_dir() / "app.log"
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s"))

    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def generate_quote_number() -> str:
    return "ORC-" + datetime.now().strftime("%Y%m%d-%H%M%S")


def generate_order_number() -> str:
    return "PED-" + datetime.now().strftime("%Y%m%d-%H%M%S")


def format_date_br(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    text = safe_text(value)
    if not text:
        return ""
    try:
        return datetime.fromisoformat(text).strftime("%d/%m/%Y")
    except ValueError:
        return text


def format_brl(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0
    formatted = f"{number:,.2f}"
    return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def format_weight(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0
    return f"{number:.2f}".replace(".", ",") + " g"


def basic_document_format_is_valid(value: str, *, kind: str) -> bool:
    digits = "".join(char for char in safe_text(value) if char.isdigit())
    if not digits:
        return True
    if kind == "cpf":
        return len(digits) == 11
    if kind == "cnpj":
        return len(digits) == 14
    return False


def get_default_logo_path() -> Path:
    if is_frozen():
        external_logo = get_distribution_base_path() / "assets" / "logo.png"
        if external_logo.exists():
            return external_logo
    return get_app_base_path() / "assets" / "logo.png"


def get_logo_source(uploaded_logo: bytes | None = None) -> bytes | None:
    if uploaded_logo:
        return uploaded_logo

    default_logo = get_default_logo_path()
    if default_logo.exists():
        try:
            return default_logo.read_bytes()
        except OSError:
            return None

    return None
