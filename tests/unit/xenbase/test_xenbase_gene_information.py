import pytest


@pytest.fixture
def gene_information_entities(mock_koza):
    row = iter(
        [
            {
                'DB': 'Xenbase',
                'DB_Object_ID': 'XB-GENE-478054',
                'DB_Object_Symbol': 'trnt1',
                'DB_Object_Name': 'tRNA nucleotidyl transferase, CCA-adding, 1',
                'DB_Object_Synonym(s)': 'cca1|mtcca|tRNA nucleotidyl transferase|xcca',
                'DB_Object_Type': 'gene',
                'Taxon': 'taxon:8364',
                'Parent_Object_ID': '',
                'DB_Xref(s)': 'NCBI_Gene:394602|UniProtKB:F6V8Z1|UniProtKB:F7DM70|UniProtKB:Q6P873',
                'Properties': '',
            }
        ]
    )

    return mock_koza('gene-information', row, './examples/xenbase/gene-information.py')


def test_gene_information_gene(gene_information_entities):
    assert len(gene_information_entities) == 1
    gene = gene_information_entities[0]
    assert gene


def test_gene_information_synonym(gene_information_entities):
    gene = gene_information_entities[0]
    assert gene.synonym
    assert 'xcca' in gene.synonym


def test_gene_information_id(gene_information_entities):
    gene = gene_information_entities[0]
    assert gene.id == 'Xenbase:XB-GENE-478054'
