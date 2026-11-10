from copy import deepcopy
from datetime import datetime
import sqlite3

import pytest

from reaction_knowledge_lab.store import (
    apply_patch, build_database, get_history, get_records, query_records,
)


ENTITIES = [{
    "entity_id": "compound:benzophenone", "preferred_name": "benzophenone",
    "aliases": ["diphenyl ketone", "二苯甲酮"], "smiles": "O=C(c1ccccc1)c1ccccc1",
}]


def record(record_id="run-1", mass=2.63):
    return {
        "record_id": record_id, "source_id": "source-1", "raw_record_id": "raw-1",
        "inputs": [], "solvents": [], "conditions": {"time_minutes": None},
        "product": {"entity_id": "compound:benzophenone", "name": "benzophenone",
                    "mass_g": mass, "yield_percent": 27},
        "source": {"url": "https://www.orgsyn.org/demo.aspx?prep=v102p0114",
                   "locator": "Procedure"},
        "notes": ["This fixture is a controlled teaching error, not a source fact."],
    }


def correction(patch_id="correct-yield"):
    return {
        "patch_id": patch_id, "reason": "Restore the reported yield in the teaching fixture",
        "evidence": [{"source_id": "source-1", "locator": "Procedure; yield", "text": "72%"}],
        "changes": [{"action": "replace", "record_id": "run-1", "expected_revision": 1,
                     "set": {"product.yield_percent": 72}}],
    }


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "knowledge.sqlite"
    build_database([record()], path, ENTITIES)
    return path


def test_two_experiments_share_entity_without_record_merge(tmp_path):
    path = tmp_path / "knowledge.sqlite"
    build_database([record(), record("run-2", 2.62)], path, ENTITIES)
    rows = query_records(path, name="DIPHENYL KETONE")
    assert len(rows) == 2
    assert {row["product"]["mass_g"] for row in rows} == {2.63, 2.62}
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM record_entities").fetchone()[0] == 2
    assert len(query_records(path, name="二苯甲酮")) == 2


def test_revision_changes_query_and_keeps_complete_history(db):
    original = get_records(db)[0]
    assert query_records(db, min_yield=70) == []
    result = apply_patch(db, correction())
    assert result["status"] == "applied"
    rows = query_records(db, min_yield=70)
    assert len(rows) == 1 and rows[0]["revision"] == 2
    history = get_history(db, "run-1")
    assert history[0]["record"] == original
    assert [row["record"]["product"]["yield_percent"] for row in history] == [27, 72]
    assert history[1]["evidence"] == correction()["evidence"]
    assert datetime.fromisoformat(history[1]["created_at"]).utcoffset().total_seconds() == 0
    assert "revision" not in get_records(db)[0]


def test_same_patch_is_idempotent_but_changed_content_is_rejected(db):
    patch = correction()
    apply_patch(db, patch)
    assert apply_patch(db, deepcopy(patch))["status"] == "already_applied"
    assert len(get_history(db, "run-1")) == 2
    patch["reason"] = "Different content using the same ID"
    with pytest.raises(ValueError, match="different content"):
        apply_patch(db, patch)
    assert query_records(db)[0]["revision"] == 2


def test_failure_in_second_change_rolls_back_first_change_and_patch_log(db):
    patch = correction()
    patch["changes"].append({"action": "add", "record": record()})
    with pytest.raises(ValueError, match="already exists"):
        apply_patch(db, patch)
    assert get_records(db)[0]["product"]["yield_percent"] == 27
    assert len(get_history(db, "run-1")) == 1
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM patches").fetchone()[0] == 0


def test_old_revision_is_rejected_without_partial_update(db):
    apply_patch(db, correction())
    stale = correction("new-patch-with-old-revision")
    with pytest.raises(ValueError, match="expected_revision"):
        apply_patch(db, stale)
    assert len(get_history(db, "run-1")) == 2


@pytest.mark.parametrize("field", ["record_id", "source_id", "raw_record_id", "product.made_up"])
def test_identity_and_nonexistent_paths_are_rejected(db, field):
    patch = correction()
    patch["changes"][0]["set"] = {field: "changed"}
    with pytest.raises(ValueError):
        apply_patch(db, patch)
    assert get_records(db)[0] == record()


def test_add_retains_unknowns_and_separate_history(db):
    patch = correction()
    second = record("run-2", 2.62)
    second["raw_record_id"] = None
    patch["changes"].append({"action": "add", "record": second})
    apply_patch(db, patch)
    rows = query_records(db, name="benzophenone")
    assert [row["record_id"] for row in rows] == ["run-1", "run-2"]
    assert rows[1]["conditions"]["time_minutes"] is None
    assert rows[1]["inputs"] == []
    assert get_history(db, "run-2")[0]["record"] == second


def test_unknown_entity_rolls_back_and_existing_database_is_not_overwritten(db):
    patch = correction()
    patch["changes"][0]["set"]["product.entity_id"] = "nonexistent"
    with pytest.raises(ValueError, match="Unknown entity"):
        apply_patch(db, patch)
    assert get_records(db)[0]["product"]["yield_percent"] == 27
    with pytest.raises(FileExistsError):
        build_database([], db, [])
    assert len(get_records(db)) == 1


def test_evidence_required_and_missing_database_not_created(tmp_path, db):
    patch = correction()
    patch["evidence"] = []
    with pytest.raises(ValueError, match="evidence"):
        apply_patch(db, patch)
    patch["evidence"] = [{"source_id": "source-1", "locator": ""}]
    with pytest.raises(ValueError, match="locator"):
        apply_patch(db, patch)
    missing = tmp_path / "missing.sqlite"
    with pytest.raises(FileNotFoundError):
        get_records(missing)
    assert not missing.exists()


def test_failed_build_cleans_only_its_new_file(tmp_path):
    path = tmp_path / "failed.sqlite"
    with pytest.raises(ValueError, match="Duplicate record_id"):
        build_database([record(), record()], path, ENTITIES)
    assert not path.exists()


def test_unknown_yield_is_excluded_and_alias_link_updates_on_revision(db):
    patch = correction()
    patch["changes"][0]["set"] = {"product.yield_percent": None, "product.entity_id": None,
                                  "product.name": "unresolved product"}
    apply_patch(db, patch)
    assert query_records(db, min_yield=0) == []
    assert query_records(db, name="diphenyl ketone") == []
    assert len(query_records(db, name="unresolved product")) == 1
