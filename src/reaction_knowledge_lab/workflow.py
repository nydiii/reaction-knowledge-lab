"""Inspectable classroom steps, composed from the same functions as notebooks."""
from copy import deepcopy
from pathlib import Path

from .alignment import align_csv, entity_cache, resolve_alias
from .extraction import replay
from .files import DATA, load_records, read_json, save_records, write_json
from .ord_bridge import export_ord
from .store import apply_patch, build_database, get_history, get_records, query_records
from .validation import check_evidence, validate_records

FIRST = "orgsyn-102-0114-run-1"
SECOND = "orgsyn-102-0114-run-2"


def teaching_error_patch(db_path):
    current = next(r for r in query_records(db_path) if r["record_id"] == FIRST)
    return {"patch_id": "teaching-yield-error-v1", "teaching_injection": True,
            "reason": "教学故意注入：把72%改为27%，不是模型实际错误，也不是原文报告值。",
            "evidence": [{"source_id": "teaching-fixture", "locator": "deliberately injected error; see reason"}],
            "changes": [{"action": "replace", "record_id": FIRST, "expected_revision": current["revision"],
                         "set": {"product.yield_percent": 27.0}}]}


def reference_patch(db_path):
    """Generate an inspectable proposal from the supplied course reference.

    This is answer-assisted revision, not an automatic literature-reading model.
    The raw extraction dictionary and identity fields are never replaced.
    """
    reference = read_json(DATA / "reference/case22.json")
    current = {r["record_id"]: r for r in query_records(db_path)}
    changes = []
    for target in reference["records"]:
        old = current.get(target["record_id"])
        if old is None:
            changes.append({"action": "add", "record": deepcopy(target)})
        else:
            fields = {key: deepcopy(target[key]) for key in ("inputs", "solvents", "product", "conditions", "source", "status", "notes")
                      if old.get(key) != target.get(key)}
            if fields:
                changes.append({"action": "replace", "record_id": target["record_id"],
                                "expected_revision": old["revision"], "set": fields})
    if not changes:
        raise ValueError("当前记录已与课程参考一致，无需生成新修订；重放请使用原patch文件。")
    return {"patch_id": "source-review-v1", "reason": "依据课程参考及原文定位核对字段，补录明确报告的第二次实验；保留其未重述条件。",
            "reference_file": "data/reference/case22.json", "evidence": reference["evidence"], "changes": changes}


def validate_and_export(records, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    source = validate_records(records)
    ord_report = export_ord(records, output_dir / "ord_all_records.json")
    # A verified partial literature observation is useful in the knowledge base,
    # but is not automatically a complete ORD reaction suitable for training.
    eligible = {r["record_id"] for r in ord_report["records"] if not r["errors"]}
    export_ord([r for r in records if r["record_id"] in eligible], output_dir / "ord_structurally_ready.json")
    report = {"source_check": source, "ord": ord_report,
              "ord_structurally_ready_ids": sorted(eligible),
              "ord_incomplete_ids": sorted(r["record_id"] for r in records if r["record_id"] not in eligible),
              "note": "ORD结构合格不等于事实正确或可直接训练；需同时查看原文差异、缺失值、warnings及任务要求。"}
    write_json(output_dir / "validation.json", report)
    return report


def demo(workdir):
    workdir = Path(workdir)
    if workdir.exists() and any(workdir.iterdir()):
        raise ValueError("demo目录已包含结果；请换一个新的--workdir，或运行verify验收现有结果。")
    workdir.mkdir(parents=True, exist_ok=True)
    raw, aligned, database = workdir / "extracted.csv", workdir / "aligned.json", workdir / "knowledge.sqlite"
    replay(raw)
    align_csv(raw, aligned)
    records = load_records(aligned)
    validate_and_export(records, workdir / "01_initial")
    build_database(records, database, entity_cache())
    write_json(workdir / "query_initial.json", query_records(database, min_yield=70))
    injected = teaching_error_patch(database)
    write_json(workdir / "teaching_error.patch.json", injected)
    apply_patch(database, injected)
    validate_and_export(get_records(database), workdir / "02_injected_error")
    write_json(workdir / "query_injected.json", query_records(database, min_yield=70))
    correction = reference_patch(database)
    write_json(workdir / "source_review.patch.json", correction)
    apply_patch(database, correction)
    records = get_records(database)
    save_records(workdir / "final_records.json", records)
    validate_and_export(records, workdir / "03_reviewed")
    write_json(workdir / "query_reviewed.json", query_records(database, min_yield=70))
    write_json(workdir / "history_run1.json", get_history(database, FIRST))
    write_json(workdir / "evidence_check.json", check_evidence())
    return verify(workdir)


def verify(workdir):
    workdir = Path(workdir)
    database = workdir / "knowledge.sqlite"
    records = get_records(database)
    by_id = {r["record_id"]: r for r in records}
    history = get_history(database, FIRST)
    ord_report = read_json(workdir / "03_reviewed/validation.json")["ord"]
    initial = read_json(workdir / "01_initial/validation.json")["source_check"]
    injected = read_json(workdir / "02_injected_error/validation.json")
    before = len(history)
    replay_result = apply_patch(database, read_json(workdir / "source_review.patch.json"))
    checks = {
        "two_distinct_experiments": set(by_id) == {FIRST, SECOND},
        "shared_product_entity_not_merged": len({r["product"]["entity_id"] for r in records}) == 1 and len(records) == 2,
        "different_product_masses_preserved": sorted(r["product"]["mass_g"] for r in records) == [2.62, 2.63],
        "second_run_conditions_remain_unknown": by_id[SECOND]["conditions"]["time_minutes"] is None and by_id[SECOND]["conditions"]["temperature_c"] is None and not by_id[SECOND]["inputs"],
        "source_reference_agreement": validate_records(records)["source_reference_agreement"],
        "original_extraction_missing_run2_detected": any(i["code"] == "missing_experiment" and i["record_id"] == SECOND for i in initial["issues"]),
        "legal_but_wrong_yield_detected": any(i["code"] == "source_mismatch" and i.get("field") == "product.yield_percent" for i in injected["source_check"]["issues"]),
        "ord_does_not_validate_fact_truth": not injected["ord"]["records"][0]["errors"],
        "query_changes_after_revision": [len(read_json(workdir / f"query_{stage}.json")) for stage in ("initial", "injected", "reviewed")] == [1, 0, 2],
        "history_keeps_original_and_correction": [r["record"]["product"]["yield_percent"] for r in history] == [72, 27, 72],
        "patch_replay_is_idempotent": replay_result["status"] == "already_applied" and len(get_history(database, FIRST)) == before,
        "alias_query_finds_both_runs": len(query_records(database, name="diphenylmethanone")) == 2,
        "solvent_alias_resolves": resolve_alias("CH3CN")["entity_id"] == resolve_alias("acetonitrile")["entity_id"],
        "partial_second_run_flagged_by_ord": any(r["record_id"] == SECOND and r["errors"] for r in ord_report["records"]),
        "raw_output_is_retained": by_id[FIRST]["raw"]["Yield"] == "72%",
    }
    report = {"passed": all(checks.values()), "checks": checks,
              "evidence_check": check_evidence(), "api_calls": 0,
              "note": "验收覆盖有限课程案例，不代表论文全数据指标或完整实验条件已复现。"}
    write_json(workdir / "verification.json", report)
    return report
