import koza


@koza.transform_record()
def transform_record(koza: koza.KozaTransform, record: dict):
    koza.write(
        {
            "STRING": record["STRING"],
            "entrez": record["entrez"],
        }
    )
