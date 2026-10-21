"""Security heuristics for skills: prompt injection, hidden text, dangerous commands.

Skills are executable-by-proxy: their text enters the agent's context as trusted
instructions, and their scripts run with the agent's permissions. These rules
flag patterns commonly seen in malicious or careless skills. They are
heuristics: expect some false positives (silence them inline with
``skillaudit-ignore``) and false negatives (this is not a sandbox).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..loader import MAX_FILE_BYTES, SKIP_DIRS
from ..models import Finding, Severity, Skill

IGNORE_MARKER = "skillaudit-ignore"
TEXT_SUFFIXES = {".md", ".txt", ".sh", ".bash", ".zsh", ".py", ".js", ".ts", ".mjs", ".ps1",
                 ".rb", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini"}  # fmt: skip
PROSE_SUFFIXES = {".md", ".txt"}
MAX_FILES = 500


@dataclass(frozen=True)
class Pattern:
    rule: str
    severity: Severity
    regex: re.Pattern[str]
    message: str
    hint: str = ""
    prose_only: bool = False


def _p(rule: str, sev: Severity, rx: str, msg: str, hint: str = "", prose: bool = False) -> Pattern:
    return Pattern(rule, sev, re.compile(rx, re.I), msg, hint, prose)


E, W = Severity.ERROR, Severity.WARNING

PATTERNS: tuple[Pattern, ...] = (
    _p(
        "SA201",
        E,
        r"ignore\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier)\s+(?:instructions|rules|prompts?)",
        "prompt-injection phrase: tells the agent to ignore prior instructions",
        prose=True,
    ),
    _p(
        "SA201",
        E,
        r"(?:do\s*n[o']?t|never)\s+(?:(?:tell|inform|mention|reveal|show|let)\s+(?:this|it|that|these|anything)(?:\s+to)?\s+the\s+user|(?:tell|inform|notify|alert)\s+the\s+user\s+(?:about|of)\s+(?:this|it|that|these|any\w*|(?:the\s+)?(?:network|upload|data|transfer|collection)\w*)|mention\s+(?:this|it|that))",
        "instructs the agent to conceal behaviour from the user",
        prose=True,
    ),
    _p(
        "SA201",
        E,
        r"(?:hide|conceal)\s+(?:this|it|these)\s+from\s+the\s+user|without\s+(?:telling|informing|asking|notifying)\s+the\s+user",
        "instructs the agent to act without the user's knowledge",
        prose=True,
    ),
    _p(
        "SA201",
        E,
        r"disregard\s+(?:the\s+|your\s+)?(?:system\s+prompt|safety|guardrails|previous)|override\s+(?:your\s+)?(?:safety|system\s+prompt)|you\s+are\s+now\s+in\s+(?:developer|dan|root|admin)\s+mode",
        "attempts to override system or safety instructions",
        prose=True,
    ),
    _p(
        "SA203",
        E,
        r"(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|da)?sh\b|(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?python3?\b|\b(?:iwr|Invoke-WebRequest)\b[^\n|]*\|\s*(?:iex|Invoke-Expression)",
        "downloads remote code and pipes it straight into an interpreter",
        "Pin a version, verify a checksum, or vendor the script.",
    ),
    _p(
        "SA204",
        W,
        r"(?:~|\$HOME|/Users/[^/\s]+|/home/[^/\s]+)/\.(?:ssh|aws|gnupg|netrc|npmrc|git-credentials|kube|docker/config\.json)|\bid_(?:rsa|ed25519)\b|/etc/(?:passwd|shadow)|Library/Keychains|Chrome/[^\n]*Login Data",
        "touches a credential or sensitive system path",
        "Skills rarely need credential stores; confirm this is intentional.",
    ),
    _p(
        "SA205",
        E,
        r"AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,}|sk-(?:ant-)?[A-Za-z0-9_-]{24,}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}|-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----",
        "looks like a hard-coded secret or private key",
        "Remove it and rotate the credential.",
    ),
    _p(
        "SA206",
        E,
        r"base64\s+(?:-d|--decode)\b[^\n]*\|\s*(?:ba|z)?sh\b|eval\s+[\"']?\$\(\s*(?:curl|wget)|(?:exec|eval)\s*\(\s*(?:base64\.b64decode|atob)|python3?\s+-c\s+[\"'][^\n]*b64decode",
        "decodes or fetches a payload and executes it (obfuscated execution)",
    ),
    _p(
        "SA207",
        E,
        r"\brm\s+-[a-z]*r[a-z]*\s+(?:--no-preserve-root\s+)?(?:/|~|\$HOME|\*)(?:\s|$|\")|\bmkfs(?:\.\w+)?\s|\bdd\s+if=[^\n]*of=/dev/|:\(\)\s*\{\s*:\|:&\s*\};:|chmod\s+-R\s+0?777\s+/(?:\s|$)",
        "destructive command that can wipe files or disks",
    ),
    _p(
        "SA210",
        E,
        r"(?:curl|wget)\b[^\n]*\s(?:-d|--data(?:-binary|-raw|-urlencode)?|-F|--form|--upload-file|-T)\s+[@\"']?[^\n]*(?:\.ssh|\.aws|\.env\b|credentials|id_rsa|\$\{?[A-Z_]*(?:KEY|TOKEN|SECRET|PASSWORD)\b)|\b(?:printenv|env)\s*\|\s*(?:curl|nc|ncat)\b|\b(?:cat|base64|tar|zip)\s+[^\n|]*(?:\.ssh|\.aws|\.env\b|id_rsa|credentials)[^\n|]*\|\s*(?:curl|wget|nc|ncat)\b",
        "sends credentials or environment variables to a remote host (exfiltration pattern)",
    ),
    _p("SA211", W, r"(?:^|[\s`$;&|(])sudo\s+\S", "uses sudo; skills should not need elevated privileges"),
)

INVISIBLE_RE = re.compile("[​-‏‪-‮⁠-⁤⁦-⁩﻿\U000e0000-\U000e007f]")
HTML_COMMENT_RE = re.compile(r"<!--(.*?)-->", re.S)
COMMENT_INSTRUCTION_RE = re.compile(
    r"\b(ignore|you\s+must|you\s+should|always|never|do\s+not|don't|secretly|system|instruction|exfiltrate|send|execute|run)\b",
    re.I,
)  # noqa: E501
BROAD_TOOL_RE = re.compile(r"^(?:\*|Bash|Bash\(\*\)|Bash\(\*:\*\)|Shell|Shell\(\*\))$")


NEGATION_RE = re.compile(r"\b(?:never|don'?t|do\s+not|avoid|must\s+not|should\s+not|shouldn'?t)\b", re.I)


def _is_mention(line: str, start: int, *, prose: bool) -> bool:
    """True when a match follows a negation, or (for prose phrases) is quoted: documented, not used."""
    before = line[:start]
    quoted = prose and before[-1:] in {'"', "'", "`", "\u201c", "\u2018"}
    return quoted or bool(NEGATION_RE.search(before[-80:]))


def _suppressed(lines: list[str]) -> dict[int, set[str] | None]:
    """Map 1-based line -> suppressed rule ids (None means all rules).

    A marker silences its own line and the line after it.
    """
    result: dict[int, set[str] | None] = {}
    for idx, line in enumerate(lines, start=1):
        if IGNORE_MARKER not in line:
            continue
        found = set(re.findall(r"SA\d{3}", line.split(IGNORE_MARKER, 1)[1]))
        for target in (idx, idx + 1):
            if target in result and result[target] is None:
                continue
            result[target] = None if not found else (result.get(target) or set()) | found
    return result


def scan_text(path: Path, text: str, *, prose: bool) -> list[Finding]:
    lines = text.split("\n")
    muted = _suppressed(lines)
    out: list[Finding] = []
    seen: set[tuple[str, int]] = set()

    def add(rule: str, sev: Severity, msg: str, lineno: int, hint: str = "") -> None:
        mute = muted.get(lineno, set())
        if lineno in muted and (mute is None or rule in mute):
            return
        if (rule, lineno) in seen:
            return
        seen.add((rule, lineno))
        out.append(Finding(rule, sev, msg, path, lineno, hint))

    for lineno, line in enumerate(lines, start=1):
        for pat in PATTERNS:
            if pat.prose_only and not prose:
                continue
            match = pat.regex.search(line)
            if match:
                sev, msg = pat.severity, pat.message
                if sev is E and _is_mention(line, match.start(), prose=pat.prose_only):
                    sev, msg = W, msg + " (quoted or negated; verify it is only a mention)"
                add(pat.rule, sev, msg, lineno, pat.hint)
        match = INVISIBLE_RE.search(line)
        if match and not (lineno == 1 and match.start() == 0 and match.group() == "﻿"):
            add("SA202", E, f"invisible/bidirectional Unicode character U+{ord(match.group()):04X}",
                lineno, "Hidden characters can smuggle instructions past human review.")  # fmt: skip

    if prose:
        for m in HTML_COMMENT_RE.finditer(text):
            inner = m.group(1)
            if IGNORE_MARKER in inner or not COMMENT_INSTRUCTION_RE.search(inner):
                continue
            lineno = text.count("\n", 0, m.start()) + 1
            add("SA209", W, "HTML comment contains instruction-like text the reader will not see",
                lineno, "Comments are invisible when rendered but are read by the agent.")  # fmt: skip
    return out


def _iter_files(skill: Skill) -> list[Path]:
    files: list[Path] = []
    stack = [skill.directory]
    while stack and len(files) < MAX_FILES:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name not in SKIP_DIRS and not (entry != current and (entry / "SKILL.md").exists()):
                    stack.append(entry)
            elif entry.suffix.lower() in TEXT_SUFFIXES and entry != skill.skill_file:
                files.append(entry)
    return files


def check(skill: Skill) -> list[Finding]:
    out = scan_text(skill.skill_file, skill.raw, prose=True)

    tools = skill.frontmatter.get("allowed-tools")
    entries = tools.split() if isinstance(tools, str) else tools if isinstance(tools, list) else []
    for entry in entries:
        if isinstance(entry, str) and BROAD_TOOL_RE.match(entry.strip(",")):
            out.append(Finding("SA208", W, f"allowed-tools grants unrestricted access via {entry!r}",
                skill.skill_file, 1, "Scope it, e.g. Bash(git status:*)."))  # fmt: skip

    for file in _iter_files(skill):
        try:
            if file.stat().st_size > MAX_FILE_BYTES:
                continue
            text = file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        out.extend(scan_text(file, text, prose=file.suffix.lower() in PROSE_SUFFIXES))
    return out
