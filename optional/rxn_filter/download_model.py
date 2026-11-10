"""Download only the pinned RXN Filter weights; no model is executed here."""

import argparse
import hashlib
import io
from pathlib import Path
import ssl
import urllib.request
import zipfile

import certifi

ARCHIVE_SHA256 = "2dccc5743df622060df4b1a34eb9724046ecb71a326f5fb6e91672b58501f489"
CHECKPOINT_SHA256 = "e57267576898f574adfb9c2dd4b8b37b3b5b09e01c47b5b78dac6129a8e2b3b4"
ARCHIVE_BYTES = 31118149
MEMBER = "retro_planner/packages/rxn_filter/rxn_filter/model/filter_model_20250604_232451_state.pt"
REMOTE_PATH = "/xiaoruiwang/ChemEnzyRetroPlanner_metadata/resolve/main/rxn_filter_metadata.zip"


def extract_verified_weights(archive):
    if hashlib.sha256(archive).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Archive SHA256 mismatch; refusing to use a changed model archive.")
    with zipfile.ZipFile(io.BytesIO(archive)) as container:
        weights = container.read(MEMBER)
    if hashlib.sha256(weights).hexdigest() != CHECKPOINT_SHA256:
        raise ValueError("Checkpoint SHA256 mismatch.")
    return weights


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "models/rxn_filter_2025.pt")
    parser.add_argument("--mirror", action="store_true", help="Explicitly use hf-mirror.com if the official host is unreachable.")
    parser.add_argument("--archive", type=Path, help="Use an already downloaded archive, with the same hash checks.")
    args = parser.parse_args()
    try:
        if args.output.exists():
            if hashlib.sha256(args.output.read_bytes()).hexdigest() == CHECKPOINT_SHA256:
                print(f"Verified existing checkpoint: {args.output}")
                return
            raise ValueError(f"Existing file has a different hash; use a new --output path: {args.output}")
        if args.archive:
            archive = args.archive.read_bytes()
        else:
            host = "https://hf-mirror.com" if args.mirror else "https://huggingface.co"
            request = urllib.request.Request(host + REMOTE_PATH, headers={"User-Agent": "reaction-knowledge-lab/1"})
            context = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(request, context=context, timeout=90) as response:
                archive = response.read(ARCHIVE_BYTES + 1)
        weights = extract_verified_weights(archive)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(weights)
        print(f"Saved verified CPU-compatible state dictionary: {args.output}")
        print(f"SHA256: {CHECKPOINT_SHA256}")
    except (OSError, ValueError, zipfile.BadZipFile, KeyError) as exc:
        parser.exit(2, f"Download failed: {exc}\n")


if __name__ == "__main__":
    main()
