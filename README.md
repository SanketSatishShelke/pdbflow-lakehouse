# pdbflow

[![PySpark](https://img.shields.io/badge/PySpark-3.1%2B-orange)](https://spark.apache.org/docs/latest/api/python/getting_started/index.html)
[![Docker](https://img.shields.io/badge/Docker-✔️-blue)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-brightgreen)](https://www.python.org/)

A PySpark pipeline for parsing PDB structure files at scale. It reads raw `.pdb` files, writes out typed **entries** (metadata) and **atoms** (coordinate) tables.

```bash
pdbflow ingest --input data/raw --output-root output
pdbflow get-structure 1abc --output-root output
pdbflow export 1abc 1abc.pdb --output-root output
```

## Getting real data

```bash
# a curated slice, or the whole archive via rsync:
rsync -rlpt -v -z --delete rsync.rcsb.org::ftp_data/structures/divided/pdb/ data/raw/rcsb/
# or fetch individual files:
curl -o data/raw/1abc.pdb https://files.rcsb.org/download/1ABC.pdb
```

Then `pdbflow ingest --input data/raw/rcsb`.

## Quickstart

```bash
pip install -r requirements-dev.txt           # installs pyspark + delta-spark too
pip install -e . --no-deps                    # registers the `pdbflow` command
python scripts/generate_sample_data.py --output data/sample
pytest                                        # parser + biopython cross-check + full pipeline

pdbflow ingest --input data/sample --output-root output
pdbflow gold --output-root output
pdbflow get-structure s000 --output-root output
pdbflow export s000 s000.pdb --output-root output
```

Querying and exporting don't need PySpark, they're DuckDB only:

```bash
pip install -r requirements.txt   # core only, no pyspark
pip install -e . --no-deps        # registers the `pdbflow` command
pdbflow get-structure s000 --output-root output
```

## CLI

| Command | What it does |
|---|---|
| `pdbflow ingest --input DIR --output-root ROOT [--format parquet\|delta]` | Parse every `*.pdb` under `DIR`, write `entries`/`atoms`/`rejects` |
| `pdbflow gold --output-root ROOT` | Rebuild the gold aggregate tables |
| `pdbflow get-structure PDB_ID --output-root ROOT` | Print every atom of one structure |
| `pdbflow export PDB_ID DEST --output-root ROOT` | Write one structure to `DEST` (`.pdb` or `.parquet`) |

`--output-root` also takes `s3a://bucket/prefix` for S3/MinIO once the usual Hadoop AWS jars and credentials are set up on the Spark side; nothing here hardcodes a local path.

## Layout

```
src/pdbflow/
  models.py          Entry / Atom / Reject dataclasses
  parser.py          pure-Python PDB parser (no Spark dependency)
  fixtures.py        column-correct PDB line builders, shared by tests + sample data
  spark_schema.py     the wide intermediate schema and per-table column lists
  pipeline.py         binaryFiles -> parse -> write entries/atoms/rejects
  gold.py              resolution_by_experiment, bfactor_by_experiment
  io_utils.py         format-agnostic (parquet|delta) read/write helpers
  query.py             DuckDB-based get_structure / get_entry / query
  export.py            on-demand per-structure .pdb / .parquet export
  cli.py               `pdbflow` command-line entry point
  config.py            Settings (env-overridable paths, table format, partitioning)
tests/
  test_parser.py               parser unit tests incl. every edge case above
  test_against_biopython.py    cross-check against an independent parser
  test_pipeline.py             end-to-end Spark ingestion + gold + query test
scripts/generate_sample_data.py   synthetic sample dataset generator
notebooks/demo.ipynb              DuckDB queries over the gold tables
```

## Testing

```bash
pytest -v
```

- `test_parser.py` and `test_against_biopython.py` only need `pip install -r requirements-dev.txt`, no JVM required (the Biopython comparison skips if it's not installed).
- `test_pipeline.py` needs PySpark (in `requirements-dev.txt`) and a JVM. It skips itself automatically if PySpark isn't importable.


## License

MIT, see [LICENSE](LICENSE).
