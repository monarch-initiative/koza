import pytest

from koza.converter.kgx_converter import KGXConverter
from koza.model.biolink.association import GeneToGeneAssociation
from koza.model.biolink.named_thing import Curie, Gene, Publication


def test_gene_conversion():
    fgf8a = Gene(
        id=Curie("ZFIN:ZDB-GENE-990415-72"), symbol="fgf8a", name="fibroblast growth factor 8a"
    )

    kgx_converter: KGXConverter = KGXConverter()
    (nodes, edges) = kgx_converter.convert([fgf8a])
    output = nodes[0]

    assert output['id'] == "ZFIN:ZDB-GENE-990415-72"
    assert output['symbol'] == "fgf8a"
    assert 'gene' in str(output['category']).lower()
    assert output['name'] == "fibroblast growth factor 8a"


def test_association_conversion():
    fgf8a = Gene(
        id=Curie("ZFIN:ZDB-GENE-990415-72"), symbol="fgf8a", name="fibroblast growth factor 8a"
    )
    pax2a = Gene(id=Curie("ZFIN:ZDB-GENE-990415-8"), symbol="pax2a", name="paired box 2a")
    pub = Publication(id=Curie("PMID:17522161"))
    predicate = Curie("RO:0003003")
    association = GeneToGeneAssociation(
        subject=fgf8a.id, predicate=predicate, object=pax2a.id, publications=[pub]
    )

    (nodes, edges) = KGXConverter().convert([fgf8a, pax2a, pub, association])

    output = edges[0]
    assert output['subject'] == Curie("ZFIN:ZDB-GENE-990415-72")
    assert output['predicate'] == Curie("RO:0003003")
    assert output['object'] == Curie("ZFIN:ZDB-GENE-990415-8")
    assert Curie("PMID:17522161") in output['publications']


@pytest.mark.parametrize(
    "id, symbol, synonym, xref",
    [
        ("MGI:1917258", "Ace2", ["RIKEN cDNA 2010305L05 gene", "2010305L05Rik"], []),
        ("RGD:620474", "Sox9", [], ["ENSEMBL:ENSRNOG00000002607", "NCBI_Gene:140586"]),
    ],
)
def test_keys_uniformity(id, symbol, synonym, xref):
    """
    Connfirm that the result of the conversion has all of the same fields, even if some aren't used
    """
    gene = Gene(id=Curie(id), symbol=symbol, synonym=synonym, xref=xref)

    (nodes, edges) = KGXConverter().convert([gene])
    output = nodes[0]

    assert 'category' in output.keys()
    assert 'id' in output.keys()
    assert 'symbol' in output.keys()
    assert 'synonym' in output.keys()
    assert 'xref' in output.keys()
    assert 'description' in output.keys()
    assert 'source' in output.keys()
