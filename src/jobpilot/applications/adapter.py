from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class FormField:
    name: str
    field_type: str
    required: bool
    label: str


@dataclass(frozen=True, slots=True)
class FormInspection:
    supported: bool
    fields: tuple[FormField, ...]
    blockers: tuple[str, ...]
    submit_controls: int


@dataclass(frozen=True, slots=True)
class SubmissionConfirmation:
    confirmed: bool
    evidence: str | None


class ApplicationAdapter(Protocol):
    def inspect(self, url: str) -> FormInspection: ...
    def check_support(self, inspection: FormInspection) -> bool: ...
    def fill(self, answers: dict[str, str]) -> None: ...
    def submit(self) -> None: ...
    def confirm(self) -> SubmissionConfirmation: ...
