import io
import json
from pathlib import Path
import urllib.error

import pytest

from reaction_knowledge_lab import extraction
from reaction_knowledge_lab.files import read_json


TABLE = """| Reactants | Reactant amounts | Products | Product amounts | Solvents | Reaction temperature | Reaction time | Yield |
|---|---|---|---|---|---|---|---|
| 1,1-diphenylethene | 20 mmol | Benzophenone | 2.63 g | acetonitrile | 35°C | 36 hours | 72% |
"""


@pytest.fixture
def api_files(tmp_path, monkeypatch):
    script = tmp_path / "GLM_evaluate.py"
    script.write_text('def get_names(title, text):\n    prompt = f"Title: {title} Procedure: {text}"\n')
    (tmp_path / "input.json").write_text(json.dumps({extraction.CASE: {"Title": "Test", "Procedure": ["Test only"]}}))
    monkeypatch.setattr(extraction, "_check_download", lambda name, directory: tmp_path / name)
    monkeypatch.setattr(extraction, "_credentials", lambda path: "unit-test-key")
    return tmp_path


def response(finish="stop", content=TABLE):
    return io.BytesIO(json.dumps({"id": "test-response", "model": "test-model", "usage": {"prompt_tokens": 100, "completion_tokens": 20},
                                "choices": [{"message": {"content": content}, "finish_reason": finish}]}).encode())


def test_parser_keeps_chemical_commas_and_rejects_broken_columns():
    assert extraction.parse_table(TABLE, extraction.CASE)[0]["Reactants"] == "1,1-diphenylethene"
    with pytest.raises(ValueError, match="列数"):
        extraction.parse_table(TABLE.replace("| 72% |", "| 72% | extra |"), extraction.CASE)
    with pytest.raises(ValueError):
        extraction.parse_table("No table available", extraction.CASE)


def test_budget_is_checked_before_request(api_files, monkeypatch):
    monkeypatch.setattr(extraction.urllib.request, "urlopen", lambda *a, **k: pytest.fail("Network must not be called"))
    with pytest.raises(ValueError, match="超过预算"):
        extraction.extract_api(api_files / "out.csv", budget_cny=0.000001)
    assert not (api_files / "out.csv").exists()


def test_api_records_usage_but_never_credentials(api_files, monkeypatch):
    def fake_request(request, **kwargs):
        body = json.loads(request.data)
        assert body["thinking"] == {"type": "disabled"}
        assert body["max_tokens"] == 2048
        assert request.full_url == "https://api.deepseek.com/chat/completions"
        return response()
    monkeypatch.setattr(extraction.urllib.request, "urlopen", fake_request)
    result = extraction.extract_api(api_files / "out.csv")
    assert result["api_calls"] == 1
    assert result["estimated_cost_cny_peak_no_cache"] == pytest.approx(0.00036)
    assert "unit-test-key" not in (api_files / "out.metadata.json").read_text()
    with pytest.raises(ValueError, match="已有结果"):
        extraction.extract_api(api_files / "out.csv")


def test_truncated_response_saved_but_not_imported(api_files, monkeypatch):
    monkeypatch.setattr(extraction.urllib.request, "urlopen", lambda *a, **k: response(finish="length"))
    with pytest.raises(ValueError, match="未正常结束"):
        extraction.extract_api(api_files / "out.csv")
    assert not (api_files / "out.csv").exists()
    assert read_json(api_files / "out.metadata.json")["status"] == "incomplete_response"


def test_http_failure_not_retried_or_leaked(api_files, monkeypatch):
    calls = []
    def fail(*args, **kwargs):
        calls.append(1)
        raise urllib.error.HTTPError("https://api.deepseek.com/chat/completions", 401, "unit-test-key", {}, None)
    monkeypatch.setattr(extraction.urllib.request, "urlopen", fail)
    with pytest.raises(RuntimeError) as failure:
        extraction.extract_api(api_files / "out.csv")
    assert "unit-test-key" not in str(failure.value)
    assert "unit-test-key" not in (api_files / "out.metadata.json").read_text()
    assert len(calls) == 1


def test_prompt_parser_does_not_execute_source(tmp_path):
    script = tmp_path / "prompt.py"
    script.write_text('raise RuntimeError("must not execute")\ndef get_names(title,text):\n    prompt=f"{title}: {text}"\n')
    assert extraction.upstream_prompt(script, "A", "B") == "A: B"
