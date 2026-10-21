"""Run all checks and apply configuration."""

from __future__ import annotations

from pathlib import Path

from .checks import PER_SKILL, library
from .config import Config
from .loader import load_all, resolve_targets
from .models import Finding, Skill


def audit(paths: list[Path], config: Config) -> tuple[list[Skill], list[Finding]]:
    skills = load_all(resolve_targets(paths))
    findings: list[Finding] = []
    for skill in skills:
        for check in PER_SKILL:
            findings.extend(check(skill))
    findings.extend(library.check(skills, overlap_threshold=config.overlap_threshold,
                                  budget_tokens=config.metadata_budget_tokens))  # fmt: skip
    findings = [f for f in findings if f.rule not in config.ignore]
    findings.sort(key=lambda f: (str(f.path), f.line, f.rule))
    return skills, findings
