"""Discover and load skills from the filesystem."""

from __future__ import annotations

from pathlib import Path

from . import frontmatter
from .models import Skill

SKILL_FILE = "SKILL.md"
DEFAULT_ROOTS = (".claude/skills", ".agents/skills", "skills")
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__"}
MAX_FILE_BYTES = 1_000_000


def find_skill_files(root: Path) -> list[Path]:
    """Return every SKILL.md under ``root`` (or ``root`` itself if it is one)."""
    if root.is_file():
        return [root] if root.name == SKILL_FILE else []
    found: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name not in SKIP_DIRS:
                    stack.append(entry)
            elif entry.name == SKILL_FILE:
                found.append(entry)
    return sorted(found)


def resolve_targets(paths: list[Path]) -> list[Path]:
    """Expand CLI paths; with no paths, look in conventional skill folders."""
    if paths:
        return paths
    return [Path(p) for p in DEFAULT_ROOTS if Path(p).is_dir()]


def load_skill(skill_file: Path) -> Skill:
    try:
        if skill_file.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("SKILL.md is larger than 1 MB")
        raw = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return Skill(skill_file.parent, skill_file, "", parse_error=f"cannot read file: {exc}")
    skill = Skill(skill_file.parent, skill_file, raw)
    try:
        parsed = frontmatter.parse(raw)
    except frontmatter.FrontmatterError as exc:
        skill.parse_error = str(exc)
        skill.body = raw
        return skill
    skill.frontmatter = parsed.data
    skill.body = parsed.body
    skill.body_start_line = parsed.body_start_line
    return skill


def load_all(targets: list[Path]) -> list[Skill]:
    seen: set[Path] = set()
    skills: list[Skill] = []
    for target in targets:
        for skill_file in find_skill_files(target):
            resolved = skill_file.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            skills.append(load_skill(skill_file))
    return skills
