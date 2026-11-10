"""Behavior checks for the course adapter against the actual ORD library."""

from copy import deepcopy
import json

from ord_schema import datasets

from reaction_knowledge_lab.ord_bridge import export_ord, to_ord


def course_record():
    return {
        "record_id": "ord-adapter-test-run-1",
        "source_id": "volume102article22",
        "inputs": [
            {
                "name": "1,1-diphenylethene",
                "smiles": "C=C(c1ccccc1)c1ccccc1",
                "role": "reactant",
                "amount": {"value": 20.0, "unit": "mmol"},
                "raw_amount": "3.61 g (20.0 mmol)",
            }
        ],
        "solvents": [{"name": "acetonitrile", "smiles": "CC#N"}],
        "product": {
            "name": "benzophenone",
            "smiles": "O=C(c1ccccc1)c1ccccc1",
            "mass_g": 2.63,
            "yield_percent": 72.0,
            "purity_percent": None,
        },
        "conditions": {
            "raw_time": "36 hours",
            "time_minutes": 2160.0,
            "raw_temperature": "30-35°C",
            "temperature_c": {"min": 30.0, "max": 35.0},
        },
        "source": {
            "url": "https://www.orgsyn.org/demo.aspx?prep=v102p0114",
            "doi": "10.15227/orgsyn.102.0114",
            "locator": "Procedure; first run",
        },
        "status": "test_fixture",
    }


def test_ord_roundtrip_keeps_original_record_range_and_unknown_amount(tmp_path):
    record = course_record()
    path = tmp_path / "dataset.json"
    report = export_ord([record], path)
    assert report["records"][0]["errors"] == []
    assert report["dataset_errors"] == []
    reaction = datasets.load_dataset(str(path)).reactions[0]
    assert json.loads(
        reaction.provenance.reaction_metadata["course_record"].string_value
    ) == record
    assert not reaction.conditions.temperature.HasField("setpoint")
    assert "30.0 to 35.0" in reaction.notes.procedure_details
    solvent_amount = reaction.inputs["solvents_0"].components[0].amount
    assert solvent_amount.WhichOneof("kind") == "unmeasured"
    assert "Unknown" in solvent_amount.unmeasured.details
    assert reaction.outcomes[0].reaction_time.value == 2160
    assert any("analysis_key" in warning for warning in report["records"][0]["warnings"])


def test_repeated_export_has_stable_ids_and_distinct_experiments(tmp_path):
    one = course_record()
    two = deepcopy(one)
    two["record_id"] = "ord-adapter-test-run-2"
    two["product"]["mass_g"] = 2.62
    first = export_ord([one, two], tmp_path / "first.json")
    second = export_ord([one, two], tmp_path / "second.json")
    ids = [row["ord_id"] for row in first["records"]]
    assert ids == [row["ord_id"] for row in second["records"]]
    assert len(set(ids)) == 2
    assert datasets.load_dataset(str(tmp_path / "first.json")) == datasets.load_dataset(
        str(tmp_path / "second.json")
    )


def test_missing_inputs_remain_missing_and_produce_an_ord_error(tmp_path):
    record = course_record()
    record["inputs"], record["solvents"] = [], []
    record["conditions"] = {"time_minutes": None, "temperature_c": None}
    report = export_ord([record], tmp_path / "missing.json")
    assert any("at least 1 reaction input" in error for error in report["records"][0]["errors"])
    reaction = datasets.load_dataset(str(tmp_path / "missing.json")).reactions[0]
    assert len(reaction.inputs) == 0
    assert not reaction.outcomes[0].HasField("reaction_time")


def test_out_of_range_yield_is_an_ord_warning_not_a_claim_of_truth(tmp_path):
    record = course_record()
    record["product"]["yield_percent"] = 172
    report = export_ord([record], tmp_path / "yield.json")
    assert any(
        "outside the expected range" in warning
        for warning in report["records"][0]["warnings"]
    )
    record["product"]["yield_percent"] = 27
    report = export_ord([record], tmp_path / "plausible_wrong_yield.json")
    assert report["records"][0]["errors"] == []
    assert not any(
        "outside the expected range" in warning
        for warning in report["records"][0]["warnings"]
    )


def test_unknown_time_not_guessed_and_point_temperature_exported():
    record = course_record()
    record["conditions"].update(raw_time="overnight", time_minutes=None)
    record["conditions"]["temperature_c"] = {"min": 25, "max": 25}
    reaction = to_ord(record)
    assert not reaction.outcomes[0].HasField("reaction_time")
    assert reaction.conditions.temperature.setpoint.value == 25


def test_duplicate_record_ids_are_reported_by_ord(tmp_path):
    record = course_record()
    report = export_ord([record, deepcopy(record)], tmp_path / "duplicate.json")
    assert any("same IDs" in error for error in report["dataset_errors"])


def test_invalid_structure_is_reported_by_real_ord_validator(tmp_path):
    record = course_record()
    record["product"]["smiles"] = "not-a-valid-smiles"
    report = export_ord([record], tmp_path / "bad_structure.json")
    assert any("RDKit" in error for error in report["records"][0]["errors"])
