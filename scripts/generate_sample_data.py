#!/usr/bin/env python3
"""Generate a small, deterministic, synthetic PDB dataset for demos and CI.
This script exists so `pytest tests/test_pipeline.py` and the demo notebook
have something to run against.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from pdbflow.fixtures import (
    atom_line,
    expdta_line,
    header_line,
    model_line,
    remark2_resolution_line,
    remark3_line,
    source_line,
)

ORGANISMS = [
    "HOMO SAPIENS",
    "ESCHERICHIA COLI",
    "SACCHAROMYCES CEREVISIAE",
    "MUS MUSCULUS",
    "THERMUS THERMOPHILUS",
]
RESIDUES = ["ALA", "GLY", "SER", "LEU", "VAL", "LYS", "ASP", "GLU", "PHE", "TYR"]
CHAINS = ["A", "B", "C"]


def _structure_lines(
    pdb_id: str,
    experiment: str,
    resolution: str | None,
    n_models: int,
    n_atoms: int,
    organisms: list[str],
    rng: random.Random,
    include_hetatm: bool = False,
    corrupt_one_atom: bool = False,
) -> list[str]:
    lines = [header_line(pdb_id=pdb_id, date="14-JUN-26"), expdta_line(experiment)]
    if resolution is not None:
        lines.append(remark2_resolution_line(resolution))
        lines.append(remark3_line("R VALUE            (WORKING SET) : 0.198"))
        lines.append(remark3_line("FREE R VALUE                     : 0.231"))
    for i, org in enumerate(organisms, start=1):
        lines.append(source_line(f"MOL_ID: {i};", continuation=str(2 * i - 1)))
        lines.append(source_line(f"ORGANISM_SCIENTIFIC: {org};", continuation=str(2 * i)))

    multi_model = n_models > 1
    for model_num in range(1, n_models + 1):
        if multi_model:
            lines.append(model_line(model_num))
        for serial in range(1, n_atoms + 1):
            chain = rng.choice(CHAINS)
            res_name = rng.choice(RESIDUES)
            atom_name = rng.choice(["N", "CA", "C", "O", "CB"])
            line = atom_line(
                serial=serial,
                atom_name=atom_name,
                res_name=res_name,
                chain=chain,
                res_seq=(serial - 1) // 5 + 1,
                x=rng.uniform(-50, 50),
                y=rng.uniform(-50, 50),
                z=rng.uniform(-50, 50),
                occupancy=1.0,
                b_factor=rng.uniform(15, 80),
                element=atom_name[0],
            )
            if corrupt_one_atom and serial == max(1, n_atoms // 2):
                chars = list(line)
                chars[30:38] = list("********")
                line = "".join(chars)
            lines.append(line)
        if include_hetatm:
            lines.append(
                atom_line(
                    record_type="HETATM",
                    serial=n_atoms + 1,
                    atom_name="ZN",
                    res_name="ZN",
                    chain="A",
                    res_seq=999,
                    x=rng.uniform(-50, 50),
                    y=rng.uniform(-50, 50),
                    z=rng.uniform(-50, 50),
                    element="ZN",
                )
            )
        if multi_model:
            lines.append("ENDMDL")
    lines.append("END")
    return lines


def generate_dataset(output_dir: Path, n_structures: int = 25, seed: int = 42) -> list[str]:
    rng = random.Random(seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    # A few edge cases, matching the scenarios covered
    # by the unit tests, so the sample dataset actually demonstrates the
    # rejects/partial-parse paths and not just the happy path.
    fixed_cases = [
        dict(
            pdb_id="s000",
            experiment="X-RAY DIFFRACTION",
            resolution="1.74 ANGSTROMS.",
            n_models=1,
            n_atoms=60,
            organisms=["HOMO SAPIENS"],
            include_hetatm=True,
        ),
        dict(
            pdb_id="s001",
            experiment="SOLUTION NMR",
            resolution="NOT APPLICABLE.",
            n_models=4,
            n_atoms=25,
            organisms=["MUS MUSCULUS"],
        ),
        dict(
            pdb_id="s002",
            experiment="ELECTRON MICROSCOPY",
            resolution="12.50 ANGSTROMS.",  # >= 10 A: the truncation edge case
            n_models=1,
            n_atoms=80,
            organisms=["THERMUS THERMOPHILUS"],
        ),
        dict(
            pdb_id="s003",
            experiment="X-RAY DIFFRACTION",
            resolution="2.05 ANGSTROMS.",
            n_models=1,
            n_atoms=100,
            organisms=["HOMO SAPIENS", "ESCHERICHIA COLI"],  # multi-organism complex
        ),
        dict(
            pdb_id="s004",
            experiment="X-RAY DIFFRACTION",
            resolution="1.90 ANGSTROMS.",
            n_models=1,
            n_atoms=45,
            organisms=["SACCHAROMYCES CEREVISIAE"],
            corrupt_one_atom=True,  # -> one atom-level reject, parse_status="partial"
        ),
    ]

    for case in fixed_cases:
        lines = _structure_lines(rng=rng, **case)
        path = output_dir / f"{case['pdb_id']}.pdb"
        path.write_text("\n".join(lines) + "\n")
        written.append(str(path))

    # A deliberately unparseable file: no HEADER at all -> whole-file reject.
    no_header_path = output_dir / "reject_no_header.pdb"
    no_header_lines = [
        atom_line(serial=i + 1, res_seq=i + 1, x=float(i)) for i in range(5)
    ] + ["END"]
    no_header_path.write_text("\n".join(no_header_lines) + "\n")
    written.append(str(no_header_path))

    # Randomized remainder for volume / benchmark purposes.
    for i in range(5, n_structures):
        pdb_id = f"s{i:03d}"
        n_models = rng.choice([1, 1, 1, 1, 2])  # mostly single-model
        experiment = rng.choice(
            ["X-RAY DIFFRACTION", "X-RAY DIFFRACTION", "SOLUTION NMR", "ELECTRON MICROSCOPY"]
        )
        resolution = None if experiment == "SOLUTION NMR" else f"{rng.uniform(1.0, 3.5):.2f} ANGSTROMS."
        organisms = rng.sample(ORGANISMS, k=rng.choice([1, 1, 2]))
        lines = _structure_lines(
            pdb_id=pdb_id,
            experiment=experiment,
            resolution="NOT APPLICABLE." if resolution is None else resolution,
            n_models=n_models,
            n_atoms=rng.randint(30, 200),
            organisms=organisms,
            rng=rng,
            include_hetatm=rng.random() < 0.3,
        )
        path = output_dir / f"{pdb_id}.pdb"
        path.write_text("\n".join(lines) + "\n")
        written.append(str(path))

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", default="data/sample", help="Directory to write .pdb files into")
    parser.add_argument("--n", type=int, default=25, help="Number of structures to generate")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    written = generate_dataset(Path(args.output), n_structures=args.n, seed=args.seed)
    print(f"wrote {len(written)} synthetic PDB files to {args.output}")


if __name__ == "__main__":
    main()
