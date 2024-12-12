import importlib
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional

import loguru
import yaml

from koza.io.writer.jsonl_writer import JSONLWriter
from koza.io.writer.tsv_writer import TSVWriter
from koza.io.writer.writer import KozaWriter
from koza.io.yaml_loader import UniqueIncludeLoader
from koza.model.config.source_config import KozaConfig, OutputFormat
from koza.model.source import Source

Record = Dict[str, Any]


def is_function(obj: object, attr: str):
    return hasattr(obj, attr) and callable(getattr(obj, attr))


@dataclass
class KozaTransform(ABC):
    writer: KozaWriter
    logger: "loguru.Logger"

    @property
    @abstractmethod
    def data(self) -> Iterator[Record]: ...

    def write(self, *records: Record, writer: Optional[str] = None) -> None:
        """Write a series of records to a writer.

        The writer argument specifies the specific writer to write to (named
        writers not yet implemented)
        """
        self.writer.write(records)

    @abstractmethod
    def lookup(self, name: str, map_name: Optional[str]) -> str:
        """Look up a term in the configured mappings.

        In the one argument form:

            koza.lookup("name")

        It will look for the first match for "name" in the configured mappings.
        The first mapping will have precendence over any proceeding ones.

        If a map name is provided, only that named mapping will be used:

            koza.lookup("name", map_name="mapping_a")

        """
        ...

    @abstractmethod
    def log(self, msg: str, level: str = "INFO") -> None:
        """Log a message."""
        ...

    @property
    @abstractmethod
    def current_reader(self) -> str:
        """Returns the reader for the last row read.

        Useful for getting the filename of the file that a row was read from:

            for row in koza.iter_rows():
                filename = koza.current_reader.filename
        """
        ...


@dataclass
class SingleTransform(KozaTransform):
    _data: Iterator[Record]

    @property
    def data(self):
        return self._data

    def lookup(self, name: str, map_name: Optional[str]) -> str:
        raise NotImplementedError()

    def log(self, msg: str, level: str = "INFO") -> None:
        raise NotImplementedError()

    @property
    def current_reader(self):
        raise NotImplementedError()


@dataclass
class SerialTransform(KozaTransform):
    @property
    def data(self):
        raise NotImplementedError()

    def lookup(self, name: str, map_name: Optional[str]) -> str:
        raise NotImplementedError()

    def log(self, msg: str, level: str = "INFO") -> None:
        raise NotImplementedError()

    @property
    def current_reader(self):
        raise NotImplementedError()


class KozaRunner:
    def __init__(
        self,
        data: Iterator[Record],
        writer: KozaWriter,
        logger: Optional["loguru.Logger"] = None,
        transform_record: Optional[Callable[[KozaTransform, Record], None]] = None,
        transform: Optional[Callable[[KozaTransform], None]] = None,
    ):
        if callable(transform) and callable(transform_record):
            raise ValueError("Can only define one of `transform` or `transform_record`")

        if not transform and not transform_record:
            raise ValueError("Must define one of `transform` or `transform_record`")

        self.transform_record = transform_record
        self.transform = transform

        self.data = data
        self.writer = writer

        if logger:
            self.logger = logger
        else:
            self.logger = loguru.logger

    def run_single(self):
        fn = self.transform
        if fn is None:
            raise ValueError("Can only be run when `transform` is defined")

        transform = SingleTransform(writer=self.writer, _data=self.data, logger=self.logger)
        fn(transform)

    def run_serial(self):
        fn = self.transform_record
        if fn is None:
            raise ValueError("Can only be run when `transform_record` is defined")

        transform = SerialTransform(writer=self.writer, logger=self.logger)
        for item in self.data:
            fn(transform, item)

    def run(self):
        if callable(self.transform):
            self.run_single()
        elif callable(self.transform_record):
            self.run_serial()

    @classmethod
    def from_config(cls, config: KozaConfig, transform_code_path: Optional[Path] = None, output_dir: str = ""):
        if transform_code_path is None and config.transform.code:
            transform_code_path = Path(config.transform.code)

        if transform_code_path is None:
            raise ValueError()

        parent_path = transform_code_path.absolute().parent
        module_name = transform_code_path.stem
        sys.path.append(str(parent_path))
        transform_module = importlib.import_module(module_name)

        transform = getattr(transform_module, "transform", None)
        transform_record = getattr(transform_module, "transform_record", None)
        source = Source(config)

        writer: Optional[KozaWriter] = None


        if config.writer.format == OutputFormat.tsv:
            writer = TSVWriter(output_dir=output_dir, source_name=config.name, config=config.writer)
        if config.writer.format == OutputFormat.jsonl:
            writer = JSONLWriter(output_dir=output_dir, source_name=config.name, config=config.writer)

        if writer is None:
            raise ValueError("No writer defined")

        return cls(
            transform=transform,
            transform_record=transform_record,
            data=iter(source),
            writer=writer,
        )

    @classmethod
    def from_config_file(cls, config_filename: str, output_dir: str = ""):
        transform_code_path = None
        config_path = Path(config_filename)

        with config_path.open("r") as fh:
            config = KozaConfig(**yaml.load(fh, Loader=UniqueIncludeLoader))  # noqa: S506

        if not config.transform.code:

            # If config file is named:
            #   /path/to/transform_name.yaml
            # then look for a transform at
            #   /path/to/transform_name.py
            transform_code_path = config_path.parent / f"{config_path.stem}.py"

            # Otherwise, look for a file named transform.py in the same directory
            if not transform_code_path.exists():
                transform_code_path = config_path.parent / "transform.py"

            if not transform_code_path.exists():
                raise FileNotFoundError(f"Could not find transform file for {config_filename}")

        return cls.from_config(
            config,
            output_dir=output_dir,
            transform_code_path=transform_code_path,
        )
