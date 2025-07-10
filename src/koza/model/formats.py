from enum import Enum

__all__ = ("InputFormat", "OutputFormat")


class InputFormat(str, Enum):
    """Enum for supported file types"""

    csv = "csv"
    jsonl = "jsonl"
    json = "json"
    yaml = "yaml"
    # xml = "xml" # Not yet supported


class OutputFormat(str, Enum):
    """
    Output formats
    """

    tsv = "tsv"
    jsonl = "jsonl"
    kgx = "kgx"
    passthrough = "passthrough"
