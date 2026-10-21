"""Configuration from ``.skillaudit.toml`` / ``pyproject.toml``."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .models import Severity

CONFIG_NAMES = (".skillaudit.toml",)


class ConfigError(ValueError):
    pass


@dataclass
class Config:
    ignore: set[str] = field(default_factory=set)
    fail_on: Severity = Severity.ERROR
    overlap_threshold: float = 0.5
    metadata_budget_tokens: int = 8000


def _from_table(table: dict[str, object]) -> Config:
    cfg = Config()
    known = {"ignore", "fail-on", "overlap-threshold", "metadata-budget-tokens"}
    unknown = set(table) - known
    if unknown:
        raise ConfigError(f"unknown config keys: {', '.join(sorted(unknown))}")
    ignore = table.get("ignore", [])
    if not isinstance(ignore, list) or not all(isinstance(i, str) for i in ignore):
        raise ConfigError("'ignore' must be a list of rule ids")
    cfg.ignore = {i.upper() for i in ignore}
    if "fail-on" in table:
        try:
            cfg.fail_on = Severity.parse(str(table["fail-on"]))
        except ValueError as exc:
            raise ConfigError(str(exc)) from exc
    threshold = table.get("overlap-threshold", cfg.overlap_threshold)
    if not isinstance(threshold, (int, float)) or not 0 < threshold <= 1:
        raise ConfigError("'overlap-threshold' must be a number in (0, 1]")
    cfg.overlap_threshold = float(threshold)
    budget = table.get("metadata-budget-tokens", cfg.metadata_budget_tokens)
    if not isinstance(budget, int) or budget <= 0:
        raise ConfigError("'metadata-budget-tokens' must be a positive integer")
    cfg.metadata_budget_tokens = budget
    return cfg


def load(path: Path | None = None, cwd: Path | None = None) -> Config:
    base = cwd or Path.cwd()
    candidates = [path] if path else [base / n for n in CONFIG_NAMES]
    for candidate in candidates:
        if candidate is None or not candidate.is_file():
            if path:
                raise ConfigError(f"config file not found: {path}")
            continue
        try:
            data = tomllib.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ConfigError(f"cannot read {candidate}: {exc}") from exc
        return _from_table(data.get("skillaudit", data) if candidate.name == "pyproject.toml" else data)
    return Config()
