from pathlib import Path

import pytest

from skillaudit.loader import load_skill


@pytest.fixture
def make_skill(tmp_path):
    def _make(content: str, name: str = "demo", files: dict[str, str] | None = None):
        d = tmp_path / name
        d.mkdir(exist_ok=True)
        (d / "SKILL.md").write_text(content, encoding="utf-8")
        for rel, text in (files or {}).items():
            f = Path(d / rel)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text, encoding="utf-8")
        return load_skill(d / "SKILL.md")

    return _make


GOOD = "---\nname: demo\ndescription: Does a useful thing for documents. Use when the user asks about documents.\n---\n# Demo\nBody.\n"
