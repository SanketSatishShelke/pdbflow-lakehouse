"""Central place for paths and options, so nothing is hardcoded in the pipeline.

Every setting can be overridden by environment variable, which is what
lets the same code point at local disk during development and at S3 bucket
in deployment (`--output-root s3a://pdbflow/...` plus the usual AWS S3 bucket
credentials). Nothing here talks to a specific storage backend directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    output_root: str = os.environ.get("PDBFLOW_OUTPUT_ROOT", "output")
    table_format: str = os.environ.get("PDBFLOW_TABLE_FORMAT", "parquet")  # "parquet" | "delta"
    atoms_shuffle_partitions: int = int(os.environ.get("PDBFLOW_ATOMS_PARTITIONS", "8"))

    @property
    def entries_path(self) -> str:
        return f"{self.output_root}/silver/entries"

    @property
    def atoms_path(self) -> str:
        return f"{self.output_root}/silver/atoms"

    @property
    def rejects_path(self) -> str:
        return f"{self.output_root}/silver/rejects"

    @property
    def gold_root(self) -> str:
        return f"{self.output_root}/gold"


DEFAULT_SETTINGS = Settings()
