from koza.converter.biolink_converter import phaf2gene, phaf2gene_pheno_association, phaf2phenotype

phaf_example = {
    'Database name': 'PomBase',
    'Gene systematic ID': 'SPAC1805.05',
    'FYPO ID': 'FYPO:0001838',
    'Allele description': 'C433S,C434S',
    'Expression': 'Not assayed',
    'Parental strain': '972 h-',
    'Strain name (background)': '',
    'Genotype description': '',
    'Gene name': 'cki3',
    'Allele name': 'cki3-SS',
    'Allele synonym': '',
    'Allele type': 'amino_acid_mutation',
    'Evidence': 'Western blot assay',
    'Condition': '',
    'Penetrance': '',
    'Severity': '',
    'Extension': 'assayed_using(PomBase:SPCC1223.06)',
    'Reference': 'PMID:26525038',
    'Taxon': '4896',
    'Date': '20151208',
}


def test_phaf2gene():
    gene = phaf2gene(phaf_example, "POMBASE:", "NCBITaxon:")

    assert gene.id == 'POMBASE:' + phaf_example['Gene systematic ID']
    assert 'NCBITaxon:' + phaf_example['Taxon'] in gene.in_taxon


def test_phaf2phenotype():
    phenotype = phaf2phenotype(phaf_example)

    assert phenotype.id == phaf_example['FYPO ID']


def test_phaf2gene_pheno_association():

    gene = phaf2gene(phaf_example, "POMBASE:", "NCBITaxon:")
    phenotype = phaf2phenotype(phaf_example)
    association = phaf2gene_pheno_association(phaf_example, gene, phenotype, 'RO:0002200')

    assert association.subject == gene.id
    assert association.object == phenotype.id
    assert phaf_example['Reference'] in association.publications
