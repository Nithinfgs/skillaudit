"""Output formats: text, json, sarif, github."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

from . import __version__
from .models import Finding, Severity
from .rules import RULES

SARIF_LEVEL = {Severity.ERROR: "error", Severity.WARNING: "warning", Severity.INFO: "note"}
COLORS = {Severity.ERROR: "31", Severity.WARNING: "33", Severity.INFO: "36"}


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def summary_line(n_skills: int, findings: list[Finding]) -> str:
    c = Counter(f.severity for f in findings)
    return (f"{n_skills} skill(s) checked: {c[Severity.ERROR]} error(s), "
            f"{c[Severity.WARNING]} warning(s), {c[Severity.INFO]} info")  # fmt: skip


def text(n_skills: int, findings: list[Finding], color: bool = False) -> str:
    lines: list[str] = []
    for f in findings:
        label = f.severity.label
        if color:
            label = f"\033[{COLORS[f.severity]}m{label}\033[0m"
        lines.append(f"{_rel(f.path)}:{f.line}: {label} [{f.rule}] {f.message}")
        if f.hint:
            lines.append(f"    hint: {f.hint}")
    lines.append(summary_line(n_skills, findings))
    return "\n".join(lines)


def as_json(n_skills: int, findings: list[Finding]) -> str:
    return json.dumps({
        "version": __version__,
        "skills_checked": n_skills,
        "findings": [{"rule": f.rule, "severity": f.severity.label, "message": f.message,
                      "path": _rel(f.path), "line": f.line, "hint": f.hint} for f in findings],
    }, indent=2)  # fmt: skip


def sarif(findings: list[Finding]) -> str:
    rules = [{"id": rid, "shortDescription": {"text": desc},
              "defaultConfiguration": {"level": SARIF_LEVEL[Severity.parse(sev)]}}
             for rid, (sev, desc) in sorted(RULES.items())]  # fmt: skip
    results = [{
        "ruleId": f.rule,
        "level": SARIF_LEVEL[f.severity],
        "message": {"text": f.message + (f" Hint: {f.hint}" if f.hint else "")},
        "locations": [{"physicalLocation": {
            "artifactLocation": {"uri": _rel(f.path)},
            "region": {"startLine": max(f.line, 1)}}}],
    } for f in findings]  # fmt: skip
    doc = {"$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0",
           "runs": [{"tool": {"driver": {"name": "skillaudit", "version": __version__,
                                         "informationUri": "https://github.com/Nithinfgs/skillaudit",
                                         "rules": rules}}, "results": results}]}  # fmt: skip
    return json.dumps(doc, indent=2)


def github(findings: list[Finding]) -> str:
    def esc(s: str) -> str:
        return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")

    kind = {Severity.ERROR: "error", Severity.WARNING: "warning", Severity.INFO: "notice"}
    return "\n".join(
        f"::{kind[f.severity]} file={esc(_rel(f.path))},line={f.line},title={f.rule}::{esc(f.message)}"
        for f in findings
    )


def use_color(stream_isatty: bool) -> bool:
    return stream_isatty and "NO_COLOR" not in os.environ
