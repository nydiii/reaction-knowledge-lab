"""Export course records through the real ORD schema and validation library.

This is a course adapter, not an implementation of scientific fact verification.
The complete course record remains in ORD metadata, including unknowns and ranges.
"""

from importlib.metadata import version
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from ord_schema import datasets, message_helpers, validations
from ord_schema.proto import dataset_pb2, reaction_pb2


COURSE_TIMESTAMP = "2026-11-10T00:00:00+00:00"
DATASET_ID = "ord_dataset-" + uuid5(
    NAMESPACE_URL, "reaction-knowledge-lab:dataset"
).hex


def _ord_id(record_id: str) -> str:
    return "ord-" + uuid5(NAMESPACE_URL, f"reaction-knowledge-lab:{record_id}").hex


def _input_component(item: dict, default_role: str) -> reaction_pb2.Compound:
    role = str(item.get("role") or default_role).upper()
    compound = message_helpers.build_compound(
        name=item.get("name"), smiles=item.get("smiles"), role=role
    )
    amount = item.get("amount") or {}
    if amount.get("value") is not None and amount.get("unit"):
        # Keep the normalized amount's stated dimension. Do not derive quantities
        # from molecular weights or infer a missing solvent volume.
        measured = message_helpers.build_compound(
            amount=f"{amount['value']} {amount['unit']}"
        )
        compound.amount.CopyFrom(measured.amount)
    else:
        compound.amount.unmeasured.type = reaction_pb2.UnmeasuredAmount.CUSTOM
        compound.amount.unmeasured.details = (
            "Unknown: amount was not supplied in this course record. "
            "This is a missing-data marker, not an experimental measurement."
        )
    return compound


def to_ord(record: dict) -> reaction_pb2.Reaction:
    """Convert one record without filling in absent experimental facts."""
    record_id = record.get("record_id")
    if not isinstance(record_id, str) or not record_id:
        raise ValueError("A nonempty record_id is required for a stable ORD ID")
    reaction = reaction_pb2.Reaction(reaction_id=_ord_id(record_id))
    reaction.identifiers.add(
        type="CUSTOM", details="course_record_id", value=record_id
    )
    for group, role in (("inputs", "REACTANT"), ("solvents", "SOLVENT")):
        for index, item in enumerate(record.get(group) or []):
            pooled = record.get('record_kind') == 'pooled_result'
            component = _input_component({**item, 'amount':None} if pooled else item, role)
            if pooled:
                component.amount.unmeasured.details = (
                    'Pooled product result: source input amounts are per run, not a confirmed total. '
                    'Original per-run quantities and replicate count are retained in course_record metadata.'
                )
            reaction.inputs[f"{group}_{index}"].components.add().CopyFrom(component)
    if record.get('record_kind') == 'pooled_result':
        reaction.notes.procedure_details = (
            f"Pooled result from {record.get('replicates')} reported runs. Product mass/yield describe "
            'combined material; native input amounts intentionally unset to avoid mixing per-run and pooled quantities.'
        )

    outcome = reaction.outcomes.add()
    conditions = record.get("conditions") or {}
    if conditions.get("time_minutes") is not None:
        outcome.reaction_time.CopyFrom(
            reaction_pb2.Time(value=conditions["time_minutes"], units="MINUTE")
        )
    temperature = conditions.get("temperature_c") or {}
    lower, upper = temperature.get("min"), temperature.get("max")
    if lower is not None and lower == upper:
        reaction.conditions.temperature.setpoint.CopyFrom(
            reaction_pb2.Temperature(value=lower, units="CELSIUS")
        )
    # ORD has no interval-valued setpoint. An interval is not measurement error
    # and must not become a midpoint or a fabricated time series.
    if lower is not None and upper is not None and lower != upper:
        reaction.notes.procedure_details = (
            f"Reported temperature range: {lower} to {upper} deg C; "
            "no single setpoint inferred. Original values and wording are in "
            "provenance.reaction_metadata.course_record."
        )

    reported_product = record.get("product") or {}
    if reported_product:
        product = outcome.products.add(reaction_role="PRODUCT")
        if reported_product.get("name"):
            product.identifiers.add(type="NAME", value=reported_product["name"])
        if reported_product.get("smiles"):
            product.identifiers.add(type="SMILES", value=reported_product["smiles"])
        for field, kind in (("yield_percent", "YIELD"), ("purity_percent", "PURITY")):
            if reported_product.get(field) is not None:
                product.measurements.add(
                    type=kind,
                    percentage=reaction_pb2.Percentage(value=reported_product[field]),
                )
        if reported_product.get("mass_g") is not None:
            measured = product.measurements.add(type="AMOUNT")
            measured.amount.mass.CopyFrom(
                reaction_pb2.Mass(value=reported_product["mass_g"], units="GRAM")
            )
        # Unknown analysis methods intentionally remain unknown. ORD may issue
        # analysis_key warnings, which are returned to students unchanged.

    source = record.get("source") or {}
    reaction.provenance.publication_url = source.get("url") or ""
    reaction.provenance.doi = source.get("doi") or ""
    reaction.provenance.is_mined = True
    created = reaction.provenance.record_created
    created.time.value = COURSE_TIMESTAMP
    created.person.name = "Reaction Knowledge Lab course exporter (not experimenter)"
    created.person.email = "course@example.invalid"
    metadata = reaction.provenance.reaction_metadata["course_record"]
    metadata.string_value = json.dumps(record, ensure_ascii=False, allow_nan=False)
    metadata.format = "application/json"
    export = reaction.provenance.reaction_metadata["course_export"]
    export.string_value = json.dumps(
        {
            "adapter": "reaction-knowledge-lab",
            "timestamp": COURSE_TIMESTAMP,
            "timestamp_meaning": "fixed course export reference, not experiment time",
            "creator_meaning": "software exporter, not experimental author",
        }
    )
    export.format = "application/json"
    return reaction


def export_ord(records: list[dict], output_path: Path) -> dict:
    """Write an ORD Dataset JSON and report its actual errors and warnings.

    Records with missing experimental information are exported and reported as
    such. Passing this check never asserts agreement with the source literature.
    """
    dataset = dataset_pb2.Dataset(
        dataset_id=DATASET_ID,
        name="Reaction Knowledge Lab: traceable classroom reaction records",
        description=(
            "Course export of extracted and reviewed records; see per-record "
            "metadata for source, original fields, and review status."
        ),
    )
    options = validations.ValidationOptions(validate_ids=True)
    reports = []
    for record in records:
        reaction = to_ord(record)
        dataset.reactions.append(reaction)
        result = validations.validate_message(
            reaction, raise_on_error=False, options=options
        )
        reports.append(
            {
                "record_id": record["record_id"],
                "ord_id": reaction.reaction_id,
                "errors": result.errors,
                "warnings": result.warnings,
            }
        )
    result = validations.validate_message(dataset, raise_on_error=False, options=options)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    datasets.save_dataset(dataset, str(output_path))
    return {
        "dataset_id": DATASET_ID,
        "record_count": len(records),
        "ord_schema_version": version("ord-schema"),
        "output_path": str(output_path),
        "records": reports,
        "dataset_errors": result.errors,
        "dataset_warnings": result.warnings,
    }
