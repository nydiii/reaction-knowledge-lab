import socket

import pytest

from reaction_knowledge_lab.workflow import demo, verify
from reaction_knowledge_lab.files import read_json


def test_whole_offline_course_without_network_or_key(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    def fail_network(*args, **kwargs):
        raise AssertionError("Offline demo must not open a network connection")
    monkeypatch.setattr(socket, "create_connection", fail_network)
    result = demo(tmp_path / "lab")
    assert result["passed"], result["checks"]
    assert result["api_calls"] == 0
    assert verify(tmp_path / "lab")["passed"]
    with pytest.raises(ValueError, match="目录"):
        demo(tmp_path / "lab")


def test_partial_observation_is_kept_but_not_complete_ord(tmp_path):
    demo(tmp_path / "lab")
    report = read_json(tmp_path / "lab/03_reviewed/validation.json")
    assert report["source_check"]["source_reference_agreement"]
    assert report["ord_structurally_ready_ids"] == ["orgsyn-102-0114-run-1"]
    assert report["ord_incomplete_ids"] == ["orgsyn-102-0114-run-2"]
