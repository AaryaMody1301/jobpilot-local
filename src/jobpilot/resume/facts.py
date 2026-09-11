from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass

from jobpilot.resume.template_map import ITEM_RE, SECTION_RE, latex_to_plain

ROLE_CALL_RE = re.compile(
    r"\\role\{([^{}]*)\}\{([^{}]*)\}\{([^{}]*)\}\{([^{}]*)\}"
)
BEGIN_LIST_RE = re.compile(r"^\s*\\begin\{(?:itemize|enumerate)\}")
END_LIST_RE = re.compile(r"^\s*\\end\{(?:itemize|enumerate)\}")
STRUCTURAL_LINE_RE = re.compile(
    r"^\s*\\(?:begin|end)\{[^}]+\}|^\s*\\(?:newpage|vspace|smallskip|medskip|bigskip)\b"
)
HREF_ONLY_RE = re.compile(r"^\s*\\href\{")
LAYOUT_SPACING_RE = re.compile(r"\\(?:vspace|hspace|vskip|hskip)\*?\{[^{}]*\}")
LINEBREAK_SPACING_RE = re.compile(r"\\\\(?:\[[^\]]*\])?")


@dataclass(frozen=True, slots=True)
class ProtectedFactCandidate:
    fact_id: str
    value: str
    category: str
    line_start: int
    line_end: int
    extractor_kind: str

    def source_ref(self, source_sha256: str) -> dict[str, object]:
        return {
            "kind": "latex_protected",
            "extractor_kind": self.extractor_kind,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "source_sha256": source_sha256,
        }

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _fact_plain(value: str) -> str:
    without_layout = LAYOUT_SPACING_RE.sub("", value)
    without_layout = LINEBREAK_SPACING_RE.sub(" ", without_layout)
    return latex_to_plain(without_layout)


def _category_for_section(section: str, raw_line: str) -> str:
    normalized = section.casefold()
    if "technical skill" in normalized or normalized == "skills":
        return "skill"
    if "education" in normalized or "qualification" in normalized or "professional development" in normalized:
        return "qualification"
    if "project" in normalized and raw_line.lstrip().startswith(r"\textit"):
        return "skill"
    if "experience" in normalized or "employment" in normalized:
        return "responsibility"
    if "language" in normalized:
        return "other"
    return "other"


def _stable_id(source_sha256: str, ordinal: int, kind: str, value: str) -> str:
    digest = hashlib.sha256(f"{kind}\0{value}".encode("utf-8")).hexdigest()[:8]
    return f"fact-{source_sha256[:12]}-protected-{ordinal:03d}-{digest}"


def extract_protected_facts(source_text: str, source_sha256: str) -> list[ProtectedFactCandidate]:
    """Extract non-bullet facts that must be protected even when they are not editable.

    Bullet wording remains handled by the template-region mapper. This extractor covers
    structured role metadata and meaningful non-list content inside resume sections so
    employers, titles, dates, locations, qualifications, skills, and other factual text
    cannot disappear from the fact bank merely because the template renders them outside
    ``\\item`` commands.
    """

    lines = source_text.splitlines()
    candidates: list[ProtectedFactCandidate] = []
    section: str | None = None
    list_depth = 0

    def append(value: str, category: str, line_number: int, kind: str) -> None:
        cleaned = " ".join(value.split()).strip()
        if not cleaned:
            return
        ordinal = len(candidates) + 1
        candidates.append(
            ProtectedFactCandidate(
                fact_id=_stable_id(source_sha256, ordinal, kind, cleaned),
                value=cleaned,
                category=category,
                line_start=line_number,
                line_end=line_number,
                extractor_kind=kind,
            )
        )

    for index, line in enumerate(lines, start=1):
        section_match = SECTION_RE.search(line)
        if section_match:
            section = _fact_plain(section_match.group(1)) or "Unnamed section"
            continue

        role_match = ROLE_CALL_RE.search(line)
        if role_match:
            title, dates, employer, location = (_fact_plain(value) for value in role_match.groups())
            append(title, "title", index, "role_title")
            append(dates, "date", index, "role_dates")
            append(employer, "employer", index, "role_employer")
            append(location, "location", index, "role_location")
            continue

        if BEGIN_LIST_RE.match(line):
            list_depth += 1
            continue
        if END_LIST_RE.match(line):
            list_depth = max(0, list_depth - 1)
            continue
        if list_depth or ITEM_RE.match(line):
            continue
        if section is None:
            continue
        if not line.strip() or STRUCTURAL_LINE_RE.match(line) or HREF_ONLY_RE.match(line):
            continue

        plain = _fact_plain(line)
        if not plain:
            continue
        category = _category_for_section(section, line)
        append(plain, category, index, f"section:{section.casefold()}")

    return candidates
