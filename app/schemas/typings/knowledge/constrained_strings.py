"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class KnowledgeAttributeKey(BaseConstrainedTypedString):
    """Snake-case key of a structured knowledge attribute ("season", "floor")."""

    min_length = 1
    max_length = 64
    pattern = r"^[a-z][a-z0-9_]*$"


class KnowledgeTag(BaseConstrainedTypedString):
    """
    Lower-case tag of a knowledge item ("vegetarian", "kids", "gluten-free").

    Example:
        tag = KnowledgeTag("vegetarian")
    """

    min_length = 1
    max_length = 48
    pattern = r"^[a-z0-9][a-z0-9_\-]*$"


# Keep abc order for all non example types, if possible.
