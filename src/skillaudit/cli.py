"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, reporters
from .config import ConfigError
from .config import load as load_config
from .engine import audit
from .models import Severity
from .rules import RULES

EXIT_OK, EXIT_FINDINGS, EXIT_USAGE = 0, 1, 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="skillaudit",
        description="Lint and security-audit agent skills (SKILL.md) before you install or ship them.",
    )
    p.add_argument("--version", action="version", version=f"skillaudit {__version__}")
    sub = p.add_subparsers(dest="command")

    chk = sub.add_parser("check", help="audit skills (default command)")
    chk.add_argument("paths", nargs="*", type=Path,
                     help="skill dirs or SKILL.md files (default: .claude/skills, .agents/skills, skills)")  # fmt: skip
    chk.add_argument("-f", "--format", choices=["text", "json", "sarif", "github"], default="text")
    chk.add_argument("--fail-on", choices=["error", "warning", "info"],
                     help="lowest severity that makes the exit code non-zero (default: error)")  # fmt: skip
    chk.add_argument("--ignore", action="append", default=[], metavar="RULE",
                     help="rule id to disable (repeatable)")  # fmt: skip
    chk.add_argument("--config", type=Path, help="path to a .skillaudit.toml")
    chk.add_argument("-o", "--output", type=Path, help="write the report to a file")

    sub.add_parser("rules", help="list all rules")
    return p


def _cmd_rules() -> int:
    for rid, (sev, desc) in sorted(RULES.items()):
        print(f"{rid}  {sev:<8} {desc}")
    return EXIT_OK


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"skillaudit: config error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    unknown = [r for r in args.ignore if r.upper() not in RULES]
    if unknown:
        print(f"skillaudit: unknown rule id(s): {', '.join(unknown)}", file=sys.stderr)
        return EXIT_USAGE
    config.ignore |= {r.upper() for r in args.ignore}
    if args.fail_on:
        config.fail_on = Severity.parse(args.fail_on)

    for path in args.paths:
        if not path.exists():
            print(f"skillaudit: path does not exist: {path}", file=sys.stderr)
            return EXIT_USAGE

    skills, findings = audit(args.paths, config)
    if not skills:
        print("skillaudit: no SKILL.md files found", file=sys.stderr)
        return EXIT_USAGE

    if args.format == "json":
        report = reporters.as_json(len(skills), findings)
    elif args.format == "sarif":
        report = reporters.sarif(findings)
    elif args.format == "github":
        report = reporters.github(findings)
    else:
        color = reporters.use_color(sys.stdout.isatty()) and not args.output
        report = reporters.text(len(skills), findings, color)

    if args.output:
        try:
            args.output.write_text(report + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"skillaudit: cannot write {args.output}: {exc}", file=sys.stderr)
            return EXIT_USAGE
        print(reporters.summary_line(len(skills), findings), file=sys.stderr)
    elif report:
        print(report)

    return EXIT_FINDINGS if any(f.severity >= config.fail_on for f in findings) else EXIT_OK


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in {"check", "rules", "-h", "--help", "--version"}:
        argv.insert(0, "check")
    args = build_parser().parse_args(argv)
    if args.command == "rules":
        return _cmd_rules()
    return _cmd_check(args)
