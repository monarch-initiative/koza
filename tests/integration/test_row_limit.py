"""
Test the row_limit argument for transforms
Assert correct number of rows has been processed
"""
#TODO: Parameterize row_limit, and test reading from JSON and JSONL 
#TODO: Address filter in examples/string-declarative/protein-links-detailed.yaml

from pathlib import Path

import pytest

from koza.cli_runner import transform_source
from koza.model.config.source_config import OutputFormat

@pytest.mark.parametrize(
    "ingest, output_names, output_format, row_limit, header_len, expected_node_len, expected_edge_len",
    [  
        (
            "string-declarative",       # ingest
            ["protein-links-detailed"], # output_names
            OutputFormat.tsv,           # output_format
            3,                          # row_limit
            1,                          # header_len
            11,                         # expected_node_leng
            6                           # expected_edge_leng
        )
    ]
)
def test_examples(ingest, output_names, output_format, row_limit, header_len, expected_node_len, expected_edge_len):

    source = f"examples/{ingest}/protein-links-detailed.yaml"
    output_suffix = ".tsv"
    output_dir = f"./test-output/{ingest}-row-limit"

    transform_source(source=source, 
                    output_dir=output_dir, 
                    output_format=output_format, 
                    global_table="examples/translation_table.yaml", 
                    local_table=None,
                    row_limit=row_limit)

    # hacky check that correct number of rows was processed
    node_file = f"{output_dir}/protein-links-detailed_nodes{output_suffix}"
    edge_file = f"{output_dir}/protein-links-detailed_edges{output_suffix}"

    node_lines = sum(1 for line in open(node_file))
    edge_lines = sum(1 for line in open(edge_file))

    assert node_lines == expected_node_len
    assert edge_lines == expected_edge_len
 