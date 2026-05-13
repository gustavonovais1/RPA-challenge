from __future__ import annotations
import re
from typing import Any, Dict, Optional

_PATTERN = re.compile(
    r"Your\s+success\s+rate\s+is\s+"
    r"(?P<rate>\d+(?:\.\d+)?)\s*%\s*"
    r"\(\s*(?P<filled>\d+)\s+out\s+of\s+(?P<total>\d+)\s+fields?\)\s+"
    r"in\s+(?P<ms>\d+)\s+milliseconds?",
    re.IGNORECASE,
)


def parse_challenge_result_message(text: str) -> Optional[Dict[str, Any]]:
    """Extrai as métricas da mensagem final do desafio."""
    if not text or not text.strip():
        return None
    match = _PATTERN.search(text)
    if not match:
        return None
    return {
        "success_rate": float(match.group("rate")),
        "filled_fields": int(match.group("filled")),
        "total_fields": int(match.group("total")),
        "execution_time_ms": int(match.group("ms")),
    }
