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


class SeasonDay(BaseConstrainedTypedString):
    """
    Month and day a season starts or ends, "MM-DD", every year ("06-15";
    "02-29" counts in leap years only).

    Example:
        first_day = SeasonDay("06-15")
    """

    min_length = 5
    max_length = 5
    pattern = (
        r"^(?:(?:0[13578]|1[02])-(?:0[1-9]|[12][0-9]|3[01])"
        r"|(?:0[469]|11)-(?:0[1-9]|[12][0-9]|30)"
        r"|02-(?:0[1-9]|1[0-9]|2[0-9]))$"
    )


# Keep abc order for all non example types, if possible.
