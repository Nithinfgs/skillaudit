# Contributing

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest
```

- Add a rule: implement it in `src/skillaudit/checks/`, register its id in `src/skillaudit/rules.py`, add a test in `tests/`.
- Security rules are heuristics. Every new pattern needs a positive test and a benign-text test so false positives stay low.
- Keep runtime dependencies at zero (standard library only).
