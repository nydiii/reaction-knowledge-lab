"""CPU inference for the published ChemEnzyRetroPlanner Morgan RXN Filter.

FilterModel and the Morgan calculations are adapted from Xiaorui Wang's MIT
licensed implementation, commit 7dbab354189db9edc7aea9c0aedc2f1b1659f906.
See LICENSE and provenance.json. Input checks, hash verification, CPU-safe
loading, JSON output, and the CLI are course additions.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem
from torch import nn
from torch.nn import functional as F

CHECKPOINT_SHA256 = "e57267576898f574adfb9c2dd4b8b37b3b5b09e01c47b5b78dac6129a8e2b3b4"
UPSTREAM_COMMIT = "7dbab354189db9edc7aea9c0aedc2f1b1659f906"


class FilterModel(nn.Module):
    """Original two-branch architecture, with the original parameter names."""

    def __init__(self, fp_dim=2048, dim=1024, dropout_rate=0.4):
        super().__init__()
        self.fp_dim = fp_dim
        self.dim = dim
        self.dropout_rate = dropout_rate
        self.lin_p = nn.Linear(self.fp_dim, self.dim)
        self.lin_r = nn.Linear(self.fp_dim, self.dim)

    def forward(self, fp_prod, fp_rxn):
        x_prod = F.dropout(self.lin_p(fp_prod), p=self.dropout_rate, training=self.training)
        x_prod = F.elu(x_prod).unsqueeze(1)
        x_rxn = F.elu(self.lin_r(fp_rxn)).unsqueeze(1)
        return torch.bmm(x_prod, x_rxn.transpose(1, 2)).view(-1)


def cal_fp(mol, radius=2, nbits=2048):
    bitvect = AllChem.GetMorganFingerprintAsBitVect(
        mol, radius, nBits=int(nbits), useChirality=True
    )
    array = np.zeros((1,))
    DataStructs.ConvertToNumpyArray(bitvect, array)
    return array.reshape([1, nbits])


def reaction_to_fingerprint(reaction):
    """Preserve upstream sum-of-reactant-fingerprints, not bitwise union."""
    if reaction.count(">>") != 1:
        raise ValueError("Use reactant1.reactant2>>product SMILES; names are not accepted.")
    left, right = reaction.split(">>")
    if not left.strip() or not right.strip() or ">" in left + right:
        raise ValueError("Both reactant and product sides must contain SMILES.")
    reactants = [Chem.MolFromSmiles(item) if item else None for item in left.split(".")]
    product = Chem.MolFromSmiles(right)
    if product is None or any(mol is None or mol.GetNumAtoms() == 0 for mol in reactants):
        raise ValueError("At least one compound is not valid SMILES; resolve its identity first.")
    if product.GetNumAtoms() == 0:
        raise ValueError("The product is empty.")
    prod_fp = cal_fp(product)
    rxn_fp = prod_fp - sum(cal_fp(mol) for mol in reactants)
    return torch.from_numpy(prod_fp).float(), torch.from_numpy(rxn_fp).float()


def score_reaction(reaction_smiles, checkpoint, cutoff=0.5):
    if not 0 <= cutoff <= 1:
        raise ValueError("cutoff must be between 0 and 1.")
    prod_fp, rxn_fp = reaction_to_fingerprint(reaction_smiles)
    checkpoint = Path(checkpoint)
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    if digest != CHECKPOINT_SHA256:
        raise ValueError("Checkpoint SHA256 mismatch. Download the pinned 2025 model again.")
    model = FilterModel()
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    model.eval()
    with torch.no_grad():
        score = torch.sigmoid(model(prod_fp, rxn_fp)).item()
    return {
        "reaction_smiles": reaction_smiles,
        "plausibility_score": score,
        "cutoff": cutoff,
        "needs_review": score < cutoff,
        "device": "cpu",
        "checkpoint_sha256": digest,
        "upstream_commit": UPSTREAM_COMMIT,
        "interpretation": "Auxiliary structural screening only; no source verification or automatic correction.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reaction-smiles", required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--cutoff", type=float, default=0.5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = score_reaction(args.reaction_smiles, args.checkpoint, args.cutoff)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"RXN Filter: {exc}\n")
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
