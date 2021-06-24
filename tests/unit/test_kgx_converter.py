import pytest
from biolink_model_pydantic.model import Curie, Gene, GeneToGeneAssociation, Predicate, Publication

from koza.converter.kgx_converter import KGXConverter


def test_gene_conversion():
    fgf8a = Gene(
        id=Curie("ZFIN:ZDB-GENE-990415-72"),
        symbol="fgf8a",
        name="fibroblast growth factor 8a",
        in_taxon=["NCBITaxon:7955"],
    )

    kgx_converter: KGXConverter = KGXConverter()
    (nodes, edges) = kgx_converter.convert([fgf8a])
    output = nodes[0]

    assert output['id'] == "ZFIN:ZDB-GENE-990415-72"
    assert output['symbol'] == "fgf8a"
    assert 'gene' in str(output['category']).lower()
    assert output['name'] == "fibroblast growth factor 8a"
    assert output['in_taxon'] == ["NCBITaxon:7955"]


def test_association_conversion():
    fgf8a = Gene(
        id=Curie("ZFIN:ZDB-GENE-990415-72"), symbol="fgf8a", name="fibroblast growth factor 8a"
    )
    pax2a = Gene(id=Curie("ZFIN:ZDB-GENE-990415-8"), symbol="pax2a", name="paired box 2a")
    pub = Publication(id=Curie("PMID:17522161"), type="MESH:foobar")
    association = GeneToGeneAssociation(
        id='uuid:123',
        subject=fgf8a.id,
        predicate=Predicate.interacts_with,
        object=pax2a.id,
        publications=[pub],
        relation="RO:0003003",
    )

    (nodes, edges) = KGXConverter().convert([fgf8a, pax2a, pub, association])

    output = edges[0]
    assert output['subject'] == Curie("ZFIN:ZDB-GENE-990415-72")
    assert output['relation'] == Curie("RO:0003003")
    assert output['object'] == Curie("ZFIN:ZDB-GENE-990415-8")
    # TODO figure out how/where to handle this conversion
    # assert Curie("PMID:17522161") in output['publications']


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
