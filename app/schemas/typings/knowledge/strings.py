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


# Keep abc order for all non example types, if possible.
