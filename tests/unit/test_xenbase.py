from examples.xenbase.gene_information import transform as gene_information_transform
from examples.xenbase.gene2phenotype import transform as gene2phenotype_transform
from examples.xenbase.gene_literature import transform as gene_literature_transform
from biolink_model_pydantic.model import Publication, Gene, NamedThingToInformationContentEntityAssociation, \
    PhenotypicFeature, GeneToPhenotypicFeatureAssociation
from koza.koza_runner import get_translation_table


def test_gene_information_transform():
    row = {'DB': 'Xenbase', 'DB_Object_ID': 'XB-GENE-478054', 'DB_Object_Symbol': 'trnt1', 'DB_Object_Name': 'tRNA nucleotidyl transferase, CCA-adding, 1', 'DB_Object_Synonym(s)': 'cca1|mtcca|tRNA nucleotidyl transferase|xcca', 'DB_Object_Type': 'gene', 'Taxon': 'taxon:8364', 'Parent_Object_ID': '', 'DB_Xref(s)': 'NCBI_Gene:394602|UniProtKB:F6V8Z1|UniProtKB:F7DM70|UniProtKB:Q6P873', 'Properties': ''}
    entities = gene_information_transform(row)
    assert len(entities) == 1
    gene = entities[0]
    assert gene
    assert gene.synonym
    assert gene.id == 'Xenbase:XB-GENE-478054'
    assert 'xcca' in gene.synonym


def test_gene2_phenotype_transform():
    row = {'SUBJECT': 'XB-GENE-1000632', 'SUBJECT_LABEL': 'dctn2', 'SUBJECT_TAXON': 'NCBITaxon:8364', 'SUBJECT_TAXON_LABEL': 'Xla', 'OBJECT': 'XPO:0102358', 'OBJECT_LABEL': 'abnormal tail morphology', 'RELATION': 'RO_0002200', 'RELATION_LABEL': 'has_phenotype', 'EVIDENCE': '', 'EVIDENCE_LABEL': '', 'SOURCE': 'PMID:17112317', 'IS_DEFINED_BY': '', 'QUALIFIER': ''}
    entities = gene2phenotype_transform(row)
    assert(entities)
    assert(len(entities) == 3)
    genes = [entity for entity in entities if isinstance(entity, Gene)]
    phenotypes = [entity for entity in entities if isinstance(entity, PhenotypicFeature)]
    associations = [entity for entity in entities if isinstance(entity, GeneToPhenotypicFeatureAssociation)]
    assert len(genes) == 1
    assert len(phenotypes) == 1
    assert len(associations) == 1
    assert 'PMID:17112317' in associations[0].publications


def test_gene_literature_transform():
    row = {'xb_article': 'XB-ART-1', 'pmid': '16938438', 'gene_pages': 'XB-GENEPAGE-487723 nog,XB-GENEPAGE-490377 msx1,XB-GENEPAGE-481828 bmp2,XB-GENEPAGE-483057 bmp4,XB-GENEPAGE-480982 fgf8,XB-GENEPAGE-6045068 hspa1l,XB-GENEPAGE-485625 hsp70'}
    maps = {
        'genepage-2-gene': {
            'XB-GENEPAGE-487723': {'tropicalis_id': 'XB-GENE-487724', 'laevis_l_id': 'XB-GENE-864891', 'laevis_s_id': 'XB-GENE-17332089'},
            'XB-GENEPAGE-490377': {'tropicalis_id': 'XB-GENE-490378', 'laevis_l_id': 'XB-GENE-490382', 'laevis_s_id': 'XB-GENE-6253888'},
            'XB-GENEPAGE-481828': {'tropicalis_id': 'XB-GENE-481829', 'laevis_l_id': 'XB-GENE-6252323', 'laevis_s_id': 'XB-GENE-481833'},
            'XB-GENEPAGE-483057': {'tropicalis_id': 'XB-GENE-483058', 'laevis_l_id': 'XB-GENE-483062', 'laevis_s_id': 'XB-GENE-6254046'},
            'XB-GENEPAGE-480982': {'tropicalis_id': 'XB-GENE-480983', 'laevis_l_id': 'XB-GENE-865429', 'laevis_s_id': 'XB-GENE-17330198'},
            'XB-GENEPAGE-6045068': {'tropicalis_id': 'XB-GENE-6045069', 'laevis_l_id': 'XB-GENE-17342842', 'laevis_s_id': 'XB-GENE-6254949'},
            'XB-GENEPAGE-485625': {'tropicalis_id': 'XB-GENE-485626', 'laevis_l_id': 'XB-GENE-485630', 'laevis_s_id': 'XB-GENE-17340402'}
        }
    }
    tt = get_translation_table("examples/translation_table.yaml", None)
    entities = gene_literature_transform(row, tt, maps)
    assert entities
    publications = [entity for entity in entities if isinstance(entity, Publication)]
    genes = [entity for entity in entities if isinstance(entity, Gene)]
    associations = [entity for entity in entities if isinstance(entity, NamedThingToInformationContentEntityAssociation)]

    # a roundabout way of confirming that everything generated is one of these three and there's nothing else
    assert len(entities) == len(publications) + len(genes) + len(associations)
    assert len(publications) == 1
    # confirm one gene id from each species
    assert 'Xenbase:XB-GENE-480983' in [gene.id for gene in genes]
    assert 'Xenbase:XB-GENE-6253888' in [gene.id for gene in genes]
    assert 'Xenbase:XB-GENE-485630' in [gene.id for gene in genes]
