import yaml

from koza.app import load_map
from koza.model.config.source_config import MapFileConfig


def test_declarative_map():
    with open("./examples/maps/entrez-2-string.yaml", 'r') as map_file_fh:
        map_file_config = MapFileConfig(**yaml.safe_load(map_file_fh))

    map = load_map(map_file_config)

    # confirm that entries are loaded from each file
    assert map.get("9606.ENSP00000306894")
    assert map.get("10090.ENSMUSP00000046168")
    assert map.get("7955.ENSDARP00000074307")
    assert map.get("7227.FBpp0293413")["entrez"]
    assert map.get("6239.ZK1053.3")["entrez"]
    assert map.get("4932.YGL077C")["entrez"]

    # confirm that entrez field is filled and accurate
    assert map.get("9606.ENSP00000306894")["entrez"] == "2119"
    assert map.get("7955.ENSDARP00000074307")["entrez"] == "100006444"


def test_procedural_map():
    map_file = "./config/maps/mimtitles.yaml"
    with open(map_file, 'r') as map_file_fh:
        map_file_config = MapFileConfig(**yaml.safe_load(map_file_fh))

    map = load_map(map_file_config, map_file=map_file)

    assert map.get("100050")
    assert map.get("100070")
    assert map.get("100100")
