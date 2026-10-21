"""Rule modules. Each exposes ``check(skill) -> list[Finding]``."""

from __future__ import annotations

from collections.abc import Callable

from ..models import Finding, Skill
from . import quality, security, spec

PerSkillCheck = Callable[[Skill], list[Finding]]

PER_SKILL: tuple[PerSkillCheck, ...] = (spec.check, quality.check, security.check)
