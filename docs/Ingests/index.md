<sub>
(For CLI usage, see the [CLI commands](../Usage/CLI.md) page.)
</sub>  

Koza is designed to process and transform existing data into a target csv/json/jsonl format.  

This process is internally known as an **ingest**. Ingests are defined by:  

1. [Koza config file yaml](./koza_config.md): Koza ingest configuration, including:
    -  metadata, formats, required columns, any SSSOM files, etc. 
1. [Map config yaml](./mapping.md): (Optional) configures creation of mapping dictionary  
1. [Transform code](./transform.md): a Python script, with specific transform instructions 
