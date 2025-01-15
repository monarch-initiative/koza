from koza.runner import KozaTransform


def transform_record(koza: KozaTransform, record: dict):
    koza.write(
        {
            "STRING": record["STRING"],
            "entrez": record["entrez"],
        }
    )
