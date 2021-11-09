from pathlib import Path

import pytest

from koza.io.reader.csv_reader import CSVReader
from koza.model.config.source_config import FieldType

test_file = Path(__file__).parent.parent / 'resources' / 'source-files' / 'string.tsv'
tsv_with_footer = (
    Path(__file__).parent.parent / 'resources' / 'source-files' / 'tsv-with-footer.tsv'
)


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
        reader = CSVReader(string_file, field_type_map, delimiter=' ')
        # TODO actually test something
        for _ in reader:
            pass


def test_type_conversion():
    with open(test_file, 'r') as string_file:
        reader = CSVReader(string_file, field_type_map, delimiter=' ')
        row = next(reader)
        assert isinstance(row['protein1'], str)
        assert isinstance(row['textmining'], float)
        assert isinstance(row['combined_score'], int)


def test_field_doesnt_exist_in_file_raises_exception():
    with open(test_file, 'r') as string_file:
        field_map = field_type_map.copy()
        field_map['some_field_that_doesnt_exist'] = FieldType.str
        reader = CSVReader(string_file, field_map, delimiter=' ')
        with pytest.raises(ValueError):
            next(reader)


def test_field_in_file_but_not_in_config_logs_warning(caplog):
    """
    https://docs.pytest.org/en/latest/logging.html#caplog-fixture
    :return:
    """
    with open(test_file, 'r') as string_file:
        field_map = field_type_map.copy()
        del field_map['combined_score']
        reader = CSVReader(string_file, field_map, delimiter=' ')
        next(reader)
        assert caplog.records[0].levelname == 'WARNING'
        assert caplog.records[0].msg.startswith('Additional column(s) in source file')


def test_middle_field_in_file_but_not_in_config_logs_warning(caplog):
    with open(test_file, 'r') as string_file:
        field_map = field_type_map.copy()
        del field_map['cooccurence']
        reader = CSVReader(string_file, field_map, delimiter=' ')
        next(reader)
        assert caplog.records[1].levelname == 'WARNING'
        assert caplog.records[1].msg.startswith(
            'Additional columns located within configured fields'
        )


def test_no_field_map(caplog):
    with open(test_file, 'r') as string_file:
        reader = CSVReader(string_file, delimiter=' ')
        next(reader)


def test_no_exceptions_with_footer():
    with open(tsv_with_footer, 'r') as footer_file:
        reader = CSVReader(footer_file, field_type_map, delimiter=' ', comment_char='!!')
        # TODO actually test something
        for _ in reader:
            pass
