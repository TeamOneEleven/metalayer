"""Metalayer configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class QmdCollectionConfig(BaseModel):
    path: str
    mask: str = "**/*.md"


class QmdConfig(BaseModel):
    collections: dict[str, QmdCollectionConfig] = Field(default_factory=lambda: {
        "vault": QmdCollectionConfig(path="./context"),
        "queries": QmdCollectionConfig(path="./utils/queries"),
    })


class QueryMemoryConfig(BaseModel):
    ring_buffer_size: int = 500


class ConsensusConfig(BaseModel):
    sub_agents: int = 5
    max_rounds: int = 3


class MetalayerConfig(BaseModel):
    context_path: Path = Path("./context")
    utils_path: Path = Path("./utils")
    qmd: QmdConfig = Field(default_factory=QmdConfig)
    query_memory: QueryMemoryConfig = Field(default_factory=QueryMemoryConfig)
    consensus: ConsensusConfig = Field(default_factory=ConsensusConfig)


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from start (default cwd) looking for config.yaml."""
    current = start or Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "config.yaml").exists():
            return parent
    return current


def load_config(path: Path | None = None) -> MetalayerConfig:
    """Load config from a YAML file. Falls back to defaults if not found."""
    if path is None:
        root = find_project_root()
        path = root / "config.yaml"

    if path.exists():
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        return MetalayerConfig(**raw)

    return MetalayerConfig()
