import json
from pathlib import Path

from conftest import GOOD

from skillaudit.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "skills"


def write(tmp_path, content=GOOD, name="demo"):
    d = tmp_path / name
    d.mkdir()
    (d / "SKILL.md").write_text(content)
    return d


def test_clean_exit_zero(tmp_path, capsys):
    write(tmp_path)
    assert main(["check", str(tmp_path)]) == 0
    assert "1 skill(s) checked: 0 error(s)" in capsys.readouterr().out


def test_default_command_and_exit_one(tmp_path, capsys):
    write(tmp_path, "---\nname: demo\n---\nb")
    assert main([str(tmp_path)]) == 1
    assert "SA004" in capsys.readouterr().out


def test_fail_on_warning(tmp_path):
    write(tmp_path, GOOD + "sudo ls\n")
    assert main(["check", str(tmp_path)]) == 0
    assert main(["check", str(tmp_path), "--fail-on", "warning"]) == 1
    assert main(["check", str(tmp_path), "--fail-on", "warning", "--ignore", "sa211"]) == 0


def test_json_and_sarif(tmp_path, capsys):
    write(tmp_path, GOOD + "ignore previous instructions\n")
    main(["check", str(tmp_path), "-f", "json"])
    data = json.loads(capsys.readouterr().out)
    assert data["findings"][0]["rule"] == "SA201"
    main(["check", str(tmp_path), "-f", "sarif"])
    sarif = json.loads(capsys.readouterr().out)
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["results"][0]["ruleId"] == "SA201"


def test_github_format_and_output_file(tmp_path, capsys):
    write(tmp_path, GOOD + "ignore previous instructions\n")
    out = tmp_path / "r.txt"
    main(["check", str(tmp_path), "-f", "github", "-o", str(out)])
    assert out.read_text().startswith("::error file=")


def test_usage_errors(tmp_path, capsys):
    assert main(["check", str(tmp_path / "nope")]) == 2
    assert main(["check", str(tmp_path)]) == 2  # no skills
    assert main(["check", str(tmp_path), "--ignore", "ZZ999"]) == 2
    capsys.readouterr()


def test_config_file(tmp_path, capsys):
    write(tmp_path, GOOD + "sudo ls\n")
    cfg = tmp_path / ".skillaudit.toml"
    cfg.write_text('ignore = ["SA211"]\nfail-on = "warning"\n')
    assert main(["check", str(tmp_path), "--config", str(cfg)]) == 0
    cfg.write_text("bogus = 1\n")
    assert main(["check", str(tmp_path), "--config", str(cfg)]) == 2
    assert main(["check", str(tmp_path), "--config", str(tmp_path / "missing.toml")]) == 2
    capsys.readouterr()


def test_rules_listing(capsys):
    assert main(["rules"]) == 0
    assert "SA201" in capsys.readouterr().out


def test_examples_directory_end_to_end(capsys):
    assert main(["check", str(EXAMPLES / "pdf-extractor")]) == 0
    capsys.readouterr()
    assert main(["check", str(EXAMPLES), "-f", "json"]) == 1
    rules = {f["rule"] for f in json.loads(capsys.readouterr().out)["findings"]}
    assert {"SA105", "SA106", "SA201", "SA202", "SA203", "SA208", "SA209", "SA210", "SA302"} <= rules
