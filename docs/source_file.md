### Source File 

This YAML file sets properties for the ingest of a single file type from a within a [Source](http://example.com?link-to-source). 

#### Example

    name: 'gene-to-phenotype'
    
    format: 'json'
    
    files:
    - './data/PHENOTYPE_RGD.json.gz' # "https://fms.alliancegenome.org/download/PHENOTYPE_RGD.json.gz"
    - './data/PHENOTYPE_MGI.json.gz' # "https://fms.alliancegenome.org/download/PHENOTYPE_MGI.json.gz"
    - './data/PHENOTYPE_WB.json.gz' # "https://fms.alliancegenome.org/download/PHENOTYPE_WB.json.gz"
    - './data/PHENOTYPE_HUMAN.json.gz' # "https://fms.alliancegenome.org/download/PHENOTYPE_HUMAN.json.gz"
    
    json_path:
    - 'data'
    
    depends_on:
    - './mingestibles/maps/alliance-gene.yaml'
    
    node_properties:
    - 'id'
    - 'category'
    - 'provided_by'
    
    edge_properties:
    - 'id'
    - 'subject'
    - 'predicate'
    - ...

