from collections.abc import Callable, Iterable
from typing import Any

from koza.transform import KozaTransform, Record

Tag = str | list[str] | None


class KozaTransformHook:
    def __init__(self, fn: Callable[..., Any], tag: Tag):
        self.fn = fn
        self.tag = tag


# @koza.prepare_data()
# Pre-process data before continuing with transform
class KozaPrepareDataFunction(KozaTransformHook):
    def __call__(self, koza: KozaTransform, data: Iterable[Record]) -> Iterable:
        return self.fn(koza, data)


def prepare_data(tag: Tag = None):
    """
    Decorator to prepare input data before starting a transform.

    The return value of a function marked with this decorator will be used as
    the input for the transform function(s) for this transform.

    Usage:

        @koza.prepare_data()
        def convert_to_pandas(koza: KozaTransform, data: Iterable[dict[str, Any]]):
            return pd.DataFrame(data)

        @koza.transform()
        def transform_with_pandas(koza: KozaTransform: data: pd.DataFrame):
            # `data` here is the pandas data frame returned from above

    Any sort of iterator may be returned from this function. For example, a cursor
    from a database query:

        @koza.prepare_data()
        def load_db_data(koza, data):
            conn = db.connect("localhost:9152")
            res = conn.query("SELECT * FROM table")
            return res

        @koza.transform_record()
        def transform_db_row(koza, record):
            # `record` here will be a row from the database query

    :param tag: The tag with which this hook should be associated.
    """

    def decorator(fn: Callable[[KozaTransform, Record], Iterable | None]):
        return KozaPrepareDataFunction(fn, tag)

    return decorator


# @koza.transform()
# Mark a function as being a single transform
class KozaSingleTransformFunction(KozaTransformHook):
    def __call__(self, koza: KozaTransform) -> Iterable | None:
        return self.fn(koza)


def transform(tag: Tag = None):
    def decorator(fn: Callable[[KozaTransform], Iterable | None]):
        return KozaSingleTransformFunction(fn, tag)

    return decorator


# @koza.transform_record()
# Mark a function as being a function to transform single records
class KozaSerialTransformFunction(KozaTransformHook):
    def __call__(self, koza: KozaTransform, data: dict[str, Any]) -> Iterable | None:
        return self.fn(koza, data)


def transform_record(tag: Tag = None):
    def decorator(fn: Callable[[KozaTransform, dict[str, Any]], Iterable | None]):
        return KozaSerialTransformFunction(fn, tag)

    return decorator


# @koza.on_data_begin()
# Mark a function as being called before the reader starts
class KozaDataBeginFunction(KozaTransformHook):
    def __call__(self, koza: KozaTransform):
        self.fn(koza)


def on_data_begin(tag: Tag = None):
    def decorator(fn: Callable[[KozaTransform], None]):
        return KozaDataBeginFunction(fn, tag)

    return decorator


# @koza.on_read_end
# Mark a function as being called after the reader ends
class KozaDataEndFunction(KozaTransformHook):
    def __call__(self, koza: KozaTransform):
        self.fn(koza)


def on_data_end(tag: Tag = None):
    def decorator(fn: Callable[[KozaTransform], None]):
        return KozaDataEndFunction(fn, tag)

    return decorator
