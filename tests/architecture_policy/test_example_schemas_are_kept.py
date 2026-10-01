import inspect
from pathlib import Path
from types import ModuleType

from base_pydantic_schemas import (
    ArbitraryImmutableDTO,
    ArbitraryMutableDTO,
    BaseDocument,
    ImmutableDTO,
    MutableDTO,
    PersistentDocument,
    UnixMicrosecondTimestampedMixin,
    UnixMillisecondTimestampedMixin,
    UnixNanosecondTimestampedMixin,
    VersionedMixin,
)
from base_typed_float import BaseConstrainedTypedFloat, BaseTypedFloat
from base_typed_id import BasePrefixedTypedId, BaseTypedId
from base_typed_int import BaseConstrainedTypedInt, BaseTypedInt
from base_typed_string import BaseConstrainedTypedString, BaseTypedString

import app.schemas.typings.booleans as boolean_typings
from app.schemas.configurations.example_config import ExampleConfig
from app.schemas.domain.example_document import (
    ExampleDocument,
    ExampleMicrosecondTimestampedDocument,
    ExampleMillisecondTimestampedDocument,
    ExampleNanosecondTimestampedDocument,
    ExamplePersistentDocument,
)
from app.schemas.dto.example_dto import (
    ExampleArbitraryImmutableDTO,
    ExampleArbitraryMutableDTO,
    ExampleImmutableDTO,
    ExampleMutableDTO,
)
from app.schemas.typings.constrained_floats import ExampleConstrainedFloat
from app.schemas.typings.constrained_integers import ExampleConstrainedInt
from app.schemas.typings.constrained_strings import ExampleConstrainedString
from app.schemas.typings.floats import ExampleFloat
from app.schemas.typings.ids import ExampleDeterministicId, ExampleRandomId
from app.schemas.typings.integers import ExampleInt
from app.schemas.typings.prefixed_id import (
    ExampleDeterministicPrefixedId,
    ExampleRandomPrefixedId,
)
from app.schemas.typings.strings import ExampleString

EXAMPLE_SCHEMA_FILE_PATHS: tuple[str, ...] = (
    "app/schemas/configurations/example_config.py",
    "app/schemas/dto/example_dto.py",
    "app/schemas/domain/example_document.py",
    "app/schemas/typings/booleans.py",
    "app/schemas/typings/constrained_floats.py",
    "app/schemas/typings/constrained_integers.py",
    "app/schemas/typings/constrained_strings.py",
    "app/schemas/typings/floats.py",
    "app/schemas/typings/ids.py",
    "app/schemas/typings/integers.py",
    "app/schemas/typings/prefixed_id.py",
    "app/schemas/typings/strings.py",
)


def test_example_schema_files_are_kept() -> None:
    project_root_path: Path = Path(__file__).resolve().parents[2]
    missing_file_paths: list[str] = []

    for relative_file_path in EXAMPLE_SCHEMA_FILE_PATHS:
        example_file_path: Path = project_root_path / relative_file_path
        if example_file_path.is_file():
            continue

        missing_file_paths.append(relative_file_path)

    assert missing_file_paths == [], (
        "Example schema files must not be deleted. They document supported "
        f"DTO, document, and typing patterns. Missing files: {missing_file_paths}"
    )


def test_example_dto_classes_are_kept() -> None:
    assert issubclass(ExampleMutableDTO, MutableDTO)
    assert issubclass(ExampleImmutableDTO, ImmutableDTO)
    assert issubclass(ExampleArbitraryMutableDTO, ArbitraryMutableDTO)
    assert issubclass(ExampleArbitraryImmutableDTO, ArbitraryImmutableDTO)

    assert_class_docstring_is_kept(ExampleMutableDTO)
    assert_class_docstring_is_kept(ExampleImmutableDTO)
    assert_class_docstring_is_kept(ExampleArbitraryMutableDTO)
    assert_class_docstring_is_kept(ExampleArbitraryImmutableDTO)


def test_example_config_class_is_kept() -> None:
    assert issubclass(ExampleConfig, ImmutableDTO)
    assert_class_docstring_is_kept(ExampleConfig)


def test_example_document_classes_are_kept() -> None:
    assert issubclass(ExampleDocument, BaseDocument)
    assert issubclass(ExamplePersistentDocument, PersistentDocument)
    assert issubclass(ExampleMicrosecondTimestampedDocument, PersistentDocument)
    assert issubclass(
        ExampleMicrosecondTimestampedDocument,
        UnixMicrosecondTimestampedMixin,
    )
    assert issubclass(ExampleMicrosecondTimestampedDocument, VersionedMixin)
    assert issubclass(ExampleMillisecondTimestampedDocument, PersistentDocument)
    assert issubclass(
        ExampleMillisecondTimestampedDocument,
        UnixMillisecondTimestampedMixin,
    )
    assert issubclass(ExampleMillisecondTimestampedDocument, VersionedMixin)
    assert issubclass(ExampleNanosecondTimestampedDocument, PersistentDocument)
    assert issubclass(
        ExampleNanosecondTimestampedDocument,
        UnixNanosecondTimestampedMixin,
    )
    assert issubclass(ExampleNanosecondTimestampedDocument, VersionedMixin)

    assert_class_docstring_is_kept(ExampleDocument)
    assert_class_docstring_is_kept(ExamplePersistentDocument)
    assert_class_docstring_is_kept(ExampleMicrosecondTimestampedDocument)
    assert_class_docstring_is_kept(ExampleMillisecondTimestampedDocument)
    assert_class_docstring_is_kept(ExampleNanosecondTimestampedDocument)


def test_example_typing_classes_and_aliases_are_kept() -> None:
    assert issubclass(ExampleDeterministicId, BaseTypedId)
    assert ExampleDeterministicId.uuid_version == 5
    assert issubclass(ExampleRandomId, BaseTypedId)
    assert issubclass(ExampleDeterministicPrefixedId, BasePrefixedTypedId)
    assert ExampleDeterministicPrefixedId.prefix == "example"
    assert ExampleDeterministicPrefixedId.uuid_version == 5
    assert issubclass(ExampleRandomPrefixedId, BasePrefixedTypedId)
    assert ExampleRandomPrefixedId.prefix == "example"
    assert issubclass(ExampleConstrainedFloat, BaseConstrainedTypedFloat)
    assert issubclass(ExampleConstrainedInt, BaseConstrainedTypedInt)
    assert issubclass(ExampleConstrainedString, BaseConstrainedTypedString)
    assert issubclass(ExampleInt, BaseTypedInt)
    assert issubclass(ExampleString, BaseTypedString)
    assert boolean_typings.ExampleBoolean is bool
    assert issubclass(ExampleFloat, BaseTypedFloat)

    assert_class_docstring_is_kept(ExampleDeterministicId)
    assert_class_docstring_is_kept(ExampleRandomId)
    assert_class_docstring_is_kept(ExampleDeterministicPrefixedId)
    assert_class_docstring_is_kept(ExampleRandomPrefixedId)
    assert_class_docstring_is_kept(ExampleConstrainedFloat)
    assert_class_docstring_is_kept(ExampleConstrainedInt)
    assert_class_docstring_is_kept(ExampleConstrainedString)
    assert_class_docstring_is_kept(ExampleInt)
    assert_class_docstring_is_kept(ExampleString)
    assert_module_docstring_mentions(boolean_typings, "ExampleBoolean")


def assert_class_docstring_is_kept(example_class: type[object]) -> None:
    docstring: str | None = inspect.getdoc(example_class)
    assert docstring is not None and docstring.strip() != "", (
        f"{example_class.__name__} must keep a docstring that explains the "
        "example pattern."
    )


def assert_module_docstring_mentions(
    example_module: ModuleType,
    expected_text: str,
) -> None:
    docstring: str | None = inspect.getdoc(example_module)
    assert docstring is not None and expected_text in docstring, (
        f"{example_module.__name__} must keep a module docstring mentioning "
        f"{expected_text}."
    )
