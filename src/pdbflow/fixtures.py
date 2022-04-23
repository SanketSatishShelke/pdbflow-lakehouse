"""
Builders for column-correct PDB-format lines.
Shared by the test suite, `scripts/generate_sample_data.py` and anything
else that needs a valid PDB file without typing
out fixed-width text by hand.
"""

from __future__ import annotations


def _put(buf: list[str], s: str, start: int, end: int) -> None:
    s = str(s)[: end - start + 1]
    for i, ch in enumerate(s):
        buf[start - 1 + i] = ch


def atom_line(
    record_type: str = "ATOM",
    serial: int = 1,
    atom_name: str = "N",
    alt_loc: str = "",
    res_name: str = "MET",
    chain: str = "A",
    res_seq: int = 1,
    icode: str = "",
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    occupancy: float = 1.0,
    b_factor: float = 0.0,
    element: str = "N",
) -> str:
    buf = [" "] * 80
    _put(buf, f"{record_type:<6}", 1, 6)
    _put(buf, f"{serial:>5}", 7, 11)
    _put(buf, f"{atom_name:<4}", 13, 16)
    _put(buf, (alt_loc or " ")[:1], 17, 17)
    _put(buf, f"{res_name:<3}", 18, 20)
    _put(buf, (chain or " ")[:1], 22, 22)
    _put(buf, f"{res_seq:>4}", 23, 26)
    _put(buf, (icode or " ")[:1], 27, 27)
    _put(buf, f"{x:>8.3f}", 31, 38)
    _put(buf, f"{y:>8.3f}", 39, 46)
    _put(buf, f"{z:>8.3f}", 47, 54)
    _put(buf, f"{occupancy:>6.2f}", 55, 60)
    _put(buf, f"{b_factor:>6.2f}", 61, 66)
    _put(buf, f"{element:>2}", 77, 78)
    return "".join(buf)


def header_line(classification: str = "HYDROLASE", date: str = "28-SEP-26", pdb_id: str = "1ABC") -> str:
    buf = [" "] * 80
    _put(buf, "HEADER", 1, 6)
    _put(buf, classification, 11, 50)
    _put(buf, date, 51, 59)
    _put(buf, pdb_id.upper(), 63, 66)
    return "".join(buf)


def expdta_line(text: str, continuation: str = "") -> str:
    buf = [" "] * 80
    _put(buf, "EXPDTA", 1, 6)
    _put(buf, continuation, 9, 10)
    _put(buf, text, 11, 79)
    return "".join(buf)


def remark2_resolution_line(value: str) -> str:
    buf = [" "] * 80
    _put(buf, "REMARK   2", 1, 10)
    _put(buf, f"RESOLUTION.  {value}", 12, 79)
    return "".join(buf)


def remark3_line(text: str) -> str:
    buf = [" "] * 80
    _put(buf, "REMARK   3", 1, 10)
    _put(buf, text, 12, 79)
    return "".join(buf)


def source_line(text: str, continuation: str = "1") -> str:
    buf = [" "] * 80
    _put(buf, "SOURCE", 1, 6)
    _put(buf, continuation, 9, 10)
    _put(buf, text, 11, 79)
    return "".join(buf)


def model_line(serial: int) -> str:
    buf = [" "] * 80
    _put(buf, "MODEL", 1, 5)
    _put(buf, f"{serial:>4}", 11, 14)
    return "".join(buf)


def minimal_entry(
    pdb_id: str = "1ABC",
    resolution: str = "1.74 ANGSTROMS.",
    n_atoms: int = 3,
    extra_lines: list[str] | None = None,
) -> str:
    lines = [
        header_line(pdb_id=pdb_id),
        expdta_line("X-RAY DIFFRACTION"),
        remark2_resolution_line(resolution),
        remark3_line("R VALUE            (WORKING SET) : 0.193"),
        remark3_line("FREE R VALUE                     : 0.229"),
        source_line("MOL_ID: 1;", continuation="1"),
        source_line("ORGANISM_SCIENTIFIC: HOMO SAPIENS;", continuation="2"),
    ]
    if extra_lines:
        lines.extend(extra_lines)
    for i in range(n_atoms):
        lines.append(atom_line(serial=i + 1, atom_name="N", res_seq=i + 1, x=float(i), y=0.0, z=0.0))
    lines.append("END")
    return "\n".join(lines) + "\n"
