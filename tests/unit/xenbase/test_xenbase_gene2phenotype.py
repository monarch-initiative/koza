import pytest
from biolink_model_pydantic.model import Gene, GeneToPhenotypicFeatureAssociation, PhenotypicFeature


@pytest.fixture
def gene2phenotype_entities(mock_koza):
    row = iter(
        [
            {
                'SUBJECT': 'XB-GENE-1000632',
                'SUBJECT_LABEL': 'dctn2',
                'SUBJECT_TAXON': 'NCBITaxon:8364',
                'SUBJECT_TAXON_LABEL': 'Xla',
                'OBJECT': 'XPO:0102358',
                'OBJECT_LABEL': 'abnormal tail morphology',
                'RELATION': 'RO_0002200',
                'RELATION_LABEL': 'has_phenotype',
                'EVIDENCE': '',
                'EVIDENCE_LABEL': '',
                'SOURCE': 'PMID:17112317',
                'IS_DEFINED_BY': '',
                'QUALIFIER': '',
            }
        ]
    )
    return mock_koza('gene-to-phenotype', row, './examples/xenbase/gene-to-phenotype.py')


def test_gene2_phenotype_transform(gene2phenotype_entities):
    assert gene2phenotype_entities
    assert len(gene2phenotype_entities) == 3
    genes = [entity for entity in gene2phenotype_entities if isinstance(entity, Gene)]
    phenotypes = [
        entity for entity in gene2phenotype_entities if isinstance(entity, PhenotypicFeature)
    ]
    associations = [
        entity
        for entity in gene2phenotype_entities
        if isinstance(entity, GeneToPhenotypicFeatureAssociation)
    ]
    assert len(genes) == 1
    assert len(phenotypes) == 1
    assert len(associations) == 1


def test_gene2_phenotype_transform_publications(gene2phenotype_entities):
    associations = [
        entity
        for entity in gene2phenotype_entities
        if isinstance(entity, GeneToPhenotypicFeatureAssociation)
    ]
    assert 'PMID:17112317' in associations[0].publications
