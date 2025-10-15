import importlib
import sys
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from itertools import chain
from pathlib import Path
from types import ModuleType
from typing import Any, TypeAlias, TypeVar, cast

import yaml
from loguru import logger
from mergedeep import merge

from koza import decorators
from koza.io.writer.jsonl_writer import JSONLWriter
from koza.io.writer.passthrough_writer import PassthroughWriter
from koza.io.writer.tsv_writer import TSVWriter
from koza.io.writer.writer import KozaWriter
from koza.io.yaml_loader import UniqueIncludeLoader
from koza.model.formats import OutputFormat
from koza.model.graphs import KnowledgeGraph
from koza.model.koza import KozaConfig
from koza.model.source import Source
from koza.transform import KozaTransform, Mappings, Record
from koza.utils.exceptions import NoTransformException

T = TypeVar("T", bound=decorators.KozaTransformHook)
TaggedFunctions: TypeAlias = dict[str | None, list[T]]


def get_instances(cls: type[T], from_list: list[Any]) -> list[T]:
    return [x for x in from_list if isinstance(x, cls)]


@dataclass
class KozaTransformHooks:
    prepare_data: list[decorators.KozaPrepareDataFunction] = field(default_factory=list)
    transform: list[decorators.KozaSingleTransformFunction] = field(default_factory=list)
    transform_record: list[decorators.KozaSerialTransformFunction] = field(default_factory=list)
    on_data_begin: list[decorators.KozaDataBeginFunction] = field(default_factory=list)
    on_data_end: list[decorators.KozaDataEndFunction] = field(default_factory=list)


def load_transform(transform_module: ModuleType | None) -> dict[str | None, KozaTransformHooks]:
    if transform_module is None:
        return {}

    module_contents = list(vars(transform_module).values())

    hook_class_map: dict[str, type[decorators.KozaTransformHook]] = {
        "prepare_data": decorators.KozaPrepareDataFunction,
        "transform": decorators.KozaSingleTransformFunction,
        "transform_record": decorators.KozaSerialTransformFunction,
        "on_data_begin": decorators.KozaDataBeginFunction,
        "on_data_end": decorators.KozaDataEndFunction,
    }

    by_tag: defaultdict[str | None, KozaTransformHooks] = defaultdict(KozaTransformHooks)

    for fn_name, fn_class in hook_class_map.items():
        hooks = get_instances(fn_class, module_contents)
        for hook in hooks:
            tags = hook.tag if isinstance(hook.tag, list) else [hook.tag]
            for tag in tags:
                getattr(by_tag[tag], fn_name).append(hook)

    for tag, hooks in by_tag.items():
        tag_str = "" if tag is None else f"[{tag}] "
        for hook_type, hook_fns in asdict(hooks).items():
            for hook_fn in hook_fns:
                logger.debug(
                    f"{tag_str}Found `{hook_type}` function `{transform_module.__name__}.{hook_fn.fn.__name__}`"
                )

    return dict(by_tag)


class KozaRunner:
    def __init__(
        self,
        data: Iterable[Record] | dict[str | None, Iterable[Record]],
        writer: KozaWriter,
        hooks: KozaTransformHooks | dict[str | None, KozaTransformHooks],
        base_directory: Path | None = None,
        input_files_dir: Path | None = None,
        mapping_filenames: list[str] | None = None,
        extra_transform_fields: dict[str, Any] | None = None,
    ):
        if isinstance(data, dict):
            # This cast is necessary because a dict with Records as keys is an
            # Iterable[Record]. So... don't pass a dict with records as its keys.
            self.data = cast(dict[str | None, Iterable[Record]], data)
        else:
            self.data: dict[str | None, Iterable[Record]] = {None: data}
        self.writer = writer
        self.base_directory = base_directory
        self.input_files_dir = input_files_dir
        self.mapping_filenames = mapping_filenames or []
        self.extra_transform_fields = extra_transform_fields or {}
        self.transform_metadata: dict[str, Any] = {}

        if isinstance(hooks, dict):
            self.hooks_by_tag = hooks
        else:
            self.hooks_by_tag: dict[str | None, KozaTransformHooks] = {None: hooks}

    def run_for_tag(self, tag: str | None, mappings: Mappings):
        data = self.data[tag]
        hooks = self.hooks_by_tag.get(tag, None)

        if hooks is None or (not hooks.transform and not hooks.transform_record):
            raise NoTransformException("Must define one of `@koza.transform` or `@koza.transform_record`")

        if hooks.transform and hooks.transform_record:
            raise ValueError("Can only define one of `@koza.transform` or `@koza.transform_record`")

        if not hooks.transform_record and len(hooks.transform) > 1:
            raise ValueError("Can only define one `@koza.transform` function")

        if hooks.prepare_data and len(hooks.prepare_data) > 1:
            raise ValueError("Can only define one `@koza.prepare_data` function")

        transform = KozaTransform(mappings=mappings,
                                  writer=self.writer,
                                  input_files_dir=self.input_files_dir,
                                  extra_fields=self.extra_transform_fields)

        if hooks.prepare_data:
            data = hooks.prepare_data[0](transform, data)

        for fn in hooks.on_data_begin:
            fn(transform)

        if hooks.transform:
            logger.info("Running single transform")
            transform_fn = hooks.transform[0]
            result = transform_fn(transform, data)
            if result is not None:
                # this looks weird, but it's just looking at the first result and checking if it's a KnowledgeGraph
                # it uses this iterator approach so that it can handle generators as well as other iterables without
                # consuming the whole generator
                result_iterator = iter(result)
                first_result = next(result_iterator)
                results = chain([first_result], result_iterator) # add the first result back
                if isinstance(first_result, KnowledgeGraph):
                    for kg in results:
                        # for results that are KnowledgeGraphs, write the nodes and edges explicitly
                        self.writer.write_nodes(kg.nodes)
                        self.writer.write_edges(kg.edges)
                else:
                    # otherwise rely on the writer to handle all the entities appropriately
                    self.writer.write(results)

        elif hooks.transform_record:
            logger.info("Running serial transform")
            for item in data:
                for transform_record_fn in hooks.transform_record:
                    result = transform_record_fn(transform, item)
                    if result is not None:
                        if isinstance(result, KnowledgeGraph):
                            self.writer.write_nodes(result.nodes)
                            self.writer.write_edges(result.edges)
                        else:
                            self.writer.write(result)

        for fn in hooks.on_data_end:
            fn(transform)

        self.transform_metadata.update(transform.transform_metadata)

    def run(self):
        mappings = self.load_mappings()

        for tag in self.data:
            self.run_for_tag(tag, mappings)

        self.writer.finalize()

        return self.writer

    def load_mappings(self):
        mappings: Mappings = {}

        if self.mapping_filenames:
            logger.info("Loading mappings")

        for mapping_config_filename in self.mapping_filenames:
            mapping_config = Path(mapping_config_filename)
            if not mapping_config.is_absolute():
                if self.base_directory is None:
                    raise ValueError("Cannot load config maps without a `base_directory` set.")
                mapping_config = self.base_directory / mapping_config

            # Check if a transform has been defined for the mapping
            config, map_runner = KozaRunner.from_config_file(
                str(mapping_config),
                output_format=OutputFormat.passthrough,
            )
            try:
                map_runner.run()
                data = map_runner.writer.result()
                assert isinstance(data, list)
            except NoTransformException:
                data = map_runner.data[None]

            mapping_entry: dict[str, dict[str, str]] = {}
            key_column: str | None = map_runner.extra_transform_fields.get("key", None)
            value_columns: list[str] | None = map_runner.extra_transform_fields.get("values", None)

            if key_column is None:
                raise ValueError(f"Must define transform mapping key column in configuration for {config.name}")

            if not isinstance(value_columns, list):
                raise ValueError(
                    "Must define a list of transform mapping value columns in configuration for {config.name}"
                )

            for row in data:
                item_key = row[key_column]

                mapping_entry[str(item_key)] = {
                    key: value
                    for key, value in row.items()
                    if key in value_columns
                    #
                }

            mappings[config.name] = mapping_entry

        if self.mapping_filenames:
            logger.info("Completed loading mappings")

        return mappings

    @classmethod
    def from_config(
        cls,
        config: KozaConfig,
        base_directory: Path,
        output_dir: str = "",
        input_files_dir: str = "",
        row_limit: int = 0,
        show_progress: bool = False,
    ):
        module_name: str | None = None
        transform_module: ModuleType | None = None

        if config.transform.code:
            transform_code_path = Path(config.transform.code)
            if not transform_code_path.is_absolute():
                transform_code_path = base_directory / transform_code_path
            parent_path = transform_code_path.absolute().parent
            module_name = transform_code_path.stem
            logger.debug(f"Adding `{parent_path}` to system path to load transform module")
            sys.path.append(str(parent_path))
            # FIXME: Remove this from sys.path
        elif config.transform.module:
            module_name = config.transform.module

        if module_name:
            logger.debug(f"Loading module `{module_name}`")
            transform_module = importlib.import_module(module_name)

        hooks_by_tag = load_transform(transform_module)

        sources_by_tag: dict[str | None, Iterable[Record]] = {
            reader.tag: iter(
                Source(
                    reader.reader,
                    base_directory,
                    row_limit=row_limit,
                    show_progress=show_progress,
                )
            )
            for reader in config.get_readers()
        }

        writer: KozaWriter | None = None

        if config.writer.format == OutputFormat.tsv:
            writer = TSVWriter(output_dir=output_dir, source_name=config.name, config=config.writer)
        elif config.writer.format == OutputFormat.jsonl:
            writer = JSONLWriter(output_dir=output_dir, source_name=config.name, config=config.writer)
        elif config.writer.format == OutputFormat.passthrough:
            writer = PassthroughWriter()

        if writer is None:
            raise ValueError("No writer defined")

        return cls(
            data=sources_by_tag,
            writer=writer,
            base_directory=base_directory,
            input_files_dir=Path(input_files_dir) if input_files_dir else None,
            mapping_filenames=config.transform.mappings,
            extra_transform_fields=config.transform.extra_fields,
            hooks=hooks_by_tag,
        )

    @classmethod
    def from_config_file(
        cls,
        config_filename: str,
        output_dir: str = "",
        output_format: OutputFormat | None = None,
        row_limit: int = 0,
        input_files: list[str] | dict[str, list[str]] | None = None,
        input_files_dir: str | None = None,
        show_progress: bool = False,
        overrides: dict | None = None,
    ):
        transform_code_path: Path | None = None
        config_path = Path(config_filename)

        logger.info(f"Loading configuration from `{config_filename}`")

        with config_path.open("r") as fh:
            config_dict = yaml.load(fh, Loader=UniqueIncludeLoader.with_file_base(str(config_path)))  # noqa: S506
            config = KozaConfig(**config_dict)

        if not config.transform.code and not config.transform.module:
            # If config file is named:
            #   /path/to/transform_name.yaml
            # then look for a transform at
            #   /path/to/transform_name.py
            mirrored_path = config_path.parent / f"{config_path.stem}.py"

            # Otherwise, look for a file named transform.py in the same directory
            transform_literal_path = config_path.parent / "transform.py"

            if mirrored_path.exists():
                transform_code_path = Path(mirrored_path.name)
            elif transform_literal_path.exists():
                transform_code_path = Path(transform_literal_path.name)

            if transform_code_path:
                logger.debug(f"Using transform code from `{mirrored_path}`")

        # Override any necessary fields
        config_dict = asdict(config)
        _overrides = {}
        if output_format is not None:
            _overrides["writer"] = {
                "format": output_format,
            }
        if transform_code_path is not None:
            _overrides["transform"] = {
                "code": str(transform_code_path),
            }
        if input_files is not None:
            if isinstance(input_files, list):
                _overrides["reader"] = {"files": input_files}
            elif config.readers:
                _overrides["readers"] = {}
                for reader in config.get_readers():
                    if reader.tag in input_files:
                        _overrides["readers"][reader.tag] = input_files[reader.tag]
        # if an input_files_dir is provided prepend it to all the input file values
        if input_files_dir is not None:
            if config.reader:
                # if only one reader
                for tagged_reader in config.get_readers():
                    if "reader" not in _overrides:
                        _overrides["reader"] = {}
                    if "files" in _overrides["reader"]:
                        # if files were already overridden start with those
                        files_to_alter = _overrides["reader"]["files"]
                    else:
                        # otherwise take the files from the config
                        files_to_alter = tagged_reader.reader.files

                    # prepend the input_files_dir to all the files
                    _overrides["reader"]["files"] = [str(Path(input_files_dir) / file) for file in files_to_alter]
            elif config.readers:
                # multiple readers
                if "readers" not in _overrides:
                    _overrides["readers"] = {}
                for tagged_reader in config.get_readers():
                    if tagged_reader.tag not in _overrides["readers"]:
                        _overrides["readers"][tagged_reader.tag] = {}
                    if "files" in _overrides["readers"][tagged_reader.tag]:
                        files_to_alter = _overrides["readers"][tagged_reader.tag]["files"]
                    else:
                        files_to_alter = tagged_reader.reader.files
                    _overrides["readers"][tagged_reader.tag]["files"] = [str(Path(input_files_dir) / file)
                                                                         for file in files_to_alter]
            else:
                raise ValueError("Input file directory was provided but no readers were defined.")

        config_dict = merge(config_dict, _overrides, overrides or {})
        config = KozaConfig(**config_dict)

        return config, cls.from_config(
            config,
            base_directory=config_path.parent,
            output_dir=output_dir,
            input_files_dir=input_files_dir,
            row_limit=row_limit,
            show_progress=show_progress,
        )
