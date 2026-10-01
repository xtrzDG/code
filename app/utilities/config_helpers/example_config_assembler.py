from app.schemas.configurations.example_config import ExampleConfig
from app.schemas.typings.booleans import ExampleBoolean
from app.schemas.typings.strings import ExampleString


def get_example_config() -> ExampleConfig:
    """Assemble the validated example configuration cached by the container."""

    return ExampleConfig(
        is_enabled=ExampleBoolean(True),
        name=ExampleString("example"),
    )
