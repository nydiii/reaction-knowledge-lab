import hashlib
import urllib.error

import pytest

from reaction_knowledge_lab import batch_sources


@pytest.fixture
def source(monkeypatch):
    body = b"%PDF-1.3\ncourse source fixture\n%%EOF"
    item = {"name": "jacs2024-si.pdf", "url": "https://example.org/source.pdf",
            "sha256": hashlib.sha256(body).hexdigest()}
    monkeypatch.setattr(batch_sources, "manifest", lambda: {"files": [item]})
    return item, body


@pytest.mark.parametrize("error, expected", [
    (urllib.error.HTTPError("https://example.org/source.pdf", 403, "Forbidden", {}, None), "HTTP 403: Forbidden"),
    (urllib.error.URLError(TimeoutError("timed out")), "timed out"),
])
def test_download_failure_explains_cause_and_save_location(tmp_path, monkeypatch, source, error, expected):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(batch_sources.urllib.request, "urlopen", fail)
    result = batch_sources.fetch_batch(tmp_path)
    row = result["files"][0]
    assert result["passed"] is False
    assert row["status"] == "needs_download"
    assert row["error_message"] == expected
    assert row["destination"] == str(tmp_path / source[0]["name"])
    if isinstance(error, urllib.error.HTTPError):
        assert row["http_status"] == 403
    else:
        assert "http_status" not in row
    assert not (tmp_path / source[0]["name"]).exists()


def test_manual_copy_is_verified_without_downloading_again(tmp_path, monkeypatch, source):
    item, body = source
    (tmp_path / item["name"]).write_bytes(body)
    monkeypatch.setattr(batch_sources.urllib.request, "urlopen", lambda *a, **k: pytest.fail("Must reuse verified local file"))
    result = batch_sources.fetch_batch(tmp_path)
    assert result == {"passed": True, "files": [{"file": item["name"], "status": "verified"}]}


def test_wrong_local_copy_reports_hash_problem_without_overwriting(tmp_path, monkeypatch, source):
    path = tmp_path / source[0]["name"]
    path.write_bytes(b"incomplete download")
    monkeypatch.setattr(batch_sources.urllib.request, "urlopen", lambda *a, **k: pytest.fail("Must preserve local file"))
    result = batch_sources.fetch_batch(tmp_path)
    assert result["passed"] is False
    assert "本地文件哈希不一致" in result["files"][0]["error_message"]
    assert path.read_bytes() == b"incomplete download"
