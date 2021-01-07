"""load and make curie_map.yaml available as dict"""
from pathlib import Path
import logging
import yaml


LOG = logging.getLogger(__name__)

curie_yaml = Path(__file__).parent / 'curie_map.yaml'

# read configuration file
curie_map = None

if curie_yaml.exists():
    with open(curie_yaml, 'r') as yaml_file:
        curie_map = yaml.safe_load(yaml_file)
        LOG.debug("Finished loading curie maps: %s", curie_map)
else:
    LOG.debug("Cannot find 'curie_map.yaml' in  %s", Path(__file__).parent)
