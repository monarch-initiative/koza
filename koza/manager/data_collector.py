"""
Functions that aggregate biolink models and facilitate serialization(s)

Implement a producer-consumer design pattern here?
https://asyncio.readthedocs.io/en/latest/producer_consumer.html

leaning towards using async for all serialization
"""

from koza.koza_runner import get_koza_app



def serialize(ingest_name: str, *args):
    # koza = get_koza_app()
    # koza.serialize(ingest_name, *args)
    pass
