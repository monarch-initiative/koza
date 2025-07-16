from collections.abc import Callable
from typing import Any

from koza.transform import KozaTransform


class KozaTransformHook:
    def __init__(self, fn: Callable[..., Any]):
        self.fn = fn


# @koza.transform()
# Mark a function as being a single transform
class KozaSingleTransformFunction(KozaTransformHook):
    def __call__(self, koza: KozaTransform):
        self.fn(koza)


def transform():
    def decorator(fn: Callable[[KozaTransform], None]):
        return KozaSingleTransformFunction(fn)

    return decorator


# @koza.transform_record()
# Mark a function as being a function to transform single records
class KozaSerialTransformFunction(KozaTransformHook):
    def __call__(self, koza: KozaTransform, data: dict[str, Any]):
        self.fn(koza, data)


def transform_record():
    def decorator(fn: Callable[[KozaTransform, dict[str, Any]], None]):
        return KozaSerialTransformFunction(fn)

    return decorator


# @koza.on_data_begin()
# Mark a function as being called before the reader starts
class KozaDataBeginFunction(KozaTransformHook):
    def __call__(self, koza: KozaTransform):
        self.fn(koza)


def on_data_begin():
    def decorator(fn: Callable[[KozaTransform], None]):
        return KozaDataBeginFunction(fn)

    return decorator


# @koza.on_read_end
# Mark a function as being called after the reader ends
class KozaDataEndFunction(KozaTransformHook):
    def __call__(self, koza: KozaTransform):
        self.fn(koza)


def on_data_end():
    def decorator(fn: Callable[[KozaTransform], None]):
        return KozaDataEndFunction(fn)

    return decorator
