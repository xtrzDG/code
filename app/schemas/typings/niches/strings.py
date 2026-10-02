"""Keep abc order."""

from base_typed_string import BaseTypedString


class ExampleAssistantLine(BaseTypedString):
    """
    What the assistant says (and which tool it calls, in brackets) in an
    example exchange of a niche template; English, for the model.
    """


class ExampleCustomerLine(BaseTypedString):
    """What the customer says in an example exchange of a niche template."""


class IntegrationName(BaseTypedString):
    """External system a niche may integrate with, e.g. "Google Calendar"."""


# Keep abc order for all non example types, if possible.
