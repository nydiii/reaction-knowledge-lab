import json
import os
import subprocess
import sys

from reaction_knowledge_lab.files import ROOT


def test_cli_reports_results_and_errors_with_legacy_terminal_encoding(tmp_path):
    command = [sys.executable, "-m", "reaction_knowledge_lab", "demo", "--workdir", str(tmp_path / "demo")]
    environment = dict(os.environ, PYTHONIOENCODING="cp1252")
    result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["passed"] is True
    assert "课程案例" in result.stdout

    repeated = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, encoding="utf-8")
    assert repeated.returncode == 2
    assert "操作未完成" in repeated.stderr
    assert "UnicodeEncodeError" not in repeated.stderr


def test_notebook_runner_reports_existing_workdir_with_legacy_encoding(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    marker = existing / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_notebooks.py"), "--workdir", str(existing)],
        cwd=ROOT, env=dict(os.environ, PYTHONIOENCODING="cp1252"),
        capture_output=True, encoding="utf-8",
    )
    assert result.returncode == 2
    assert "拒绝覆盖" in result.stderr
    assert "UnicodeEncodeError" not in result.stderr
    assert marker.read_text(encoding="utf-8") == "keep"
