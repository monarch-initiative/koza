import logging
from koza.converter.biolink_converter import gpi2gene

LOG = logging.getLogger(__name__)


def transform(row, translate_table=None, maps=None):
    row['DB_Object_ID'] = "Xenbase:" + row['DB_Object_ID']
    return [gpi2gene(row)]
