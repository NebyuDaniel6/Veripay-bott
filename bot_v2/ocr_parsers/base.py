import re
from typing import Dict, Any, Optional


def clean_amount_str(value: str) -> str:
    s = value.replace(",", "").replace("ETB", "").replace("Br", "").strip()
    return s


def to_confidence(ok: bool, base: float = 0.9) -> float:
    return base if ok else 0.0


def extract_first(patterns: list[str], text: str, flags: int = re.IGNORECASE) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            return m.group(1).strip()
    return None


def number_candidates(text: str) -> list[float]:
    cands: list[float] = []
    for m in re.finditer(r"(?<!\d)(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+\.\d+|\d+)(?:\s*(?:ETB|Br))?", text):
        raw = m.group(1)
        try:
            cands.append(float(clean_amount_str(raw)))
        except Exception:
            continue
    return cands 