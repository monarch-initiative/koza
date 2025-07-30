from collections.abc import Callable
from typing import Any

from koza.transform import KozaTransform

Tag = str | list[str] | None


class KozaTransformHook:
    def __init__(self, fn: Callable[..., Any], tag: Tag):
        self.fn = fn
        self.tag = tag


# @koza.transform()
# Mark a function as being a single transform
class KozaSingleTransformFunction(KozaTransformHook):
    def __call__(self, koza: KozaTransform):
        self.fn(koza)


def transform(tag: Tag = None):
    def decorator(fn: Callable[[KozaTransform], None]):
        return KozaSingleTransformFunction(fn, tag)

    return decorator


# @koza.transform_record()
# Mark a function as being a function to transform single records
class KozaSerialTransformFunction(KozaTransformHook):
    def __call__(self, koza: KozaTransform, data: dict[str, Any]):
        self.fn(koza, data)


def transform_record(tag: Tag = None):
    def decorator(fn: Callable[[KozaTransform, dict[str, Any]], None]):
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
