import logging

from koza.cli_runner import koza_app
from koza.converter.biolink_converter import gpi2gene

LOG = logging.getLogger(__name__)

row = koza_app.get_row('gene-information')

row['DB_Object_ID'] = "Xenbase:" + row['DB_Object_ID']

gene = gpi2gene(row)

koza_app.write(gene)
