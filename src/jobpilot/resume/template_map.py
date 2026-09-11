from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Iterable

SECTION_RE = re.compile(r"\\section\*?\{([^}]*)\}")
ITEM_RE = re.compile(r"^\s*\\item(?:\[[^\]]*\])?\s*(.*)$")
DOCUMENTCLASS_RE = re.compile(r"\\documentclass(?:\[[^\]]*\])?\{([^}]*)\}")
EXTERNAL_INPUT_RE = re.compile(r"\\(?:input|include|includegraphics|bibliography)\*?(?:\[[^\]]*\])?\{([^}]*)\}")
COMMENT_RE = re.compile(r"(?<!\\)%.*$")
SIMPLE_COMMAND_RE = re.compile(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?")
WRAPPER_COMMAND_RE = re.compile(r"\\(?:textbf|textit|emph|underline|small|large|Large|href)\*?(?:\{[^{}]*\})?\{([^{}]*)\}")


@dataclass(frozen=True, slots=True)
class TemplateRegion:
    region_id: str
    ordinal: int
    section: str
    line_start: int
    line_end: int
    raw_text: str
    plain_text: str
    raw_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def latex_to_plain(value: str) -> str:
    """Best-effort display text only. The original LaTeX remains authoritative."""
    text = "\n".join(COMMENT_RE.sub("", line) for line in value.splitlines())
    replacements = {
        r"\&": "&",
        r"\%": "%",
        r"\$": "$",
        r"\#": "#",
        r"\_": "_",
        r"\{": "{",
        r"\}": "}",
        r"~": " ",
        r"\\": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    previous = None
    while text != previous:
        previous = text
        text = WRAPPER_COMMAND_RE.sub(r" \1 ", text)
    text = SIMPLE_COMMAND_RE.sub(" ", text)
    text = text.replace("{", " ").replace("}", " ")
    return " ".join(text.split())


def map_editable_regions(source_text: str, source_sha256: str) -> list[TemplateRegion]:
    """Identify bullet wording as candidate editable regions without changing source."""
    lines = source_text.splitlines()
    regions: list[TemplateRegion] = []
    section = "Unsectioned"
    active_start: int | None = None
    active_section = section

    def finish(end_index_exclusive: int) -> None:
        nonlocal active_start
        if active_start is None:
            return
        raw_lines = lines[active_start:end_index_exclusive]
        raw = "\n".join(raw_lines).strip()
        first = ITEM_RE.match(raw_lines[0]) if raw_lines else None
        display_source = "\n".join([first.group(1) if first else "", *raw_lines[1:]])
        plain = latex_to_plain(display_source)
        if plain:
            ordinal = len(regions) + 1
            region_id = f"region-{source_sha256[:12]}-{ordinal:03d}"
            regions.append(
                TemplateRegion(
                    region_id=region_id,
                    ordinal=ordinal,
                    section=active_section,
                    line_start=active_start + 1,
                    line_end=end_index_exclusive,
                    raw_text=raw,
                    plain_text=plain,
                    raw_sha256=_digest_text(raw),
                )
            )
        active_start = None

    for index, line in enumerate(lines):
        section_match = SECTION_RE.search(line)
        item_match = ITEM_RE.match(line)
        if section_match:
            finish(index)
            section = latex_to_plain(section_match.group(1)) or "Unnamed section"
        if item_match:
            finish(index)
            active_start = index
            active_section = section
        elif active_start is not None and re.match(r"^\s*\\end\{(?:itemize|enumerate)\}", line):
            finish(index)
    finish(len(lines))
    return regions


def source_metrics(source_text: str, regions: Iterable[TemplateRegion]) -> dict[str, object]:
    lines = source_text.splitlines()
    region_list = list(regions)
    sections: list[str] = []
    for match in SECTION_RE.finditer(source_text):
        name = latex_to_plain(match.group(1))
        if name:
            sections.append(name)
    documentclass_match = DOCUMENTCLASS_RE.search(source_text)
    external_inputs = sorted({match.group(1).strip() for match in EXTERNAL_INPUT_RE.finditer(source_text) if match.group(1).strip()})
    return {
        "line_count": len(lines),
        "section_order": sections,
        "bullet_count": len(region_list),
        "documentclass": documentclass_match.group(1).strip() if documentclass_match else None,
        "external_inputs": external_inputs,
        "contains_write18": bool(re.search(r"\\(?:write18|immediate\s*\\write18)", source_text, re.IGNORECASE)),
    }
