import pytest
from biolink_model_pydantic.model import (
    Gene,
    InformationContentEntityToNamedThingAssociation,
    Publication,
)

from koza.cli_runner import get_translation_table


@pytest.fixture
def gene_literature_entities(mock_koza):
    row = iter(
        [
            {
                'xb_article': 'XB-ART-1',
                'pmid': '16938438',
                'gene_pages': 'XB-GENEPAGE-487723 nog,XB-GENEPAGE-490377 msx1,XB-GENEPAGE-481828 bmp2,XB-GENEPAGE-483057 bmp4,XB-GENEPAGE-480982 fgf8,XB-GENEPAGE-6045068 hspa1l,XB-GENEPAGE-485625 hsp70',
            }
        ]
    )
    map_cache = {
        'genepage-2-gene': {
            'XB-GENEPAGE-487723': {
                'tropicalis_id': 'XB-GENE-487724',
                'laevis_l_id': 'XB-GENE-864891',
                'laevis_s_id': 'XB-GENE-17332089',
            },
            'XB-GENEPAGE-490377': {
                'tropicalis_id': 'XB-GENE-490378',
                'laevis_l_id': 'XB-GENE-490382',
                'laevis_s_id': 'XB-GENE-6253888',
            },
            'XB-GENEPAGE-481828': {
                'tropicalis_id': 'XB-GENE-481829',
                'laevis_l_id': 'XB-GENE-6252323',
                'laevis_s_id': 'XB-GENE-481833',
            },
            'XB-GENEPAGE-483057': {
                'tropicalis_id': 'XB-GENE-483058',
                'laevis_l_id': 'XB-GENE-483062',
                'laevis_s_id': 'XB-GENE-6254046',
            },
            'XB-GENEPAGE-480982': {
                'tropicalis_id': 'XB-GENE-480983',
                'laevis_l_id': 'XB-GENE-865429',
                'laevis_s_id': 'XB-GENE-17330198',
            },
            'XB-GENEPAGE-6045068': {
                'tropicalis_id': 'XB-GENE-6045069',
                'laevis_l_id': 'XB-GENE-17342842',
                'laevis_s_id': 'XB-GENE-6254949',
            },
            'XB-GENEPAGE-485625': {
                'tropicalis_id': 'XB-GENE-485626',
                'laevis_l_id': 'XB-GENE-485630',
                'laevis_s_id': 'XB-GENE-17340402',
            },
        }
    }
    tt = get_translation_table("examples/translation_table.yaml", None)

    return mock_koza(
        'gene-literature',
        row,
        './examples/xenbase/gene-literature.py',
        map_cache=map_cache,
        translation_table=tt,
    )


def test_gene_literature_entities(gene_literature_entities):
    assert gene_literature_entities


def test_gene_literature_entity_types(gene_literature_entities):
    publications = [
        entity for entity in gene_literature_entities if isinstance(entity, Publication)
    ]
    genes = [entity for entity in gene_literature_entities if isinstance(entity, Gene)]
    associations = [
        entity
        for entity in gene_literature_entities
        if isinstance(entity, InformationContentEntityToNamedThingAssociation)
    ]

    # a roundabout way of confirming that everything generated is one of these three and there's nothing else
    assert len(gene_literature_entities) == len(publications) + len(genes) + len(associations)
    assert len(publications) == 1


def test_gene_literature_entity(gene_literature_entities):
    genes = [entity for entity in gene_literature_entities if isinstance(entity, Gene)]

    # confirm one gene id from each species
    assert 'Xenbase:XB-GENE-480983' in [gene.id for gene in genes]
    assert 'Xenbase:XB-GENE-6253888' in [gene.id for gene in genes]
    assert 'Xenbase:XB-GENE-485630' in [gene.id for gene in genes]
