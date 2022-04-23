"""
End-to-end test of the Spark ingestion layer against the sample
dataset.
"""

from __future__ import annotations

import duckdb
import pytest

pyspark = pytest.importorskip("pyspark")

from pyspark.sql import SparkSession  # noqa: E402

from pdbflow.config import Settings  # noqa: E402
from pdbflow.gold import build_gold_tables  # noqa: E402
from pdbflow.pipeline import ingest  # noqa: E402
from pdbflow.query import get_entry, get_structure  # noqa: E402
from scripts.generate_sample_data import generate_dataset  # noqa: E402


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.appName("pdbflow-test")
        .master("local[2]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture(scope="module")
def ingested(tmp_path_factory, spark):
    raw_dir = tmp_path_factory.mktemp("raw")
    generate_dataset(raw_dir, n_structures=20, seed=7)

    output_root = tmp_path_factory.mktemp("output")
    settings = Settings(output_root=str(output_root), table_format="parquet")

    result = ingest(spark, str(raw_dir), settings)
    return settings, result


def test_ingest_counts_are_consistent(ingested):
    _, result = ingested
    assert result.n_files > 0
    assert result.n_entries > 0
    assert result.n_atoms > 0
    assert result.n_entries <= result.n_files
    assert result.n_rejects >= 1


def test_entries_table_has_expected_columns(ingested, spark):
    settings, _ = ingested
    df = spark.read.parquet(settings.entries_path)
    expected = {
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
        "coords_path",
    }
    assert expected.issubset(set(df.columns))
    assert df.select("pdb_id").distinct().count() == df.count()  # one row per structure


def test_reject_no_header_is_quarantined_not_silently_dropped(ingested, spark):
    settings, _ = ingested
    rejects_df = spark.read.parquet(settings.rejects_path)
    reasons = [r["reason"] for r in rejects_df.filter("level = 'file'").collect()]
    assert any("HEADER" in r for r in reasons)


def test_atoms_table_is_compacted_not_one_file_per_structure(ingested):
    settings, result = ingested
    import glob

    part_files = glob.glob(f"{settings.atoms_path}/*.parquet")
    assert 0 < len(part_files) <= settings.atoms_shuffle_partitions


def test_get_structure_returns_only_that_pdb_id(ingested, spark):
    settings, _ = ingested
    entries_df = spark.read.parquet(settings.entries_path)
    any_id = entries_df.select("pdb_id").first()["pdb_id"]

    con = duckdb.connect()
    atoms = get_structure(con, settings.atoms_path, any_id, settings.table_format)
    assert len(atoms) > 0
    assert set(atoms["pdb_id"].unique()) == {any_id}

    entry = get_entry(con, settings.entries_path, any_id, settings.table_format)
    assert len(entry) == 1
    assert entry.iloc[0]["n_atoms"] == len(atoms)


def test_gold_tables_build_from_silver(ingested, spark):
    settings, _ = ingested
    paths = build_gold_tables(spark, settings)
    resolution_df = spark.read.parquet(paths["resolution_by_experiment"])
    bfactor_df = spark.read.parquet(paths["bfactor_by_experiment"])
    assert resolution_df.count() > 0
    assert bfactor_df.count() > 0
    assert "avg_resolution" in resolution_df.columns
    assert "avg_b_factor" in bfactor_df.columns
