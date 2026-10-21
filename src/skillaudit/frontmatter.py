"""Minimal YAML-subset frontmatter parser (no third-party dependencies).

Supports what real SKILL.md files use: scalar values (plain, single- or
double-quoted), folded/literal block scalars (``>`` / ``|``), one level of
nested mappings (e.g. ``metadata:``) and simple ``- item`` lists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class FrontmatterError(ValueError):
    """Raised when frontmatter is missing or malformed."""


@dataclass
class Parsed:
    data: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    body_start_line: int = 1


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        inner = value[1:-1]
        if value[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
        else:
            inner = inner.replace("''", "'")
        return inner
    if value and value[0] in "'\"":
        raise FrontmatterError(f"unterminated quoted string: {value[:30]}")
    # strip trailing comment on plain scalars
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    return value


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_block(lines: list[str], style: str) -> str:
    stripped = [ln.strip() for ln in lines]
    if style.startswith("|"):
        return "\n".join(stripped).strip("\n")
    out: list[str] = []
    for ln in stripped:
        if ln == "":
            out.append("\n")
        elif out and not out[-1].endswith("\n"):
            out[-1] += " " + ln
        else:
            out.append(ln)
    return "".join(out).strip()


def parse_mapping(lines: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if _indent(line) != 0:
            raise FrontmatterError(f"unexpected indentation: {line!r}")
        if ":" not in line:
            raise FrontmatterError(f"expected 'key: value', got: {line!r}")
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if not key:
            raise FrontmatterError(f"empty key in line: {line!r}")
        if key in result:
            raise FrontmatterError(f"duplicate key: {key!r}")
        # collect indented children
        j = i + 1
        children: list[str] = []
        while j < len(lines) and (not lines[j].strip() or _indent(lines[j]) > 0):
            children.append(lines[j])
            j += 1
        if rest[:1] in (">", "|"):
            result[key] = _parse_block(children, rest)
        elif rest == "":
            result[key] = _parse_nested(children)
        else:
            if children and any(c.strip() for c in children):
                # plain multi-line scalar continuation
                rest = rest + " " + " ".join(c.strip() for c in children if c.strip())
            result[key] = _unquote(rest)
        i = j
    return result


def _parse_nested(children: list[str]) -> Any:
    items = [c for c in children if c.strip() and not c.lstrip().startswith("#")]
    if not items:
        return ""
    if all(c.lstrip().startswith("- ") or c.strip() == "-" for c in items):
        return [_unquote(c.lstrip()[1:].strip()) for c in items]
    base = min(_indent(c) for c in items)
    return parse_mapping([c[base:] for c in children])


def parse(text: str) -> Parsed:
    """Split ``text`` into frontmatter mapping and Markdown body."""
    text = text.lstrip("﻿")
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != "---":
        raise FrontmatterError("file does not start with a '---' frontmatter fence")
    for idx in range(1, len(lines)):
        if lines[idx].rstrip() == "---":
            fm_lines = [ln.rstrip("\r") for ln in lines[1:idx]]
            body = "\n".join(lines[idx + 1 :])
            return Parsed(parse_mapping(fm_lines), body, idx + 2)
    raise FrontmatterError("frontmatter fence '---' is never closed")
