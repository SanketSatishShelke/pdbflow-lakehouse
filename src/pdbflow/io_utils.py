"""
Format-agnostic read/write helpers.
"""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession


def write_table(df: DataFrame, path: str, table_format: str) -> None:
    writer = df.write.mode("overwrite")
    if table_format == "delta":
        writer.format("delta").save(path)
    elif table_format == "parquet":
        writer.parquet(path)
    else:
        raise ValueError(f"unknown table_format {table_format!r} (expected 'parquet' or 'delta')")


def read_table(spark: SparkSession, path: str, table_format: str) -> DataFrame:
    return spark.read.format(table_format).load(path)


def read_table_if_exists(spark: SparkSession, path: str, table_format: str) -> DataFrame | None:
    try:
        return read_table(spark, path, table_format)
    except Exception:
        return None


def append_table(df: DataFrame, path: str, table_format: str) -> None:
    writer = df.write.mode("append")
    if table_format == "delta":
        writer.format("delta").save(path)
    elif table_format == "parquet":
        writer.parquet(path)
    else:
        raise ValueError(f"unknown table_format {table_format!r} (expected 'parquet' or 'delta')")
