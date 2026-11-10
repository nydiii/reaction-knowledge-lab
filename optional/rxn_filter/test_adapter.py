"""Small contract tests; the actual pretrained model check is documented separately."""

import tempfile
from pathlib import Path
import unittest

from adapter import reaction_to_fingerprint, score_reaction
from download_model import extract_verified_weights


class ContractTests(unittest.TestCase):
    def test_unresolved_or_malformed_input_is_rejected(self):
        for reaction in ("ethanol>>CC=O", ">>CC=O", "CCO>>", "CCO>O>CC=O", "CCO..O>>CC=O"):
            with self.subTest(reaction=reaction), self.assertRaises(ValueError):
                reaction_to_fingerprint(reaction)

    def test_wrong_checkpoint_is_rejected_before_deserialization(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wrong.pt"
            path.write_bytes(b"not a pretrained model")
            with self.assertRaisesRegex(ValueError, "SHA256"):
                score_reaction("CCO>>CC=O", path)

    def test_changed_archive_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "SHA256"):
            extract_verified_weights(b"not the pinned archive")


if __name__ == "__main__":
    unittest.main()
