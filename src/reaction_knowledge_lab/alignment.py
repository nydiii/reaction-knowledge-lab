"""Course adaptation of ReactionSeek name/structure and unit standardization.

The four-entity identity cache has explicit references. This is intentionally a
bounded classroom case, not an automatic resolver for arbitrary chemistry.
"""
import csv
from pathlib import Path
import re
import unicodedata

from rdkit import Chem

from .extraction import CASE
from .files import DATA, read_json, save_records, write_json


def normalize_name(name):
    return " ".join(unicodedata.normalize("NFKC", name).casefold().strip().split())


def entity_cache():
    return read_json(DATA / "reference/aliases.json")["entities"]


def resolve_alias(name, entities=None):
    entities = entities if entities is not None else entity_cache()
    key = normalize_name(name)
    matches = [e for e in entities if key in {normalize_name(a) for a in e["aliases"]}]
    if not matches:
        return {"name": name, "entity_id": None, "smiles": None, "resolution_status": "unresolved"}
    if len(matches) != 1:
        raise ValueError(f"名称映射存在歧义：{name}")
    entity = matches[0]
    molecule = Chem.MolFromSmiles(entity["smiles"])
    if molecule is None:
        raise ValueError(f"结构缓存中的SMILES无效：{entity['entity_id']}")
    return {"name": name, "entity_id": entity["entity_id"],
            "smiles": Chem.MolToSmiles(molecule, isomericSmiles=True),
            "resolution_status": "reference_cache"}


def _split_names(text, entities):
    """Match known aliases before separating commas in chemical names."""
    normalized = normalize_name(text)
    if normalized in {"", "n/a", "na", "unknown"}:
        return []
    aliases = sorted({normalize_name(a) for e in entities for a in e["aliases"]}, key=len, reverse=True)
    expression = re.compile(r"(?<![\w-])(" + "|".join(re.escape(a) for a in aliases) + r")(?![\w-])")
    found, cursor = [], 0
    for match in expression.finditer(normalized):
        remainder = normalized[cursor:match.start()].strip(" ,;；")
        # Compound labels such as '(1)' are source references, not names.
        remainder = re.sub(r"\(\d+\)", "", remainder).strip(" ,;；")
        if remainder:
            found.append(resolve_alias(remainder, entities))
        found.append(resolve_alias(match.group(), entities))
        cursor = match.end()
    remainder = re.sub(r"\(\d+\)", "", normalized[cursor:]).strip(" ,;；")
    if remainder:
        found.append(resolve_alias(remainder, entities))
    return found


def _split_amounts(text):
    pieces, start, depth = [], 0, 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char in ",;" and depth == 0:
            pieces.append(text[start:index].strip())
            start = index + 1
    pieces.append(text[start:].strip())
    return pieces


def parse_amount(text):
    # Prefer an explicitly reported molar amount, without deriving from mass.
    if _qualified_quantity(text):
        return None
    for unit in ("mmol", "mol", "mg", "g", "mL", "L"):
        values = re.findall(r"(?<![\w.])([0-9]+(?:\.[0-9]+)?)\s*" + re.escape(unit) + r"\b", text)
        if len(values) == 1:
            return {"value": float(values[0]), "unit": unit}
    return None


def time_minutes(text):
    if text is None:
        return None
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(seconds?|s|minutes?|mins?|min|hours?|hrs?|h|days?|d)\s*", text, re.I)
    if not match:
        return None
    value, unit = float(match[1]), match[2].lower()
    factor = 1/60 if unit.startswith("s") else 1 if unit.startswith("m") else 60 if unit.startswith("h") else 1440
    return value * factor


def temperature_range(text):
    if text is None:
        return None
    value = unicodedata.normalize("NFKC", text).replace("−", "-")
    number = r"(-?\d+(?:\.\d+)?)"
    match = re.fullmatch(r"\s*" + number + r"\s*(?:[-–—]|to)\s*" + number + r"\s*°?\s*C\s*", value, re.I)
    if match:
        return {"min": min(float(match[1]), float(match[2])), "max": max(float(match[1]), float(match[2]))}
    match = re.fullmatch(r"\s*" + number + r"\s*°?\s*C\s*", value, re.I)
    return {"min": float(match[1]), "max": float(match[1])} if match else None


def _single_number(text, unit):
    if _qualified_quantity(text):
        return None
    values = re.findall(r"(?<![\d.])(\d+(?:\.\d+)?)\s*" + unit, text)
    return float(values[0]) if len(values) == 1 else None


def _qualified_quantity(text):
    # This course parser handles exact nonnegative quantities only. Preserve
    # uncertainty and qualifiers in raw text instead of dropping their meaning.
    return bool(re.search(r"\d\s*(?:[-–—]|to)\s*\d|[<>≤≥±~≈]|[-−]\s*\d|\b(?:about|approximately|circa)\b", text, re.I))


def align_csv(input_path, output_path):
    entities = entity_cache()
    source = next(s for s in read_json(DATA / "sources.json")["sources"] if s["source_id"] == CASE)
    with Path(input_path).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("输入CSV没有记录。")
    if any(not row.get("Index", "").startswith(CASE + "_1_") for row in rows):
        raise ValueError("必做适配器仅支持article22的第一段procedure；其他四篇需人工设计实验身份映射，不能自动套用。")
    records, mappings = [], []
    for row in rows:
        # This provisional identity is reviewed against the source in the next
        # stage. It is not deduplicated by molecule or inferred from yield.
        ordinal = int(row["Index"].rsplit("_", 1)[-1])
        record_id = f"orgsyn-102-0114-run-{ordinal}"
        inputs = _split_names(row["Reactants"], entities)
        amounts = _split_amounts(row["Reactant amounts"])
        notes = ["实验编号暂按单篇表格行顺序对应，必须通过下一步原文参考核对；不按分子结构合并实验。"]
        for index, item in enumerate(inputs):
            raw_amount = amounts[index] if len(amounts) == len(inputs) else None
            item.update(role="reactant", amount=parse_amount(raw_amount) if raw_amount else None,
                        raw_amount=raw_amount)
        if len(amounts) != len(inputs):
            notes.append("物质与用量个数不一致，未自动配对；完整原值保留在raw。")
        solvents = _split_names(row["Solvents"], entities)
        product = resolve_alias(row["Products"], entities)
        product.update(mass_g=_single_number(row["Product amounts"], r"g\b"),
                       yield_percent=_single_number(row["Yield"], "%"), purity_percent=None)
        conditions = {"raw_time": row["Reaction time"], "time_minutes": time_minutes(row["Reaction time"]),
                      "raw_temperature": row["Reaction temperature"], "temperature_c": temperature_range(row["Reaction temperature"])}
        record = {"record_id": record_id, "source_id": CASE, "raw_record_id": row["Index"],
                  "experiment_label": f"run-{ordinal}", "status": "extracted", "inputs": inputs,
                  "solvents": solvents, "product": product, "conditions": conditions,
                  "source": {"doi": source["doi"], "url": source["url"], "locator": f"ReactionSeek row {row['Index']}; provisional run-{ordinal}"},
                  "notes": notes, "raw": row}
        records.append(record)
        for role, items in (("reactant", inputs), ("solvent", solvents), ("product", [product])):
            mappings.extend({"record_id": record_id, "raw_record_id": row["Index"], "role": role,
                             "name": item["name"], "entity_id": item["entity_id"], "status": item["resolution_status"]} for item in items)
    if len({r["record_id"] for r in records}) != len(records):
        raise ValueError("重复候选ID；没有自动去重或覆盖。")
    save_records(output_path, records)
    write_json(Path(output_path).with_suffix(".mapping.json"), {"mappings": mappings})
    return {"record_count": len(records), "entity_count": len({x["entity_id"] for x in mappings if x["entity_id"]}),
            "unresolved_names": [x for x in mappings if x["entity_id"] is None]}
