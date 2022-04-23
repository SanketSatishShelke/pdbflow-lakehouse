"""
Python parser for PDB-format structure files.
- Parses the whole file at once.
- Column positions follow the actual PDB format spec.
- A file only gets rejected if it has no HEADER or no
  ATOM/HETATM records at all.
"""

from __future__ import annotations

import re

from pdbflow.models import Atom, Entry, ParseResult, Reject

_ATOM_COLUMNS = {
    "record_type": (1, 6),
    "serial": (7, 11),
    "atom_name": (13, 16),
    "alt_loc": (17, 17),
    "res_name": (18, 20),
    "chain": (22, 22),
    "res_seq": (23, 26),
    "insertion_code": (27, 27),
    "x": (31, 38),
    "y": (39, 46),
    "z": (47, 54),
    "occupancy": (55, 60),
    "b_factor": (61, 66),
    "element": (77, 78),
}

_HEADER_COLUMNS = {
    "classification": (11, 50),
    "deposition_date": (51, 59),
    "pdb_id": (63, 66),
}

_MONTHS = {
    m: f"{i:02d}"
    for i, m in enumerate(
        ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"],
        start=1,
    )
}

_RESOLUTION_RE = re.compile(r"RESOLUTION\.\s*([\d.]+)\s*ANGSTROM", re.IGNORECASE)
_R_WORK_RE = re.compile(
    r"R\s+VALUE\s*\(?\s*WORKING(?:\s+SET)?[^:]*:\s*([\d.]+)", re.IGNORECASE
)
_R_FREE_RE = re.compile(r"FREE\s+R\s+VALUE[^:]*:\s*([\d.]+)", re.IGNORECASE)
_ORGANISM_RE = re.compile(r"ORGANISM_SCIENTIFIC:\s*([^;]+)", re.IGNORECASE)


def _slice(line: str, span: tuple[int, int]) -> str:
    start, end = span
    return line[start - 1 : end].strip() if len(line) >= start else ""


def _parse_pdb_date(raw: str) -> str | None:
    m = re.match(r"(\d{2})-([A-Z]{3})-(\d{2})$", raw.strip().upper())
    if not m or m.group(2) not in _MONTHS:
        return None
    day, mon, yy = m.group(1), _MONTHS[m.group(2)], int(m.group(3))
    year = 2000 + yy if yy < 69 else 1900 + yy
    return f"{year:04d}-{mon}-{day}"


def _parse_float(raw: str) -> float | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_int(raw: str) -> int | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def parse_pdb(text: str, source_id: str | None = None) -> ParseResult:
    lines = text.splitlines()
    rejects: list[Reject] = []

    header_line = next((ln for ln in lines if ln.startswith("HEADER")), None)
    pdb_id = _slice(header_line, _HEADER_COLUMNS["pdb_id"]).lower() if header_line else None
    pdb_id = pdb_id or (source_id.lower() if source_id else None)

    if header_line is None or not pdb_id:
        return ParseResult(
            entry=None,
            atoms=[],
            rejects=[
                Reject(
                    pdb_id=source_id or "UNKNOWN",
                    level="file",
                    reason="missing or unparseable HEADER record",
                )
            ],
        )

    atom_lines = [ln for ln in lines if ln.startswith("ATOM") or ln.startswith("HETATM")]
    if not atom_lines:
        return ParseResult(
            entry=None,
            atoms=[],
            rejects=[
                Reject(pdb_id=pdb_id, level="file", reason="no ATOM/HETATM records")
            ],
        )

    parse_status = "ok"

    # --- metadata fields ---
    classification = _slice(header_line, _HEADER_COLUMNS["classification"]) or None

    raw_date = _slice(header_line, _HEADER_COLUMNS["deposition_date"])
    deposition_date = _parse_pdb_date(raw_date) if raw_date else None
    if raw_date and deposition_date is None:
        parse_status = "partial"
        rejects.append(
            Reject(pdb_id=pdb_id, level="field", reason=f"unparseable HEADER date {raw_date!r}")
        )

    expdta_lines = [ln for ln in lines if ln.startswith("EXPDTA")]
    experiment_types: list[str] = []
    if expdta_lines:
        joined = " ".join(ln[10:79].strip() for ln in expdta_lines)
        experiment_types = [t.strip() for t in joined.split(";") if t.strip()]
    else:
        parse_status = "partial"

    resolution = None
    for ln in lines:
        if ln.startswith("REMARK   2") and "RESOLUTION" in ln:
            m = _RESOLUTION_RE.search(ln)
            if m:
                resolution = _parse_float(m.group(1))
            break

    r_work = r_free = None
    for ln in lines:
        if not ln.startswith("REMARK   3"):
            continue
        if r_work is None:
            m = _R_WORK_RE.search(ln)
            if m:
                r_work = _parse_float(m.group(1))
        if r_free is None:
            m = _R_FREE_RE.search(ln)
            if m:
                r_free = _parse_float(m.group(1))
        if r_work is not None and r_free is not None:
            break

    source_lines = [ln for ln in lines if ln.startswith("SOURCE")]
    organisms: list[str] = []
    if source_lines:
        joined = " ".join(ln[10:79].strip() for ln in source_lines)
        seen = set()
        for m in _ORGANISM_RE.finditer(joined):
            org = m.group(1).strip().rstrip(";").strip()
            if org and org not in seen:
                seen.add(org)
                organisms.append(org)

    # --- coordinates ---
    atoms: list[Atom] = []
    model = 1
    chains: set[str] = set()

    for ln in lines:
        if ln.startswith("MODEL"):
            model = _parse_int(_slice(ln, (11, 14))) or (model + 1 if atoms else model)
            continue
        if ln.startswith("ENDMDL"):
            continue
        if not (ln.startswith("ATOM") or ln.startswith("HETATM")):
            continue

        serial = _parse_int(_slice(ln, _ATOM_COLUMNS["serial"]))
        x = _parse_float(_slice(ln, _ATOM_COLUMNS["x"]))
        y = _parse_float(_slice(ln, _ATOM_COLUMNS["y"]))
        z = _parse_float(_slice(ln, _ATOM_COLUMNS["z"]))

        if serial is None or x is None or y is None or z is None:
            parse_status = "partial"
            rejects.append(
                Reject(
                    pdb_id=pdb_id,
                    level="atom",
                    reason="non-numeric serial or coordinate",
                    line=ln,
                )
            )
            continue

        chain = _slice(ln, _ATOM_COLUMNS["chain"])
        chains.add(chain)
        alt_loc = _slice(ln, _ATOM_COLUMNS["alt_loc"]) or None
        insertion_code = _slice(ln, _ATOM_COLUMNS["insertion_code"]) or None

        atoms.append(
            Atom(
                pdb_id=pdb_id,
                model=model,
                serial=serial,
                record_type="ATOM" if ln.startswith("ATOM") else "HETATM",
                atom_name=_slice(ln, _ATOM_COLUMNS["atom_name"]),
                alt_loc=alt_loc,
                res_name=_slice(ln, _ATOM_COLUMNS["res_name"]),
                chain=chain,
                res_seq=_parse_int(_slice(ln, _ATOM_COLUMNS["res_seq"])) or 0,
                insertion_code=insertion_code,
                x=x,
                y=y,
                z=z,
                occupancy=_parse_float(_slice(ln, _ATOM_COLUMNS["occupancy"])),
                b_factor=_parse_float(_slice(ln, _ATOM_COLUMNS["b_factor"])),
                element=_slice(ln, _ATOM_COLUMNS["element"]) or None,
            )
        )

    if not atoms:
        # file-level reject
        rejects.append(Reject(pdb_id=pdb_id, level="file", reason="all coordinate rows unparseable"))
        return ParseResult(entry=None, atoms=[], rejects=rejects)

    n_models = len({a.model for a in atoms}) or 1

    entry = Entry(
        pdb_id=pdb_id,
        classification=classification,
        deposition_date=deposition_date,
        experiment_types=experiment_types,
        resolution=resolution,
        r_work=r_work,
        r_free=r_free,
        organisms=organisms,
        n_models=n_models,
        n_atoms=len(atoms),
        n_chains=len(chains),
        parse_status=parse_status,
    )

    return ParseResult(entry=entry, atoms=atoms, rejects=rejects)
