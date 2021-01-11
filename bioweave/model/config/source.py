"""
source config data class
map config data class
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceConfig:
    pass

@dataclass(frozen=True)
class PrimarySourceConfig(SourceConfig):
    pass

@dataclass(frozen=True)
class MapSourceConfig(SourceConfig):
    pass