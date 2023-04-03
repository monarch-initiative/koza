# `koza`

**Usage**:

```console
$ koza [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `transform`: Transform a source file
* `validate`: Validate a source file

## `koza transform`

Transform a source file

**Usage**:

```console
$ koza transform [OPTIONS]
```

**Options**:

* `--source TEXT`: Source metadata file  [required]
* `--output-dir TEXT`: Path to output directory  [default: ./output]
* `--output-format [tsv|jsonl|kgx]`: Output format  [default: tsv]
* `--global-table TEXT`: Path to global translation table
* `--local-table TEXT`: Path to local translation table
* `--schema TEXT`: Path to schema YAML for validation in writer
* `--row-limit INTEGER`: Number of rows to process (if skipped, processes entire source file)
* `--debug / --quiet`
* `--log / --no-log`: Optional log mode - set true to save output to ./logs  [default: no-log]
* `--help`: Show this message and exit.

## `koza validate`

Validate a source file

Given a file and configuration checks that the file is valid, ie
format is as expected (tsv, json), required columns/fields are there

**Usage**:

```console
$ koza validate [OPTIONS]
```

**Options**:

* `--file TEXT`: Path or url to the source file  [required]
* `--format [csv|jsonl|json|yaml|xml]`: [default: FormatType.csv]
* `--delimiter TEXT`: [default: ,]
* `--header-delimiter TEXT`
* `--skip-blank-lines / --no-skip-blank-lines`: [default: skip-blank-lines]
* `--help`: Show this message and exit.
