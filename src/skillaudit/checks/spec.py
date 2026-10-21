"""Conformance with the Agent Skills specification (agentskills.io)."""

from __future__ import annotations

import re

from ..models import Finding, Severity, Skill

NAME_RE = re.compile(r"^[^\W_]+(?:-[^\W_]+)*$")
KNOWN_KEYS = {
    "name", "description", "license", "compatibility", "metadata", "allowed-tools",
    # widely used extensions in Claude Code and other clients
    "version", "model", "disable-model-invocation", "user-invocable", "argument-hint",
    "when_to_use", "tags",
}  # fmt: skip


def check(skill: Skill) -> list[Finding]:
    path = skill.skill_file
    out: list[Finding] = []

    def add(rule: str, sev: Severity, msg: str, hint: str = "", line: int = 1) -> None:
        out.append(Finding(rule, sev, msg, path, line, hint))

    if skill.parse_error:
        add("SA001", Severity.ERROR, f"invalid frontmatter: {skill.parse_error}",
            "SKILL.md must start with a YAML block delimited by '---' lines.")  # fmt: skip
        return out
    fm = skill.frontmatter

    name = fm.get("name")
    if not isinstance(name, str) or not name:
        add("SA002", Severity.ERROR, "missing required field 'name'")
    else:
        if len(name) > 64:
            add("SA002", Severity.ERROR, f"name is {len(name)} chars (max 64)")
        if not NAME_RE.match(name) or name != name.lower():
            add("SA002", Severity.ERROR, f"name {name!r} must be lowercase letters, "
                "digits and single hyphens, not starting or ending with '-'")  # fmt: skip
        if name != skill.directory.name:
            add("SA003", Severity.ERROR,
                f"name {name!r} does not match directory {skill.directory.name!r}",
                "Rename the directory or the 'name' field so they are identical.")  # fmt: skip

    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        add("SA004", Severity.ERROR, "missing or empty required field 'description'")
    elif len(desc) > 1024:
        add("SA004", Severity.ERROR, f"description is {len(desc)} chars (max 1024)")

    compat = fm.get("compatibility")
    if compat is not None and (not isinstance(compat, str) or not 1 <= len(compat) <= 500):
        add("SA005", Severity.ERROR, "compatibility must be a string of 1-500 characters")

    meta = fm.get("metadata")
    if meta is not None and (not isinstance(meta, dict) or not all(isinstance(v, str) for v in meta.values())):
        add("SA006", Severity.ERROR, "metadata must be a mapping of string keys to string values",
            'Quote numbers, e.g. version: "1.0".')  # fmt: skip

    tools = fm.get("allowed-tools")
    if tools is not None and not isinstance(tools, (str, list)):
        add("SA008", Severity.ERROR, "allowed-tools must be a space-separated string")

    for key in fm:
        if key not in KNOWN_KEYS:
            add("SA007", Severity.INFO, f"unknown frontmatter field {key!r}",
                "Clients may ignore it; put custom data under 'metadata'.")  # fmt: skip
    return out
