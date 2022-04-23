"""
Per-structure export from the compacted atoms table.
"""

from __future__ import annotations

import pandas as pd

from pdbflow import query


def _format_atom_line(row: pd.Series) -> str:
    buf = [" "] * 80

    def put(s: str, start: int, end: int) -> None:
        s = str(s)[: end - start + 1]
        for i, ch in enumerate(s):
            buf[start - 1 + i] = ch

    put(f"{row['record_type']:<6}", 1, 6)
    put(f"{int(row['serial']):>5}", 7, 11)
    put(f"{row['atom_name']:<4}", 13, 16)
    put((row["alt_loc"] or " ")[:1], 17, 17)
    put(f"{row['res_name']:<3}", 18, 20)
    put((row["chain"] or " ")[:1], 22, 22)
    put(f"{int(row['res_seq']):>4}", 23, 26)
    put((row["insertion_code"] or " ")[:1], 27, 27)
    put(f"{row['x']:>8.3f}", 31, 38)
    put(f"{row['y']:>8.3f}", 39, 46)
    put(f"{row['z']:>8.3f}", 47, 54)
    occ = row["occupancy"] if pd.notna(row["occupancy"]) else 1.0
    bfac = row["b_factor"] if pd.notna(row["b_factor"]) else 0.0
    put(f"{occ:>6.2f}", 55, 60)
    put(f"{bfac:>6.2f}", 61, 66)
    if row["element"]:
        put(f"{row['element']:>2}", 77, 78)
    return "".join(buf).rstrip()


def export_structure_pdb(
    con,
    atoms_path: str,
    pdb_id: str,
    dest_path: str,
    table_format: str = "parquet",
) -> int:
    """
    Write `pdb_id`'s atoms back out as a legacy-format .pdb file.
    Returns the number of atom lines written.
    """
    df = query.get_structure(con, atoms_path, pdb_id, table_format)
    if df.empty:
        raise ValueError(f"no atoms found for pdb_id={pdb_id!r}")

    lines: list[str] = []
    multi_model = df["model"].nunique() > 1
    for model_id, group in df.groupby("model", sort=True):
        if multi_model:
            lines.append(f"MODEL     {model_id:>4}")
        for _, row in group.sort_values("serial").iterrows():
            lines.append(_format_atom_line(row))
        if multi_model:
            lines.append("ENDMDL")
    lines.append("END")

    with open(dest_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    return len(df)


def export_structure_parquet(
    con,
    atoms_path: str,
    pdb_id: str,
    dest_path: str,
    table_format: str = "parquet",
) -> int:
    """Write `pdb_id`'s atoms out as a single standalone Parquet file."""
    df = query.get_structure(con, atoms_path, pdb_id, table_format)
    if df.empty:
        raise ValueError(f"no atoms found for pdb_id={pdb_id!r}")
    df.to_parquet(dest_path, index=False)
    return len(df)
