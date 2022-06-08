"""
Test parallel transforms
"""
#import pytest
import dask

from koza.cli_runner import transform_source
from koza.model.config.source_config import OutputFormat


def transform(source_file):
    transform_source(
        source=source_file,
        output_dir="test-output/string/test-parallel",
        output_format=OutputFormat.tsv,
        local_table=None,
        global_table='examples/translation_table.yaml',
        row_limit=10,
    )
    return source_file

@dask.delayed
def transform_string():
    return transform("examples/string/protein-links-detailed.yaml")

@dask.delayed
def transform_string_string_declarative():
    return transform("examples/string-declarative/declarative-protein-links-detailed.yaml")

a = transform_string()
b = transform_string_string_declarative()

def test_parallel_transforms():
    results = [a,b]

    result = dask.delayed(print)(results)
    result.compute()
