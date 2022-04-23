"""
Read/query entries/atoms/gold tables.
"""

from __future__ import annotations

import duckdb


def _relation(con: duckdb.DuckDBPyConnection, path: str, table_format: str) -> str:
    if table_format == "parquet":
        return f"read_parquet('{path}/*.parquet')"
    if table_format == "delta":
        con.execute("INSTALL delta; LOAD delta;")
        return f"delta_scan('{path}')"
    raise ValueError(f"unknown table_format {table_format!r} (expected 'parquet' or 'delta')")


def connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect()


def get_structure(
    con: duckdb.DuckDBPyConnection, atoms_path: str, pdb_id: str, table_format: str = "parquet"
):
    rel = _relation(con, atoms_path, table_format)
    return con.execute(
        f"""
        SELECT *
        FROM {rel}
        WHERE pdb_id = ?
        ORDER BY model, serial
        """,
        [pdb_id.lower()],
    ).fetchdf()


def get_entry(
    con: duckdb.DuckDBPyConnection, entries_path: str, pdb_id: str, table_format: str = "parquet"
):
    rel = _relation(con, entries_path, table_format)
    return con.execute(f"SELECT * FROM {rel} WHERE pdb_id = ?", [pdb_id.lower()]).fetchdf()


def query(con: duckdb.DuckDBPyConnection, path: str, sql_where: str = "", table_format: str = "parquet"):
    rel = _relation(con, path, table_format)
    where = f"WHERE {sql_where}" if sql_where else ""
    return con.execute(f"SELECT * FROM {rel} {where}").fetchdf()
