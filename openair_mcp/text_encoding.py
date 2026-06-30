"""Fix UTF-8 mojibake in Spanish/EU portal column labels."""
from __future__ import annotations

_MOJIBAKE_MARKERS = ("Ã", "Â", "â€", "ï¿½")


def looks_like_mojibake(text: str) -> bool:
    return any(marker in text for marker in _MOJIBAKE_MARKERS)


def fix_mojibake(text: str) -> str:
    """Repair UTF-8 bytes misread as Latin-1 (e.g. DiÃ³xido → Dióxido)."""
    if not text or not isinstance(text, str):
        return text
    if not looks_like_mojibake(text):
        return text
    try:
        fixed = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    return fixed if fixed and fixed != text else text


def normalize_label(text: str) -> str:
    """Normalize a column header or series name for ingest and prepare."""
    if text is None:
        return text
    cleaned = str(text).strip()
    return fix_mojibake(cleaned)
