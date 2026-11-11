"""Small, local knowledge store with separate entities and experiment records.

The SQLite tables and patch protocol are course code. They are not ORD features.
"""

from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3


_IDENTITY_FIELDS = {"record_id", "source_id", "raw_record_id"}
_SCHEMA = """
CREATE TABLE entities (entity_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE records (
    record_id TEXT PRIMARY KEY, revision INTEGER NOT NULL CHECK(revision > 0),
    payload TEXT NOT NULL
);
CREATE TABLE record_entities (
    record_id TEXT NOT NULL REFERENCES records(record_id),
    entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    role TEXT NOT NULL, PRIMARY KEY (record_id, entity_id, role)
);
CREATE TABLE history (
    record_id TEXT NOT NULL REFERENCES records(record_id),
    revision INTEGER NOT NULL, payload TEXT NOT NULL, reason TEXT NOT NULL,
    evidence TEXT NOT NULL, patch_id TEXT, created_at TEXT NOT NULL,
    PRIMARY KEY (record_id, revision)
);
CREATE TABLE patches (
    patch_id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, payload TEXT NOT NULL,
    applied_at TEXT NOT NULL
);
"""


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect(path: Path) -> sqlite3.Connection:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Knowledge database does not exist: {path}")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _check_record(record: dict) -> None:
    if not isinstance(record, dict):
        raise ValueError("A record must be a JSON object")
    for key in ("record_id", "source_id"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f"Record requires a nonempty {key}")
    if "raw_record_id" not in record:
        raise ValueError("Record must preserve raw_record_id (null is allowed)")
    for key in ("product", "conditions", "source"):
        if not isinstance(record.get(key), dict):
            raise ValueError(f"Record requires a {key} object")
    for key in ("inputs", "solvents"):
        values = record.get(key)
        if not isinstance(values, list) or any(not isinstance(x, dict) for x in values):
            raise ValueError(f"Record requires a list of {key} objects")
    value = record["product"].get("yield_percent")
    if value is not None and not isinstance(value, (int, float)):
        raise ValueError("yield_percent must be a number or null")
    _json(record)  # Reject non-JSON values, NaN, and Infinity before writing.


def _components(record: dict):
    for item in record["inputs"]:
        yield item, item.get("role") or "input"
    for item in record["solvents"]:
        yield item, "solvent"
    yield record["product"], "product"


def _refresh_links(connection: sqlite3.Connection, record: dict) -> None:
    record_id = record["record_id"]
    connection.execute("DELETE FROM record_entities WHERE record_id = ?", (record_id,))
    for component, role in _components(record):
        entity_id = component.get("entity_id")
        if not entity_id:
            continue  # Unresolved names remain in the record, without a guessed link.
        if not connection.execute(
            "SELECT 1 FROM entities WHERE entity_id = ?", (entity_id,)
        ).fetchone():
            raise ValueError(f"Unknown entity_id in {record_id}: {entity_id}")
        connection.execute(
            "INSERT OR IGNORE INTO record_entities VALUES (?, ?, ?)",
            (record_id, entity_id, role),
        )


def _history(connection, record, revision, reason, evidence, patch_id, created_at):
    connection.execute(
        "INSERT INTO history VALUES (?, ?, ?, ?, ?, ?, ?)",
        (record["record_id"], revision, _json(record), reason, _json(evidence),
         patch_id, created_at),
    )


def build_database(records: list[dict], db_path: Path, entities: list[dict]) -> dict:
    """Create a new database. An existing path is never overwritten."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects against two classroom commands racing.
    fd = os.open(db_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with closing(_connect(db_path)) as connection:
            connection.executescript(_SCHEMA)
            with connection:
                seen_entities = set()
                for entity in entities:
                    entity_id = entity.get("entity_id")
                    if not isinstance(entity_id, str) or not entity_id.strip():
                        raise ValueError("Every entity requires an entity_id")
                    if entity_id in seen_entities:
                        raise ValueError(f"Duplicate entity_id: {entity_id}")
                    seen_entities.add(entity_id)
                    connection.execute(
                        "INSERT INTO entities VALUES (?, ?)", (entity_id, _json(entity))
                    )
                seen_records = set()
                for record in records:
                    _check_record(record)
                    record_id = record["record_id"]
                    if record_id in seen_records:
                        raise ValueError(f"Duplicate record_id: {record_id}")
                    seen_records.add(record_id)
                    connection.execute(
                        "INSERT INTO records VALUES (?, 1, ?)", (record_id, _json(record))
                    )
                    _refresh_links(connection, record)
                    _history(
                        connection, record, 1,
                        "Initial import; this event does not assert source correctness.",
                        [{"source_id": record["source_id"], **record["source"]}],
                        None, _now(),
                    )
    except Exception:
        db_path.unlink(missing_ok=True)  # Only the file exclusively created above.
        raise
    return {
        "status": "created", "database": str(db_path),
        "record_count": len(records), "entity_count": len(entities),
    }


def get_records(db_path: Path) -> list[dict]:
    """Return current record payloads without adding storage-specific fields."""
    with closing(_connect(db_path)) as connection:
        return [json.loads(row["payload"]) for row in connection.execute(
            "SELECT payload FROM records ORDER BY record_id"
        )]


def ingest_records(records: list[dict], db_path: Path, entities: list[dict]) -> dict:
    """Atomically add a literature batch; repeated input never undoes reviews."""
    ids = [r['record_id'] for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate record_id in import')
    fingerprint = hashlib.sha256(_json({
        'records': sorted(records, key=lambda r: r['record_id']),
        'entities': sorted(entities, key=lambda e: e['entity_id']),
    }).encode()).hexdigest()
    added = []
    with closing(_connect(db_path)) as connection:
        with connection:
            connection.execute('BEGIN IMMEDIATE')
            connection.execute('CREATE TABLE IF NOT EXISTS imports (sha256 TEXT PRIMARY KEY, record_ids TEXT NOT NULL)')
            if connection.execute('SELECT 1 FROM imports WHERE sha256=?', (fingerprint,)).fetchone():
                return {'status':'already_ingested','added':0,'import_sha256':fingerprint}
            for entity in entities:
                old = connection.execute('SELECT payload FROM entities WHERE entity_id=?', (entity['entity_id'],)).fetchone()
                if old and old[0] != _json(entity):
                    raise ValueError('Entity conflict: '+entity['entity_id'])
                if not old:
                    connection.execute('INSERT INTO entities VALUES (?,?)', (entity['entity_id'],_json(entity)))
            for record in records:
                _check_record(record)
                old = connection.execute('SELECT payload FROM records WHERE record_id=?',(record['record_id'],)).fetchone()
                if old:
                    if old[0] != _json(record):
                        raise ValueError('Record conflict; use an evidence-bearing revision: '+record['record_id'])
                    continue
                connection.execute('INSERT INTO records VALUES (?,1,?)',(record['record_id'],_json(record)))
                _refresh_links(connection,record)
                _history(connection,record,1,'Incremental import; not a source-correctness assertion.',
                         [{'source_id':record['source_id'],**record['source']}],None,_now())
                added.append(record['record_id'])
            connection.execute('INSERT INTO imports VALUES (?,?)',(fingerprint,_json(ids)))
    return {'status':'ingested','added':len(added),'record_ids':added,'import_sha256':fingerprint}


def query_records(
    db_path: Path, min_yield: float | None = None, name: str | None = None
) -> list[dict]:
    """Query current records; an entity alias never collapses experiments."""
    with closing(_connect(db_path)) as connection:
        matching_records = set()
        search = name.strip().casefold() if name is not None else None
        if search is not None:
            if not search:
                raise ValueError("name must not be empty")
            for row in connection.execute("SELECT entity_id, payload FROM entities"):
                entity = json.loads(row["payload"])
                names = [entity.get("preferred_name", ""), *entity.get("aliases", [])]
                if search in {value.strip().casefold() for value in names}:
                    matching_records.update(link[0] for link in connection.execute(
                        "SELECT record_id FROM record_entities WHERE entity_id = ?",
                        (row["entity_id"],),
                    ))
        result = []
        for row in connection.execute("SELECT * FROM records ORDER BY record_id"):
            record = json.loads(row["payload"])
            if search is not None and row["record_id"] not in matching_records:
                # Also permit an exact literal-name query for unresolved objects.
                names = {str(item.get("name", "")).strip().casefold()
                         for item, _ in _components(record)}
                if search not in names:
                    continue
            value = record["product"].get("yield_percent")
            if min_yield is not None and (value is None or value < min_yield):
                continue
            result.append({**record, "revision": row["revision"]})
        return result


def get_history(db_path: Path, record_id: str) -> list[dict]:
    with closing(_connect(db_path)) as connection:
        return [
            {
                "record_id": row["record_id"], "revision": row["revision"],
                "record": json.loads(row["payload"]), "reason": row["reason"],
                "evidence": json.loads(row["evidence"]), "patch_id": row["patch_id"],
                "created_at": row["created_at"],
            }
            for row in connection.execute(
                "SELECT * FROM history WHERE record_id = ? ORDER BY revision", (record_id,)
            )
        ]


def _check_patch(patch: dict) -> None:
    if not isinstance(patch, dict):
        raise ValueError("A patch must be a JSON object")
    for key in ("patch_id", "reason"):
        if not isinstance(patch.get(key), str) or not patch[key].strip():
            raise ValueError(f"Patch requires a nonempty {key}")
    evidence = patch.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("Patch requires nonempty evidence")
    for item in evidence:
        if not isinstance(item, dict) or not any(
            isinstance(item.get(k), str) and item[k].strip()
            for k in ("source_id", "url", "doi")
        ):
            raise ValueError("Evidence requires a source_id, url, or doi")
        has_location = any(
            isinstance(item.get(k), str) and item[k].strip()
            for k in ("locator", "text")
        ) or (type(item.get("start")) is int and item["start"] >= 0)
        if not has_location:
            raise ValueError("Evidence requires a locator, text, or start offset")
    if not isinstance(patch.get("changes"), list) or not patch["changes"]:
        raise ValueError("Patch requires nonempty changes")
    if any(not isinstance(change, dict) for change in patch["changes"]):
        raise ValueError("Every patch change must be an object")


def _replace_fields(record: dict, fields: dict) -> None:
    if not isinstance(fields, dict) or not fields:
        raise ValueError("replace requires a nonempty set object")
    for path, value in fields.items():
        if not isinstance(path, str) or not path:
            raise ValueError("A replacement field must be an existing dotted path")
        keys = path.split(".")
        if keys[0] in _IDENTITY_FIELDS:
            raise ValueError(f"Identity fields cannot be changed: {path}")
        target = record
        for key in keys[:-1]:
            if not isinstance(target, dict) or key not in target:
                raise ValueError(f"Unknown replacement path: {path}")
            target = target[key]
        if not isinstance(target, dict) or keys[-1] not in target:
            raise ValueError(f"Unknown replacement path: {path}")
        target[keys[-1]] = deepcopy(value)


def apply_patch(db_path: Path, patch: dict) -> dict:
    """Atomically apply evidence-bearing changes with optimistic revision checks."""
    _check_patch(patch)
    serialized = _json(patch)
    patch_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    patch_id = patch["patch_id"]
    changed = []
    with closing(_connect(db_path)) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                "SELECT sha256 FROM patches WHERE patch_id = ?", (patch_id,)
            ).fetchone()
            if previous:
                if previous["sha256"] != patch_hash:
                    raise ValueError(f"patch_id has already been used with different content: {patch_id}")
                return {"status": "already_applied", "patch_id": patch_id, "changed_records": []}
            timestamp = _now()
            for change in patch["changes"]:
                action = change.get("action")
                if action == "replace":
                    row = connection.execute(
                        "SELECT * FROM records WHERE record_id = ?", (change.get("record_id"),)
                    ).fetchone()
                    if not row:
                        raise ValueError(f"Unknown record_id: {change.get('record_id')}")
                    expected = change.get("expected_revision")
                    if type(expected) is not int or expected != row["revision"]:
                        raise ValueError(f"Stale or missing expected_revision for {row['record_id']}")
                    record = json.loads(row["payload"])
                    _replace_fields(record, change.get("set"))
                    _check_record(record)
                    revision = row["revision"] + 1
                    connection.execute(
                        "UPDATE records SET revision = ?, payload = ? WHERE record_id = ?",
                        (revision, _json(record), record["record_id"]),
                    )
                elif action == "add":
                    record = deepcopy(change.get("record"))
                    _check_record(record)
                    if connection.execute(
                        "SELECT 1 FROM records WHERE record_id = ?", (record["record_id"],)
                    ).fetchone():
                        raise ValueError(f"record_id already exists: {record['record_id']}")
                    revision = 1
                    connection.execute(
                        "INSERT INTO records VALUES (?, ?, ?)",
                        (record["record_id"], revision, _json(record)),
                    )
                else:
                    raise ValueError(f"Unsupported change action: {action}")
                _refresh_links(connection, record)
                _history(connection, record, revision, patch["reason"],
                         patch["evidence"], patch_id, timestamp)
                changed.append({"record_id": record["record_id"], "revision": revision})
            connection.execute(
                "INSERT INTO patches VALUES (?, ?, ?, ?)",
                (patch_id, patch_hash, serialized, timestamp),
            )
    return {"status": "applied", "patch_id": patch_id, "changed_records": changed}
