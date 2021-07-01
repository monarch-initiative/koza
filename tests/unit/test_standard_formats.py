from pathlib import Path

from koza.model.config.source_config import CompressionType, SourceFileConfig, StandardFormat
from koza.model.source import SourceFile


def test_phaf():

    source_file = SourceFile(
        SourceFileConfig(
            name="test-phaf",
            standard_format=StandardFormat.phaf,
            compression=CompressionType.gzip,
            files=[
                str(Path(__file__).parent.parent / 'resources' / 'source-files' / 'pombase.phaf.gz')
            ],
        )
    )

    assert source_file

    row = source_file.__next__()

    assert row
    assert row['Database name'] == 'PomBase'
    assert row['Expression'] == 'Not assayed'
    assert row['Gene name'] == 'cki3'
