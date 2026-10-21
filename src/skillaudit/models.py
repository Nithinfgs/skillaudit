"""Core data types shared across skillaudit."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any


class Severity(IntEnum):
    INFO = 0
    WARNING = 1
    ERROR = 2

    @classmethod
    def parse(cls, value: str) -> Severity:
        try:
            return cls[value.strip().upper()]
        except KeyError as exc:
            raise ValueError(f"unknown severity: {value!r}") from exc

    @property
    def label(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: Severity
    message: str
    path: Path
    line: int = 1
    hint: str = ""


@dataclass
class Skill:
    """A skill directory containing a SKILL.md."""

    directory: Path
    skill_file: Path
    raw: str
    frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    body_start_line: int = 1
    parse_error: str | None = None

    @property
    def name(self) -> str:
        value = self.frontmatter.get("name")
        return value if isinstance(value, str) and value else self.directory.name

    @property
    def description(self) -> str:
        value = self.frontmatter.get("description")
        return value if isinstance(value, str) else ""
