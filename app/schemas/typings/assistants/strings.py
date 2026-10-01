"""Keep abc order."""

from base_typed_string import BaseTypedString


class AutotestFinding(BaseTypedString):
    """One reason the judge gave for passing or failing a scenario."""


class AutotestScenarioGoal(BaseTypedString):
    """Instruction for the AI customer: what it must try to achieve."""


class GapDescription(BaseTypedString):
    """One item of the owner's "what to add" list."""


class LlmToolDescription(BaseTypedString):
    """Description of a tool shown to the language model."""


class LlmToolInputSchemaJson(BaseTypedString):
    """JSON Schema of a tool input, serialized as a JSON object."""


class PromptRuleText(BaseTypedString):
    """One behavioural rule of the assistant written for the language model."""


class SystemPromptText(BaseTypedString):
    """Frozen system prompt of an assistant version."""


# Keep abc order for all non example types, if possible.
