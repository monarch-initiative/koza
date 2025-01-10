from io import StringIO
from pathlib import Path

import pytest
from koza.io.reader.csv_reader import CSVReader
from koza.model.config.source_config import (CSVReaderConfig, FieldType,
                                             FormatType)

test_file = Path(__file__).parent.parent / 'resources' / 'source-files' / 'string.tsv'
tsv_with_footer = Path(__file__).parent.parent / 'resources' / 'source-files' / 'tsv-with-footer.tsv'


field_type_map = {
    'protein1': FieldType.str,
    'protein2': FieldType.str,
    'neighborhood': FieldType.str,
    'fusion': FieldType.str,
    'cooccurence': FieldType.str,
    'coexpression': FieldType.str,
    'experimental': FieldType.str,
    'database': FieldType.str,
    'textmining': FieldType.float,
    'combined_score': FieldType.int,
}


def test_no_exceptions_in_normal_case():
    with open(test_file, 'r') as string_file:
        config = CSVReaderConfig(
            format=FormatType.csv,
            field_type_map=field_type_map,
            delimiter=' ',
        )
        reader = CSVReader(string_file, config)
        # TODO actually test something
        for _ in reader:
            pass


def test_type_conversion():
    with open(test_file, 'r') as string_file:
        config = CSVReaderConfig(
            format=FormatType.csv,
            field_type_map=field_type_map,
            delimiter=' ',
        )
        reader = CSVReader(string_file, config)
        row = next(iter(reader))
        assert isinstance(row['protein1'], str)
        assert isinstance(row['textmining'], float)
        assert isinstance(row['combined_score'], int)


def test_field_doesnt_exist_in_file_raises_exception():
    with open(test_file, 'r') as string_file:
        invalid_field_type_map = field_type_map.copy()
        invalid_field_type_map['some_field_that_doesnt_exist'] = FieldType.str
        config = CSVReaderConfig(
            field_type_map=invalid_field_type_map,
            delimiter=' ',
        )
        reader = CSVReader(string_file, config)
        with pytest.raises(ValueError):
            next(iter(reader))


def test_field_in_file_but_not_in_config_logs_warning(caplog):
    """
    https://docs.pytest.org/en/latest/logging.html#caplog-fixture
    :return:
    """
    with open(test_file, 'r') as string_file:
        missing_field_field_type_map = field_type_map.copy()
        del missing_field_field_type_map['combined_score']
        config = CSVReaderConfig(
            field_type_map=missing_field_field_type_map,
            delimiter=' ',
        )
        reader = CSVReader(string_file, config)
        next(iter(reader))
        assert caplog.records[0].levelname == 'WARNING'
        assert caplog.records[0].msg.startswith('Additional column(s) in source file')


def test_middle_field_in_file_but_not_in_config_logs_warning(caplog):
    with open(test_file, 'r') as string_file:
        missing_field_field_type_map = field_type_map.copy()
        del missing_field_field_type_map['cooccurence']
        config = CSVReaderConfig(
            field_type_map=missing_field_field_type_map,
            delimiter=' ',
        )
        reader = CSVReader(string_file, config)
        next(iter(reader))
        assert caplog.records[0].levelname == 'WARNING'
        # assert caplog.records[1].msg.startswith('Additional columns located within configured fields')
        assert caplog.records[0].msg.startswith('Additional column(s) in source file')


def test_no_field_map(caplog):
    with open(test_file, 'r') as string_file:
        config = CSVReaderConfig(
            delimiter=' ',
        )
        reader = CSVReader(string_file, config)
        assert reader.field_type_map is None
        header = reader.header
        assert len(header) == 10
        assert reader.field_type_map is not None
        assert header == list(reader.field_type_map.keys())


def test_no_exceptions_with_footer():
    with open(tsv_with_footer, 'r') as footer_file:
        config = CSVReaderConfig(
            format=FormatType.csv,
            field_type_map=field_type_map,
            delimiter=' ',
            comment_char='!!',
        )
        reader = CSVReader(footer_file, config)
        # TODO actually test something
        for _ in reader:
            pass


def test_header_delimiter():
    test_buffer = StringIO('a/b/c\n1,2,3\n4,5,6')
    test_buffer.name = 'teststring'
    config = CSVReaderConfig(
        delimiter=',',
        header_delimiter='/',
    )
    reader = CSVReader(test_buffer, config)
    assert reader.header == ["a", "b", "c"]
    assert [row for row in reader] == [
        {
            "a": "1",
            "b": "2",
            "c": "3",
        },
        {
            "a": "4",
            "b": "5",
            "c": "6",
        },
    ]


def test_header_prefix():
    test_buffer = StringIO("# a|b|c")
    test_buffer.name = 'teststring'
    config = CSVReaderConfig(
        header_delimiter='|',
        header_prefix="# ",
    )
    reader = CSVReader(test_buffer, config)
    assert reader.header == ["a", "b", "c"]


def test_header_skip_lines():
    test_buffer = StringIO("skipped line 1\nskipped line 2\na,b,c")
    test_buffer.name = 'teststring'
    config = CSVReaderConfig(
        header_mode=2,
        delimiter=',',
    )
    reader = CSVReader(test_buffer, config)
    assert reader.header == ["a", "b", "c"]


def test_default_config():
    test_buffer = StringIO("a\tb\tc\n1\t2\t3\n4\t5\t6")
    test_buffer.name = 'teststring'
    config = CSVReaderConfig()
    reader = CSVReader(test_buffer, config)
    assert [row for row in reader] == [
        {
            "a": "1",
            "b": "2",
            "c": "3",
        },
        {
            "a": "4",
            "b": "5",
            "c": "6",
        },
    ]


def test_header_with_leading_comments():
    test_buffer = StringIO("# comment 1\n#comment 2\na,b,c")
    test_buffer.name = 'teststring'
    config = CSVReaderConfig(
        comment_char='#',
        delimiter=',',
    )
    reader = CSVReader(test_buffer, config)
    assert reader.header == ["a", "b", "c"]


def test_header_with_blank_lines():
    test_buffer = StringIO("\n\n\n\na,b,c")
    test_buffer.name = 'teststring'
    config = CSVReaderConfig(
        delimiter=',',
    )
    reader = CSVReader(test_buffer, config)
    assert reader.header == ["a", "b", "c"]
