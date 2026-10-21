"""Authoring quality: trigger clarity, size, and file references."""

from __future__ import annotations

import re
from pathlib import Path

from ..models import Finding, Severity, Skill
from ..tokens import estimate_tokens

TRIGGER_RE = re.compile(r"\b(use when|use this|use for|when the user|when you|whenever|if the user|trigger)", re.I)
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CODE_FENCE_RE = re.compile(r"^\s*```")
BARE_PATH_RE = re.compile(r"(?<![\w/.:-])((?:scripts|references|assets)/[\w./-]+\.\w+)")

MAX_BODY_LINES = 500
MAX_BODY_TOKENS = 5000
MIN_DESC_CHARS = 40
METADATA_TOKEN_TARGET = 100


def metadata_tokens(skill: Skill) -> int:
    return estimate_tokens(f"{skill.name} {skill.description}")


def _references(skill: Skill) -> list[tuple[str, int]]:
    refs: list[tuple[str, int]] = []
    in_fence = False
    for offset, line in enumerate(skill.body.split("\n")):
        lineno = skill.body_start_line + offset
        if CODE_FENCE_RE.match(line):
            in_fence = not in_fence
        targets = [m.group(1) for m in LINK_RE.finditer(line)]
        targets += [m.group(1) for m in BARE_PATH_RE.finditer(line)] if not in_fence else []
        for target in targets:
            target = target.split("#", 1)[0]
            looks_like_file = "/" in target or "." in target
            if target and looks_like_file and "://" not in target and not target.startswith(("mailto:", "/", "~")):
                refs.append((target, lineno))
    return refs


def check(skill: Skill) -> list[Finding]:
    out: list[Finding] = []
    path = skill.skill_file
    if skill.parse_error:
        return out

    desc = skill.description.strip()
    if desc and len(desc) < MIN_DESC_CHARS:
        out.append(Finding("SA102", Severity.WARNING,
            f"description is only {len(desc)} chars; agents choose skills based on it",
            path, 1, "Say what the skill does and when to use it."))  # fmt: skip
    elif desc and not TRIGGER_RE.search(desc):
        out.append(Finding("SA101", Severity.WARNING,
            "description never says WHEN to use the skill", path, 1,
            "Add a trigger clause such as 'Use when the user asks about ...'."))  # fmt: skip

    mt = metadata_tokens(skill)
    if mt > 2 * METADATA_TOKEN_TARGET:
        out.append(Finding("SA110", Severity.WARNING,
            f"name+description cost ~{mt} tokens in every session (target ~{METADATA_TOKEN_TARGET})",
            path, 1, "Shorten the description; it is loaded for all installed skills."))  # fmt: skip

    if not skill.body.strip():
        out.append(Finding("SA108", Severity.WARNING, "SKILL.md body is empty", path, skill.body_start_line))

    lines = skill.body.count("\n") + 1 if skill.body else 0
    if lines > MAX_BODY_LINES:
        out.append(Finding("SA103", Severity.WARNING,
            f"body is {lines} lines (recommended max {MAX_BODY_LINES})", path, skill.body_start_line,
            "Move detail into references/ files loaded on demand."))  # fmt: skip
    bt = estimate_tokens(skill.body)
    if bt > MAX_BODY_TOKENS:
        out.append(Finding("SA104", Severity.WARNING,
            f"body is ~{bt} tokens (recommended max {MAX_BODY_TOKENS})", path, skill.body_start_line,
            "Large bodies are loaded in full when the skill activates."))  # fmt: skip

    root = skill.directory.resolve()
    seen: set[str] = set()
    for target, lineno in _references(skill):
        if target in seen:
            continue
        seen.add(target)
        resolved = (skill.directory / target).resolve()
        if root != resolved and root not in resolved.parents:
            out.append(Finding("SA106", Severity.ERROR,
                f"reference {target!r} escapes the skill directory", path, lineno,
                "Skills must be self-contained; copy the file into the skill."))  # fmt: skip
        elif not resolved.exists():
            out.append(Finding("SA105", Severity.ERROR,
                f"referenced file {target!r} does not exist", path, lineno))  # fmt: skip
        elif resolved.suffix == ".md" and resolved != skill.skill_file.resolve():
            out.extend(_nested(skill, resolved, target, lineno))
    return out


def _nested(skill: Skill, ref_file: Path, target: str, lineno: int) -> list[Finding]:
    try:
        text = ref_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    nested = [m.group(1) for m in LINK_RE.finditer(text)
              if m.group(1).endswith(".md") and "://" not in m.group(1)]  # fmt: skip
    if nested:
        return [Finding("SA107", Severity.INFO,
            f"{target!r} links onward to {nested[0]!r}; keep references one level deep",
            skill.skill_file, lineno)]  # fmt: skip
    return []
