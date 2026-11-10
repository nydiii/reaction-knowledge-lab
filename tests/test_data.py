"""Integrity and scientific identity checks for the published teaching data."""

import csv
import hashlib
import json
from pathlib import Path

import pytest
from rdkit import Chem


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPLAY_HASHES = {
    "data/replay/upstream_output_table.csv":
        "176b004ba00bef39e14b8cb6d9f620954c051180f5cde0832b0f3768dffbdc97",
    "data/replay/upstream_output_summary.csv":
        "ab9d974ce3e5d74fc24a4b5bacac67df6c3b330e2df9f0d55ebfcffec7d906e9",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.mark.parametrize("relative_path,expected", REPLAY_HASHES.items())
def test_bundled_replay_is_unchanged_pinned_upstream_data(relative_path, expected):
    actual = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
    assert actual == expected
    manifest = read_json(DATA / "sources.json")
    assert manifest["upstream"]["commit"] == "6d42c4a1c5e47e1a5544b67a5b3ce9b00dbf8f6a"
    entry = next(item for item in manifest["bundled_files"] if item["path"] == relative_path)
    assert entry["sha256"] == expected
    assert manifest["upstream"]["commit"] in entry["upstream_url"]


def test_six_candidate_rows_do_not_prove_six_correct_experiment_identities():
    rows = read_csv(DATA / "replay/upstream_output_table.csv")
    assert len(rows) == 6
    case22 = [row for row in rows if row["Index"].startswith("volume102article22_")]
    assert [row["Index"] for row in case22] == ["volume102article22_1_1"]
    assert case22[0]["Product amounts"] == "2.63 g"
    assert not any("2.62" in row["Product amounts"] for row in case22)

    # These two candidates are fractions and their total from one experiment.
    case24 = [row for row in rows if row["Index"].startswith("volume102article24_")]
    assert [row["Index"] for row in case24] == [
        "volume102article24_1_1", "volume102article24_1_2"
    ]
    assert case24[0]["Yield"] == "65%, 8%"
    assert case24[1]["Yield"] == "73%"
    assert case24[1]["Reactants"] == "N/A"
    assert case24[1]["Reaction time"] == "N/A"


def test_summary_has_five_real_answers_and_the_original_empty_placeholder():
    rows = read_csv(DATA / "replay/upstream_output_summary.csv")
    assert len(rows) == 6
    assert rows[0] == {"Index": "0", "Summary": ""}
    answers = [row for row in rows if row["Summary"].strip()]
    assert len(answers) == 5
    assert {row["Index"] for row in answers} == {
        "volume102article28_1", "volume102article24_1", "volume102article22_1",
        "volume102article17_1", "volume102article9_1",
    }


def test_reference_structures_match_verified_pubchem_identities():
    expected = {
        "pubchem:10740": "ZMYIIHDQURVDRB-UHFFFAOYSA-N",
        "pubchem:12090": "NKJIFDNZPGLLSH-UHFFFAOYSA-N",
        "pubchem:6342": "WEVYAHXRMPXWCK-UHFFFAOYSA-N",
        "pubchem:3102": "RWCCWEUUXYIKHB-UHFFFAOYSA-N",
    }
    entities = read_json(DATA / "reference/aliases.json")["entities"]
    assert {entity["entity_id"] for entity in entities} == set(expected)
    alias_to_entity = {}
    for entity in entities:
        molecule = Chem.MolFromSmiles(entity["smiles"])
        assert molecule is not None
        assert Chem.MolToInchiKey(molecule) == expected[entity["entity_id"]]
        assert entity["inchikey"] == expected[entity["entity_id"]]
        assert entity["entity_id"] == f"pubchem:{entity['pubchem_cid']}"
        assert any("pubchem.ncbi.nlm.nih.gov/compound/" in url for url in entity["sources"])
        for alias in entity["aliases"]:
            key = alias.casefold().strip()
            assert alias_to_entity.setdefault(key, entity["entity_id"]) == entity["entity_id"]
    assert alias_to_entity["acetonitrile"] == alias_to_entity["ch3cn"]
    assert alias_to_entity["1,1-diphenylethene"] == alias_to_entity["1,1-diphenylethylene"]


def test_reference_runs_share_product_but_keep_identity_and_missing_conditions():
    reference = read_json(DATA / "reference/case22.json")
    records = reference["records"]
    assert len(records) == 2
    assert {row["record_id"] for row in records} == {
        "orgsyn-102-0114-run-1", "orgsyn-102-0114-run-2"
    }
    first, second = sorted(records, key=lambda row: row["experiment_label"])
    assert first["product"]["entity_id"] == second["product"]["entity_id"] == "pubchem:3102"
    assert first["product"]["yield_percent"] == second["product"]["yield_percent"] == 72
    assert [row["product"]["mass_g"] for row in (first, second)] == [2.63, 2.62]
    assert [row["product"]["purity_percent"] for row in (first, second)] == [99.8, 98.6]
    assert first["source_id"] == second["source_id"] == reference["source_id"]
    assert all(row["status"] == "source_checked" for row in records)
    assert first["raw_record_id"] == "volume102article22_1_1"
    assert second["raw_record_id"].startswith("manual-reference:")
    assert second["inputs"] == []
    assert second["solvents"] == []
    assert second["conditions"] == {
        "raw_time": None, "time_minutes": None,
        "raw_temperature": None, "temperature_c": None,
    }


def test_reference_evidence_matches_downloaded_source_hash_and_character_ranges():
    manifest = read_json(DATA / "sources.json")
    entry = next(item for item in manifest["files"] if item["name"] == "input.json")
    source_path = DATA / "downloads" / entry["target"]
    if not source_path.is_file():
        pytest.skip(
            "Original source text is intentionally not bundled. Run the documented fetch "
            "command to download data/downloads/input.json and enable source evidence checks."
        )
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == entry["sha256"]
    reference = read_json(DATA / "reference/case22.json")
    procedure = read_json(source_path)[reference["source_id"]]["Procedure"][0]
    assert hashlib.sha256(procedure.encode("utf-8")).hexdigest() == reference["procedure_sha256"]
    evidence = reference["evidence"]
    assert {item["record_id"] for item in evidence} == {
        row["record_id"] for row in reference["records"]
    }
    assert sum(len(item["text"].split()) for item in evidence) <= 25
    for item in evidence:
        assert item["source_id"] == reference["source_id"]
        assert 0 <= item["start"] < item["end"] <= len(procedure)
        assert procedure[item["start"]:item["end"]] == item["text"]
