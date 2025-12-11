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

Transform a source file

**Usage**:

```console
$ koza transform [OPTIONS] CONFIGURATION_YAML
```

**Arguments**:

* `CONFIGURATION_YAML`: Configuration YAML file  [required]

**Options**:

* `-i, --input-file TEXT`: Override input files
* `-o, --output-dir TEXT`: Path to output directory  [default: ./output]
* `-f, --output-format [tsv|jsonl|kgx|passthrough]`: Output format  [default: tsv]
* `-n, --limit INTEGER`: Number of rows to process (if skipped, processes entire source file)  [default: 0]
* `-p, --progress`: Display progress of transform
* `-q, --quiet`: Disable log output
* `--help`: Show this message and exit.
