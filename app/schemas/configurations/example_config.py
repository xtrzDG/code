from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.booleans import ExampleBoolean
from app.schemas.typings.strings import ExampleString


class ExampleConfig(ImmutableDTO):
    """Validated immutable configuration exposed by the config container."""

    is_enabled: ExampleBoolean
    name: ExampleString
