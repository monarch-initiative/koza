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
    def __call__(self, koza: KozaTransform, data: Iterable[Record]) -> Iterable | None:
        return self.fn(koza, data)


def transform(tag: Tag = None):
    """
    Decorator to mark a transformation function.

    A function marked with this hook will be run *once* for all input data for a
    given tag. If your transform can be performed on records one at a time,
    prefer to use `@koza.transform_record()`.

    Usage:

        @koza.transform()
        def do_transform(koza: KozaTransform, data):
            for record in data:
                output = MyOutputObject(
                    name=record["name"],
                    label=record["label"],
                )

                koza.write(output)

    :param tag: The tag with which this hook should be associated.
    """

    def decorator(fn: Callable[[KozaTransform, Iterable[Record]], Iterable | None]):
        return KozaSingleTransformFunction(fn, tag)

    return decorator


# @koza.transform_record()
# Mark a function as being a function to transform single records
class KozaSerialTransformFunction(KozaTransformHook):
    def __call__(self, koza: KozaTransform, data: Record) -> Iterable | None:
        return self.fn(koza, data)


def transform_record(tag: Tag = None):
    """
    Decorator to mark a record transformation function.

    This function will be called on every record for a configured reader. By
    default, these records will be of the type `dict[str, Any]`, but may be
    different if a `@koza.prepare_data` decorator has been configured.

    Usage:

        @koza.transform_record()
        def transform_csv_row(koza: KozaTransform, record: dict[str, Any]):
            output = MyOutputObject(
                name=record["name"],
                label=record["label"],
            )

            koza.write(output)

    :param tag: The tag with which this hook should be associated.
    """

    def decorator(fn: Callable[[KozaTransform, Record], Iterable | None]):
        return KozaSerialTransformFunction(fn, tag)

    return decorator


# @koza.on_data_begin()
# Mark a function as being called before the reader starts
class KozaDataBeginFunction(KozaTransformHook):
    def __call__(self, koza: KozaTransform):
        self.fn(koza)


def on_data_begin(tag: Tag = None):
    """
    Decorator to mark a function to be called before data is read in a transform.

    :param tag: The tag with which this hook should be associated.
    """

    def decorator(fn: Callable[[KozaTransform], None]):
        return KozaDataBeginFunction(fn, tag)

    return decorator


# @koza.on_read_end
# Mark a function as being called after the reader ends
class KozaDataEndFunction(KozaTransformHook):
    def __call__(self, koza: KozaTransform):
        self.fn(koza)


def on_data_end(tag: Tag = None):
    """
    Decorator to mark a function to be called after data is read in a transform.

    :param tag: The tag with which this hook should be associated.
    """

    def decorator(fn: Callable[[KozaTransform], None]):
        return KozaDataEndFunction(fn, tag)

    return decorator
