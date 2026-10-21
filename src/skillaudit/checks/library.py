"""Cross-skill checks: duplicate names and overlapping triggers."""

from __future__ import annotations

import re
from itertools import combinations

from ..models import Finding, Severity, Skill
from .quality import metadata_tokens

STOPWORDS = frozenset(
    "a an and are as at be by can for from has have how i if in into is it its of on or "
    "that the this to use used using when with you your user users skill skills file files "
    "work working help helps need needs any all also not should will".split()
)
WORD_RE = re.compile(r"[a-z0-9][a-z0-9+#.-]*")


def keywords(text: str) -> frozenset[str]:
    words = (w.strip(".-") for w in WORD_RE.findall(text.lower()))
    return frozenset(w for w in words if len(w) > 2 and w not in STOPWORDS)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def check(skills: list[Skill], *, overlap_threshold: float = 0.5,
          budget_tokens: int = 8000) -> list[Finding]:  # fmt: skip
    out: list[Finding] = []
    valid = [s for s in skills if not s.parse_error]

    by_name: dict[str, list[Skill]] = {}
    for s in valid:
        by_name.setdefault(s.name, []).append(s)
    for name, group in by_name.items():
        if len(group) > 1:
            for s in group:
                others = ", ".join(str(o.skill_file) for o in group if o is not s)
                out.append(Finding("SA301", Severity.ERROR,
                    f"duplicate skill name {name!r} (also in {others})", s.skill_file))  # fmt: skip

    kw = {id(s): keywords(s.description) for s in valid}
    for a, b in combinations(valid, 2):
        if a.name == b.name:
            continue
        score = jaccard(kw[id(a)], kw[id(b)])
        if score >= overlap_threshold:
            out.append(Finding("SA302", Severity.WARNING,
                f"description overlaps {b.name!r} ({score:.0%} shared keywords); "
                "the agent may pick the wrong skill", a.skill_file, 1,
                "Make each description name distinct triggers."))  # fmt: skip

    total = sum(metadata_tokens(s) for s in valid)
    if total > budget_tokens and valid:
        top = max(valid, key=metadata_tokens)
        out.append(Finding("SA303", Severity.WARNING,
            f"{len(valid)} skills cost ~{total} tokens of always-loaded metadata "
            f"(budget {budget_tokens}); heaviest is {top.name!r} (~{metadata_tokens(top)})",
            top.skill_file, 1, "Trim descriptions or remove unused skills."))  # fmt: skip
    return out
