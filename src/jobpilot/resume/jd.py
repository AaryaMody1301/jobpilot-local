from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass

MAX_JD_CHARS = 50_000
INSTRUCTION_MARKERS = (
    "ignore previous",
    "ignore all previous",
    "system message",
    "developer message",
    "assistant message",
    "follow these instructions",
    "prompt injection",
    "reveal your prompt",
    "disregard previous",
)


@dataclass(frozen=True, slots=True)
class ManualJobDescription:
    text: str
    sha256: str
    source_url: str | None
    instruction_like: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_job_description(text: str, source_url: str | None = None) -> ManualJobDescription:
    if not isinstance(text, str):
        raise TypeError("job description must be text")
    normalized = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    normalized = "".join(ch for ch in normalized if ch in "\n\t" or unicodedata.category(ch) != "Cc")
    normalized = "\n".join(line.rstrip() for line in normalized.splitlines()).strip()
    if not normalized:
        raise ValueError("job description cannot be empty")
    if len(normalized) > MAX_JD_CHARS:
        raise ValueError(f"job description exceeds {MAX_JD_CHARS} characters")
    url = (source_url or "").strip() or None
    if url is not None and len(url) > 2000:
        raise ValueError("job description source URL exceeds 2000 characters")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    folded = " ".join(normalized.casefold().split())
    instruction_like = any(marker in folded for marker in INSTRUCTION_MARKERS)
    return ManualJobDescription(normalized, digest, url, instruction_like)


def normalize_phrase(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value)).casefold().split())


def phrase_is_in_jd(phrase: str, jd_text: str) -> bool:
    needle = normalize_phrase(phrase)
    if not needle:
        return False
    haystack = normalize_phrase(jd_text)
    if needle in haystack:
        return True
    tokens = re.findall(r"[a-z0-9+#.-]+", needle)
    return bool(tokens) and all(re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", haystack) for token in tokens)
