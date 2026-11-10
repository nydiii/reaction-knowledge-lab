"""Separate record rules, source-reference comparisons, and evidence lookup."""
import hashlib
import math
from pathlib import Path

from rdkit import Chem

from .alignment import entity_cache
from .files import DATA, read_json

CHECK_FIELDS = ["product.entity_id", "product.mass_g", "product.yield_percent",
                "product.purity_percent", "conditions.time_minutes", "conditions.temperature_c"]


def get_field(record, path):
    value = record
    for part in path.split("."):
        if isinstance(value, list):
            value = value[int(part)] if int(part) < len(value) else None
        elif isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def validate_records(records, reference=None):
    reference = reference or read_json(DATA / "reference/case22.json")
    issues = []
    expected = {r["record_id"]: r for r in reference["records"]}
    actual = {r["record_id"]: r for r in records}
    entities = {e["entity_id"]: Chem.MolToSmiles(Chem.MolFromSmiles(e["smiles"]), isomericSmiles=True) for e in entity_cache()}
    if len(actual) != len(records):
        issues.append({"code": "duplicate_record_id", "severity": "error"})
    for record in records:
        record_id = record["record_id"]
        for field in ("product.yield_percent", "product.purity_percent"):
            value = get_field(record, field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100):
                issues.append({"code": "percentage_out_of_range", "severity": "error", "record_id": record_id, "field": field, "actual": value})
        for item in record.get("inputs", []) + record.get("solvents", []) + [record.get("product", {})]:
            if not item.get("entity_id") or not item.get("smiles"):
                issues.append({"code": "unresolved_entity", "severity": "warning", "record_id": record_id, "name": item.get("name")})
            elif Chem.MolFromSmiles(item["smiles"]) is None:
                issues.append({"code": "invalid_smiles", "severity": "error", "record_id": record_id, "name": item.get("name")})
            elif item["entity_id"] in entities and Chem.MolToSmiles(Chem.MolFromSmiles(item["smiles"]), isomericSmiles=True) != entities[item["entity_id"]]:
                issues.append({"code": "entity_structure_conflict", "severity": "error", "record_id": record_id, "name": item.get("name")})
        if not record.get("source", {}).get("doi"):
            issues.append({"code": "missing_provenance", "severity": "error", "record_id": record_id})
        if record_id not in expected:
            issues.append({"code": "unmatched_record", "severity": "warning", "record_id": record_id})
            continue
        for field in ("source_id", "source.doi", "source.url"):
            if get_field(record, field) != get_field(expected[record_id], field):
                issues.append({"code": "source_identity_mismatch", "severity": "error", "record_id": record_id, "field": field,
                               "actual": get_field(record, field), "expected": get_field(expected[record_id], field)})
        for field in CHECK_FIELDS:
            wanted, observed = get_field(expected[record_id], field), get_field(record, field)
            if wanted != observed:
                issues.append({"code": "source_mismatch" if observed is not None else "missing_field",
                               "severity": "error" if observed is not None else "warning", "record_id": record_id,
                               "field": field, "expected": wanted, "actual": observed,
                               "evidence": [e for e in reference["evidence"] if e["record_id"] == record_id and (e["field"] == field or e["field"].startswith(field + "."))]})
        if not expected[record_id]["inputs"] and record.get("inputs"):
            issues.append({"code": "unreported_inputs_inferred", "severity": "error", "record_id": record_id})
        if not expected[record_id]["solvents"] and record.get("solvents"):
            issues.append({"code": "unreported_solvent_inferred", "severity": "error", "record_id": record_id})
        if expected[record_id]["inputs"]:
            def signature(items):
                values = [(x.get("entity_id") or "", (x.get("amount") or {}).get("value"),
                           (x.get("amount") or {}).get("unit"), x.get("role")) for x in items]
                return sorted(values, key=repr)
            if signature(record.get("inputs", [])) != signature(expected[record_id]["inputs"]):
                issues.append({"code": "source_mismatch", "severity": "error", "record_id": record_id, "field": "inputs"})
        if expected[record_id]["solvents"]:
            if sorted(x.get("entity_id") or "" for x in record.get("solvents", [])) != sorted(x.get("entity_id") or "" for x in expected[record_id]["solvents"]):
                issues.append({"code": "source_mismatch", "severity": "error", "record_id": record_id, "field": "solvents"})
    for record_id in expected.keys() - actual.keys():
        issues.append({"code": "missing_experiment", "severity": "error", "record_id": record_id,
                       "evidence": [e for e in reference["evidence"] if e["record_id"] == record_id]})
    return {"record_count": len(records), "reference_record_count": len(expected), "issues": issues,
            "source_reference_agreement": not issues,
            "scope": "bounded course reference comparison; not an autonomous verifier of arbitrary literature"}


def check_evidence(input_path=None):
    input_path = Path(input_path or DATA / "downloads/input.json")
    reference = read_json(DATA / "reference/case22.json")
    if not input_path.exists():
        return {"status": "not_checked", "reason": "原文未下载；离线回放仍可运行，但不能声称已重新核对原文定位。"}
    text = read_json(input_path)[reference["source_id"]]["Procedure"][0]
    if hashlib.sha256(text.encode()).hexdigest() != reference["procedure_sha256"]:
        raise ValueError("原文procedure哈希改变；不能沿用旧证据位置。")
    for evidence in reference["evidence"]:
        if text[evidence["start"]:evidence["end"]] != evidence["text"]:
            raise ValueError(f"证据位置不一致：{evidence['record_id']} / {evidence['field']}")
    return {"status": "verified", "evidence_count": len(reference["evidence"]), "procedure_sha256": reference["procedure_sha256"]}
