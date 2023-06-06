import pytest

from koza.model.config.source_config import SSSOMConfig 

sssom_files = [
    'tests/resources/sssom/testmapping.sssom.tsv',
    'tests/resources/sssom/testmapping2.sssom.tsv'
]

def _make_sssom_config(
        multifile: bool = False,
        filter_prefixes = [],
        subject_target_prefixes = [],
        object_target_prefixes= []
    ):
    return SSSOMConfig(
        files = sssom_files,
        filter_prefixes = filter_prefixes,
        subject_target_prefixes = subject_target_prefixes,
        object_target_prefixes = object_target_prefixes
        )

def test_basic_mapping():
    sssom_config = _make_sssom_config(
        filter_prefixes = ['A', 'B', 'SOMETHINGELSE'],
        subject_target_prefixes = ['B'],
        object_target_prefixes = ['X']
    )

    edge = {
        'subject': 'A:123',
        'object': 'SOMETHINGELSE:456',
    }
    mapped = sssom_config.apply_mapping(edge)
    assert mapped['subject'] == 'B:987'


def test_merge_and_filter():
    sssom_config = _make_sssom_config(
        multifile=True,
        filter_prefixes = ['A', 'B'],
    )
    df = sssom_config.df
    assert 'A:123' in df['subject_id'].values    
    assert 'B:987' in df['object_id'].values
    assert ('X:111' not in df['object_id'].values and
            'X:111' not in df['subject_id'].values)


def test_exact_match_is_bidirectional():
    sssom_config = _make_sssom_config(  
        filter_prefixes = ['A', 'B'],
        subject_target_prefixes = ['B'],
        object_target_prefixes = ['B']
    )
    
    edge = {
        'subject': 'A:123',
        'object': 'SOMETHINGELSE:456',
    }
    mapped = sssom_config.apply_mapping(edge)
    print(f"MAPPED::\n\n{mapped}\n\n")
    assert mapped['subject'] == 'B:987'

    edge = {
        'subject': 'SOMETHINGELSE:123',
        'object': 'A:420'
    }
    mapped = sssom_config.apply_mapping(edge)
    assert mapped['object'] == 'B:000'


def test_narrow_match():
    pass


def test_broad_match():
    pass
