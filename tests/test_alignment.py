import copy
import csv

from reaction_knowledge_lab.alignment import align_csv, resolve_alias, temperature_range, time_minutes, parse_amount, _single_number
from reaction_knowledge_lab.extraction import replay
from reaction_knowledge_lab.files import DATA, read_json, load_records
from reaction_knowledge_lab.validation import validate_records


def test_real_aliases_match_but_unknown_stays_unknown():
    assert resolve_alias("CH3CN")["entity_id"] == resolve_alias("acetonitrile")["entity_id"]
    assert resolve_alias("1,1-Diphenylethylene")["entity_id"] == resolve_alias("1,1-diphenylethene")["entity_id"]
    assert resolve_alias("some nitrile")["entity_id"] is None


def test_unknown_and_range_are_not_invented():
    assert time_minutes("36 hours") == 2160
    assert time_minutes("overnight") is None
    assert time_minutes("5 days, 1 hour") is None
    assert temperature_range("30–35°C") == {"min": 30, "max": 35}
    assert temperature_range("-15 to -16 ℃") == {"min": -16, "max": -15}
    assert temperature_range("ambient") is None


def test_real_replay_preserves_comma_in_chemical_name(tmp_path):
    raw, normalized = tmp_path / "raw.csv", tmp_path / "records.json"
    replay(raw)
    report = align_csv(raw, normalized)
    record = load_records(normalized)[0]
    assert report["unresolved_names"] == []
    assert len(record["inputs"]) == 2
    assert record["inputs"][0]["name"] == "1,1-diphenylethene"
    assert record["inputs"][0]["amount"] == {"value": 20, "unit": "mmol"}
    assert record["raw"]["Product amounts"] == "2.63 g"
    assert record["product"]["mass_g"] == 2.63
    assert record["conditions"]["temperature_c"] == {"min": 30, "max": 35}
    report = validate_records([record])
    assert any(i["code"] == "missing_experiment" for i in report["issues"])
    assert any(i["code"] == "missing_field" and i["field"] == "product.purity_percent" for i in report["issues"])


def test_valid_percentage_can_still_disagree_with_source():
    records = copy.deepcopy(read_json(DATA / "reference/case22.json")["records"])
    assert validate_records(records)["source_reference_agreement"]
    records[0]["product"]["yield_percent"] = 27
    issues = validate_records(records)["issues"]
    assert any(i["code"] == "source_mismatch" for i in issues)
    assert not any(i["code"] == "percentage_out_of_range" for i in issues)


def test_second_experiment_conditions_cannot_be_inherited():
    records = copy.deepcopy(read_json(DATA / "reference/case22.json")["records"])
    records[1]["conditions"] = records[0]["conditions"]
    assert any(i["code"] == "source_mismatch" for i in validate_records(records)["issues"])


def test_uncertainty_limits_and_negative_values_do_not_become_exact_positive_values():
    for value in ("20 ± 2 mmol", "<20 mmol", "-20 mmol", "approximately 20 mmol", "20–30 mmol"):
        assert parse_amount(value) is None
    for value in ("72 ± 3%", "-27%", ">72%", "70–75%"):
        assert _single_number(value, "%") is None


def test_wrong_source_and_role_are_not_reference_agreement():
    for field, value in (("source_id", "unrelated"), ("doi", "10.1000/unrelated"), ("url", "https://example.org/unrelated"), ("role", "catalyst")):
        records = copy.deepcopy(read_json(DATA / "reference/case22.json")["records"])
        if field == "source_id":
            records[0][field] = value
        elif field == "role":
            records[0]["inputs"][0][field] = value
        else:
            records[0]["source"][field] = value
        assert not validate_records(records)["source_reference_agreement"]


def test_duplicate_entity_with_missing_amount_reports_difference_without_crashing():
    records = copy.deepcopy(read_json(DATA / "reference/case22.json")["records"])
    duplicate = copy.deepcopy(records[0]["inputs"][0])
    duplicate["amount"] = None
    records[0]["inputs"].append(duplicate)
    assert any(i["code"] == "source_mismatch" and i.get("field") == "inputs" for i in validate_records(records)["issues"])
