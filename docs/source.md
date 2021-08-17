### Source (aka metadata.yaml)

The Source File provides metadata for the description of the dataset and the list of Source Files to be ingested

#### Example
    name: 'xenbase'

    dataset_description:
      ingest_title: 'Xenbase'
      ingest_url: 'https://xenbase.org'
      description: 'Xenbase: The Xenopus Model Organism Knowledgebase'
      rights: 'https://www.xenbase.org/other/static-xenbase/citingMOD.jsp'

    source_files:
      - 'gene-information.yaml'
      - 'gene-to-phenotype.yaml'
      - 'gene-literature.yaml'

#### Properties

<dl>
<dt>name</dt>
<dd>The name of this ingest</dd>

<dt>dataset_description.ingest_title</dt>
<dd>The title of the ingest</dd>

<dt>dataset_description.ingest_url</dt>
<dd>Homepage of ingest organization</dd>

<dt>dataset_description.description</dt>
<dd>Description of organization</dd>

<dt>dataset_description.rights</dt>
<dd>URL for a page describing data usage policies</dd>

<dt>source_files</dt>
<dd>List of [Source Files](http://example.com#link-to-source-file-doc)</dd>

</dl>
