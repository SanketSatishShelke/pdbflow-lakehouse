"""
Spark schemas shared between ingestion and consumers.
`WIDE_SCHEMA` is the intermediate shape from one pass over the raw files.
"""

from __future__ import annotations

from pyspark.sql.types import (
    ArrayType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

WIDE_SCHEMA = StructType(
    [
        StructField("kind", StringType(), False),  # "entry" | "atom" | "reject"
        StructField("pdb_id", StringType(), False),
        # entry fields
        StructField("classification", StringType(), True),
        StructField("deposition_date", StringType(), True),
        StructField("experiment_types", ArrayType(StringType()), True),
        StructField("resolution", DoubleType(), True),
        StructField("r_work", DoubleType(), True),
        StructField("r_free", DoubleType(), True),
        StructField("organisms", ArrayType(StringType()), True),
        StructField("n_models", IntegerType(), True),
        StructField("n_atoms", IntegerType(), True),
        StructField("n_chains", IntegerType(), True),
        StructField("parse_status", StringType(), True),
        # atom fields
        StructField("model", IntegerType(), True),
        StructField("serial", IntegerType(), True),
        StructField("record_type", StringType(), True),
        StructField("atom_name", StringType(), True),
        StructField("alt_loc", StringType(), True),
        StructField("res_name", StringType(), True),
        StructField("chain", StringType(), True),
        StructField("res_seq", IntegerType(), True),
        StructField("insertion_code", StringType(), True),
        StructField("x", DoubleType(), True),
        StructField("y", DoubleType(), True),
        StructField("z", DoubleType(), True),
        StructField("occupancy", DoubleType(), True),
        StructField("b_factor", DoubleType(), True),
        StructField("element", StringType(), True),
        # reject fields
        StructField("level", StringType(), True),
        StructField("reason", StringType(), True),
        StructField("line", StringType(), True),
    ]
)

ENTRIES_COLUMNS = [
    "pdb_id",
    "classification",
    "deposition_date",
    "experiment_types",
    "resolution",
    "r_work",
    "r_free",
    "organisms",
    "n_models",
    "n_atoms",
    "n_chains",
    "parse_status",
]

ATOMS_COLUMNS = [
    "pdb_id",
    "model",
    "serial",
    "record_type",
    "atom_name",
    "alt_loc",
    "res_name",
    "chain",
    "res_seq",
    "insertion_code",
    "x",
    "y",
    "z",
    "occupancy",
    "b_factor",
    "element",
]

REJECTS_COLUMNS = ["pdb_id", "level", "reason", "line"]
