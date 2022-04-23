"""
Cross-check parse_pdb() wrt Biopython's PDBParser.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

Bio = pytest.importorskip("Bio")
from Bio.PDB import PDBParser  # noqa: E402

from pdbflow.parser import parse_pdb  # noqa: E402

from .helpers import atom_line, expdta_line, header_line, minimal_entry, model_line  # noqa: E402


def _biopython_atoms(text: str):
    with tempfile.NamedTemporaryFile("w", suffix=".pdb", delete=False) as f:
        f.write(text)
        path = f.name
    try:
        structure = PDBParser(QUIET=True).get_structure("x", path)
        rows = []
        for model in structure:
            for chain in model:
                for residue in chain:
                    for atom in residue:
                        coord = atom.get_coord()
                        rows.append(
                            {
                                "model": model.id + 1,  # Biopython models are 0-indexed
                                "chain": chain.id,
                                "res_seq": residue.id[1],
                                "atom_name": atom.get_name(),
                                "x": round(float(coord[0]), 3),
                                "y": round(float(coord[1]), 3),
                                "z": round(float(coord[2]), 3),
                                "b_factor": round(float(atom.get_bfactor()), 2),
                                "occupancy": round(float(atom.get_occupancy()), 2),
                            }
                        )
        return rows
    finally:
        Path(path).unlink(missing_ok=True)


def _ours_atoms(text: str):
    result = parse_pdb(text)
    return [
        {
            "model": a.model,
            "chain": a.chain,
            "res_seq": a.res_seq,
            "atom_name": a.atom_name.strip(),
            "x": round(a.x, 3),
            "y": round(a.y, 3),
            "z": round(a.z, 3),
            "b_factor": round(a.b_factor, 2) if a.b_factor is not None else 0.0,
            "occupancy": round(a.occupancy, 2) if a.occupancy is not None else 0.0,
        }
        for a in result.atoms
    ]


def _sort_key(row):
    return (row["model"], row["chain"], row["res_seq"], row["atom_name"])


def test_single_model_matches_biopython():
    text = minimal_entry(pdb_id="1ABC", n_atoms=5)
    ours = sorted(_ours_atoms(text), key=_sort_key)
    theirs = sorted(_biopython_atoms(text), key=_sort_key)
    assert ours == theirs


def test_four_char_atom_name_matches_biopython():
    line = atom_line(serial=1, atom_name="HD11", res_name="LEU", res_seq=5, x=1.234, y=-5.6, z=7.0)
    text = minimal_entry(pdb_id="1ABC", n_atoms=0, extra_lines=[line])
    ours = sorted(_ours_atoms(text), key=_sort_key)
    theirs = sorted(_biopython_atoms(text), key=_sort_key)
    assert ours == theirs
    assert ours[0]["atom_name"] == "HD11"


def test_multi_model_nmr_ensemble_matches_biopython():
    lines = [header_line(pdb_id="2NMR"), expdta_line("SOLUTION NMR")]
    for model_num in (1, 2, 3):
        lines.append(model_line(model_num))
        for serial, resseq in enumerate((1, 2), start=1):
            lines.append(atom_line(serial=serial, res_seq=resseq, x=float(model_num), y=float(resseq)))
        lines.append("ENDMDL")
    lines.append("END")
    text = "\n".join(lines)

    ours = sorted(_ours_atoms(text), key=_sort_key)
    theirs = sorted(_biopython_atoms(text), key=_sort_key)
    assert len(ours) == len(theirs) == 6
    assert ours == theirs
