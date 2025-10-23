"""
Test to verify that multiple ingests with same-named transform files
don't suffer from module caching issues.

This test reproduces the bug where:
1. First ingest loads gene.py from source_a (expects column 'species_A')
2. Second ingest loads gene.py from source_b (expects column 'species_B')
3. Without proper cache clearing, Python's import system returns the cached
   gene module from source_a, causing a KeyError when it tries to access
   'species_A' on source_b's data which only has 'species_B'
"""

import os
from pathlib import Path

from koza.runner import KozaRunner
from koza.model.formats import OutputFormat


def test_same_named_modules_in_sequence():
    """
    Test that loading two configs with same-named transform files (gene.py)
    doesn't cause module caching issues.

    Without the fix in runner.py that clears sys.modules, this test will fail
    because the second ingest will use the cached gene module from the first ingest.
    """
    test_resources = Path(__file__).parent.parent / "resources"
    output_dir = Path(__file__).parent.parent / "output"

    # Run first ingest - uses gene.py that expects 'species_A' column
    config1_path = test_resources / "module_cache_test_source_a" / "gene.yaml"
    config1, runner1 = KozaRunner.from_config_file(
        str(config1_path),
        output_dir=str(output_dir),
        output_format=OutputFormat.tsv,
    )
    runner1.run()

    # Verify source_a produced output
    assert os.path.exists(f"{output_dir}/module_cache_test_source_a_nodes.tsv")

    # Run second ingest - uses different gene.py that expects 'species_B' column
    config2_path = test_resources / "module_cache_test_source_b" / "gene.yaml"
    config2, runner2 = KozaRunner.from_config_file(
        str(config2_path),
        output_dir=str(output_dir),
        output_format=OutputFormat.tsv,
    )
    runner2.run()  # This will fail with KeyError if module is cached

    # Verify source_b produced output
    assert os.path.exists(f"{output_dir}/module_cache_test_source_b_nodes.tsv")

    # Both ingests should have completed successfully without KeyError
