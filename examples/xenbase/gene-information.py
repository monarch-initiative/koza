import logging

from koza.converter.biolink_converter import gpi2gene
from koza.manager.data_provider import inject_row
from koza.manager.data_collector import collect

LOG = logging.getLogger(__name__)

source_name = 'gene-information'
row = inject_row(source_name)

row['DB_Object_ID'] = "Xenbase:" + row['DB_Object_ID']

gene = gpi2gene(row)

collect(source_name, gene)
