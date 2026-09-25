"""Heuristic masking of common identifiers; human PII review is still required."""
import re

EMAIL = re.compile(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b")
URL = re.compile(r"(?i)(?:https?://|www\.|t\.me/)\S+")
PHONE = re.compile(r"(?<!\d)(?:\+?7|8)[\s()\-]*\d{3}[\s()\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)")
HANDLE = re.compile(r"(?<!\w)@[\w.]{2,}", re.UNICODE)
COORDINATES = re.compile(r"(?<!\d)-?\d{1,2}\.\d{3,},\s*-?\d{1,3}\.\d{3,}(?!\d)")


def anonymize_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    for pattern, replacement in (
        (EMAIL, "[EMAIL]"),
        (URL, "[URL]"),
        (PHONE, "[PHONE]"),
        (HANDLE, "[ACCOUNT]"),
        (COORDINATES, "[GEO]"),
    ):
        text = pattern.sub(replacement, text)
    return text
