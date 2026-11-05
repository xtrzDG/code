"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class CircuitName(BaseConstrainedTypedString):
    """
    What one circuit breaker guards: a provider and its model,
    e.g. "openai:gpt-5-mini".

    Example:
        circuit = CircuitName("anthropic:claude-sonnet-5-5")
    """

    min_length = 3
    max_length = 160
    pattern = r"^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._:@\-]*$"


# Keep abc order for all non example types, if possible.
