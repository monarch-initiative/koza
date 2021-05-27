import logging

from koza.manager.data_provider import inject_row
from koza.manager.data_collector import collect
from koza.model.biolink import Gene

LOG = logging.getLogger(__name__)

source_name = 'gene-information'
prefix = 'Xenbase:'

row = inject_row(source_name)

gene = Gene()
gene.id = prefix + row['DB_Object_ID']
gene.symbol = row['DB_Object_Symbol']
gene.name = row['DB_Object_Name']
gene.synonym = row['DB_Object_Synonym(s)'].split("|") if row['DB_Object_Synonym(s)'] else []
gene.in_taxon = [row['Taxon'].replace("taxon:", "NCBITaxon:")]  # not sure this replacement should be necessary?
gene.xref = row['DB_Xref(s)'].split("|") if row['DB_Xref(s)'] else []

collect(source_name, gene)
