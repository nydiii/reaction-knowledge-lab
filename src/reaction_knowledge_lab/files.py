"""Small file helpers shared by the CLI and notebooks."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_records(path):
    return read_json(path)["records"]


def save_records(path, records):
    return write_json(path, {"schema_version": 1, "records": records})
