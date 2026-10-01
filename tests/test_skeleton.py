from io import StringIO
from uuid import NAMESPACE_URL, uuid5

from base_typed_id import deterministically_from_words
from typed_time_provider import MonotonicClock, Nanoseconds, WallClock

from app.containers.app import AppContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases import UseCasesContainer
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
from app.schemas.typings.booleans import ExampleBoolean
from app.schemas.typings.floats import ExampleFloat
from app.schemas.typings.ids import ExampleDeterministicId, ExampleRandomId
from app.schemas.typings.integers import ExampleInt
from app.schemas.typings.prefixed_id import (
    ExampleDeterministicPrefixedId,
    ExampleRandomPrefixedId,
)
from app.schemas.typings.strings import ExampleString
from app.use_cases.example_use_case import ExampleUseCase


def test_app_container_can_be_created() -> None:
    app_container: AppContainer = AppContainer()
    app_container.check_dependencies()


def test_config_container_builds_example_config_as_singleton() -> None:
    config_container: ConfigContainer = ConfigContainer()

    first_example_config: ExampleConfig = config_container.example_config()
    second_example_config: ExampleConfig = config_container.example_config()

    assert first_example_config is second_example_config
    assert first_example_config.is_enabled is True
    assert first_example_config.name == ExampleString("example")


def test_time_provider_container_builds_default_clocks() -> None:
    time_provider_container = TimeProviderContainer()
    monotonic_clock: MonotonicClock[Nanoseconds] = (
        time_provider_container.monotonic_clock()
    )
    wall_clock: WallClock[Nanoseconds] = time_provider_container.wall_clock()

    assert monotonic_clock.preferred_time_unit_type is Nanoseconds
    assert wall_clock.preferred_time_unit_type is Nanoseconds


def test_use_cases_container_builds_example_use_case() -> None:
    use_cases_container: UseCasesContainer = UseCasesContainer()
    example_use_case: ExampleUseCase = use_cases_container.example_use_case()
    input_data = create_example_mutable_dto()
    output = example_use_case.run(input_data)

    assert output.count == ExampleInt(1)
    assert output.deterministic_id == input_data.deterministic_id
    assert output.deterministic_prefixed_id == input_data.deterministic_prefixed_id
    assert output.is_enabled is True
    assert output.name == ExampleString("example")
    assert output.random_id == input_data.random_id
    assert output.random_prefixed_id == input_data.random_prefixed_id
    assert output.ratio == ExampleFloat(0.75)


def test_example_arbitrary_dtos_accept_runtime_objects() -> None:
    input_data = create_example_mutable_dto()
    output = ExampleImmutableDTO(**input_data.model_dump())
    published_outputs: list[ExampleImmutableDTO] = []

    def publish_output(output_data: ExampleImmutableDTO) -> None:
        published_outputs.append(output_data)

    mutable_runtime_dto = ExampleArbitraryMutableDTO(
        mutable_input=input_data,
        output_buffer=StringIO(),
        publish_output=publish_output,
    )
    immutable_runtime_dto = ExampleArbitraryImmutableDTO(
        immutable_output=output,
        output_buffer=StringIO(),
        publish_output=publish_output,
    )

    mutable_runtime_dto.publish_output(output)
    immutable_runtime_dto.publish_output(output)

    assert mutable_runtime_dto.mutable_input == input_data
    assert immutable_runtime_dto.immutable_output == output
    assert published_outputs == [output, output]


def test_example_documents_show_persistence_base_classes() -> None:
    random_id = ExampleRandomId()
    document = ExampleDocument(
        count=ExampleInt(1),
        deterministic_id=deterministically_from_words(
            ExampleDeterministicId,
            words=[
                "source:example",
                "record:42",
            ],
        ),
        deterministic_prefixed_id=ExampleDeterministicPrefixedId(
            uuid5(NAMESPACE_URL, "source:example/record:42"),
        ),
        is_enabled=ExampleBoolean(True),
        name=ExampleString("example"),
        random_id=random_id,
        random_prefixed_id=ExampleRandomPrefixedId(),
        ratio=ExampleFloat(0.75),
    )
    persistent_document = ExamplePersistentDocument(
        count=ExampleInt(1),
        name=ExampleString("example"),
        random_id=random_id,
    )
    microsecond_document = ExampleMicrosecondTimestampedDocument(
        count=ExampleInt(1),
        name=ExampleString("example"),
        random_id=random_id,
    )
    millisecond_document = ExampleMillisecondTimestampedDocument(
        count=ExampleInt(1),
        name=ExampleString("example"),
        random_id=random_id,
    )
    nanosecond_document = ExampleNanosecondTimestampedDocument(
        count=ExampleInt(1),
        name=ExampleString("example"),
        random_id=random_id,
    )

    assert document.schema_version == "1"
    assert persistent_document.random_id == random_id
    assert microsecond_document.schema_version == "1"
    assert millisecond_document.schema_version == "1"
    assert nanosecond_document.schema_version == "1"
    assert microsecond_document.created_at > millisecond_document.created_at
    assert nanosecond_document.created_at > microsecond_document.created_at


def create_example_mutable_dto() -> ExampleMutableDTO:
    return ExampleMutableDTO(
        count=ExampleInt(1),
        deterministic_id=deterministically_from_words(
            ExampleDeterministicId,
            words=[
                "source:example",
                "record:42",
            ],
        ),
        deterministic_prefixed_id=ExampleDeterministicPrefixedId(
            uuid5(NAMESPACE_URL, "source:example/record:42"),
        ),
        is_enabled=ExampleBoolean(True),
        name=ExampleString("example"),
        random_id=ExampleRandomId(),
        random_prefixed_id=ExampleRandomPrefixedId(),
        ratio=ExampleFloat(0.75),
    )
