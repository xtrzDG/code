"""Keep abc order."""

from base_typed_string import BaseTypedString


class KnowledgeAttributeValue(BaseTypedString):
    """Value of a structured knowledge attribute."""


class KnowledgeBody(BaseTypedString):
    """Body of a knowledge item: answer, description, or policy text."""


class KnowledgeSearchQuery(BaseTypedString):
    """Free-text query the language model searches the knowledge base with."""


class KnowledgeTitle(BaseTypedString):
    """Title of a knowledge item: question, dish, service, room type."""


class SeasonName(BaseTypedString):
    """Owner's name of a season of nightly rates ("High season", "Новый год")."""


class ServiceReference(BaseTypedString):
    """
    How the language model names a bookable service: its id from the facts
    or a tool result, or its name as the customer wrote it, in any script.
    """


# Keep abc order for all non example types, if possible.
