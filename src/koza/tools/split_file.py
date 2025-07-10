import os

import duckdb

from koza.model.formats import OutputFormat


def split_file(
    file: str,
    fields: str,
    format: OutputFormat = OutputFormat.tsv,
    remove_prefixes: bool = False,
    output_dir: str = "./output",
):
    db = duckdb.connect(":memory:")

    # todo: validate that each of the fields is actually a column in the file
    if format == OutputFormat.tsv:
        read_file = f"read_csv('{file}')"
    elif format == OutputFormat.jsonl:
        read_file = f"read_json('{file}')"
    else:
        raise ValueError(f"Format {format} not supported")

    values = db.execute(f"SELECT DISTINCT {fields} FROM {read_file};").fetchall()
    keys = fields.split(",")
    list_of_value_dicts = [dict(zip(keys, v, strict=False)) for v in values]

    def clean_value_for_filename(value):
        if remove_prefixes and ":" in value:
            value = value.split(":")[-1]

        return value.replace("biolink:", "").replace(" ", "_").replace(":", "_")

    def generate_filename_from_row(row):
        return "_".join([clean_value_for_filename(row[k]) for k in keys if row[k] is not None])

    def get_filename_prefix(name):
        # get just the filename part of the path
        name = os.path.basename(name)
        if name.endswith("_edges.tsv"):
            return name[:-9]
        elif name.endswith("_nodes.tsv"):
            return name[:-9]
        else:
            raise ValueError(f"Unexpected file name {name}, not sure how to make am output prefix for it")

    def get_filename_suffix(name):
        if name.endswith("_edges.tsv"):
            return "_edges.tsv"
        elif name.endswith("_nodes.tsv"):
            return "_nodes.tsv"
        else:
            raise ValueError(f"Unexpected file name {name}, not sure how to make am output prefix for it")

    # create output/split if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    for row in list_of_value_dicts:
        # export to a tsv file named with the values of the pivot fields
        where_clause = " AND ".join([f"{k} = '{row[k]}'" for k in keys])
        file_name = (
            output_dir + "/" + get_filename_prefix(file) + generate_filename_from_row(row) + get_filename_suffix(file)
        )
        print(f"writing {file_name}")
        db.execute(
            f"""
        COPY (
            SELECT * FROM {read_file}
            WHERE {where_clause}
        ) TO '{file_name}' (HEADER, DELIMITER '\t');
        """
        )
