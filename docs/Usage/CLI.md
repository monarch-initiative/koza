# `koza`

**Usage**:

```console
$ koza [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--version`
* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `transform`: Transform a source file

## `koza transform`

Transform a source file.

Accepts either a config YAML file or a Python transform file directly.

**Usage**:

```console
# Config file mode (traditional)
$ koza transform [OPTIONS] CONFIG.yaml

# Config-free mode with Python transform (input files as positional args)
$ koza transform [OPTIONS] TRANSFORM.py [INPUT_FILES]...
```

**Arguments**:

* `CONFIG_OR_TRANSFORM`: Configuration YAML file OR Python transform file  [required]
* `INPUT_FILES`: Input files (supports shell glob expansion)
  - **Config-free mode** (`.py` file): Required. These files are processed by the transform.
  - **Config file mode** (`.yaml` file): Optional. If provided, overrides the `files` list in the config's reader section.

**Options**:

* `--input-format`: Input format (auto-detected from extension if not specified)
* `-d, --delimiter TEXT`: Field delimiter for CSV/TSV files (default: tab for .tsv, comma for .csv)
* `-o, --output-dir TEXT`: Path to output directory  [default: ./output]
* `-f, --output-format [tsv|jsonl|parquet]`: Output format  [default: tsv]
* `-n, --limit INTEGER`: Number of rows to process (if skipped, processes entire source file)  [default: 0]
* `-p, --progress`: Display progress of transform
* `-q, --quiet`: Disable log output
* `--help`: Show this message and exit.

**Examples**:

```console
# Config file mode
$ koza transform examples/string/protein-links-detailed.yaml

# Config file mode with input file override
$ koza transform config.yaml different_data.tsv

# Config-free mode with Python transform
$ koza transform transform.py -o ./output -f jsonl data/*.yaml
```
