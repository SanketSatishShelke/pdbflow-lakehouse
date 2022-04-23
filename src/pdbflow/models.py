"""
Records produced by the PDB parser.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Entry:
    """
    Metadata for one PDB structure (from HEADER, EXPDTA, REMARK 2/3, SOURCE).
    """

    pdb_id: str
    classification: str | None = None
    deposition_date: str | None = None
    experiment_types: list[str] = field(default_factory=list)
    resolution: float | None = None  # angstroms
    r_work: float | None = None
    r_free: float | None = None
    organisms: list[str] = field(default_factory=list)
    n_models: int = 0
    n_atoms: int = 0
    n_chains: int = 0
    coords_path: str | None = None
    parse_status: str = "ok"


@dataclass
class Atom:
    pdb_id: str
    model: int
    serial: int
    record_type: str  # "ATOM" or "HETATM"
    atom_name: str
    alt_loc: str | None
    res_name: str
    chain: str
    res_seq: int
    insertion_code: str | None
    x: float
    y: float
    z: float
    occupancy: float | None
    b_factor: float | None
    element: str | None


@dataclass
class Reject:
    """
    A file or a single record that failed to parse cleanly.
    """

    pdb_id: str
    level: str  # "file" | "atom"
    reason: str
    line: str | None = None


@dataclass
class ParseResult:
    entry: Entry | None
    atoms: list[Atom]
    rejects: list[Reject]
