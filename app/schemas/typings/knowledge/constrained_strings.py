"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class EmbeddingModelId(BaseConstrainedTypedString):
    """
    Identifier of a text embedding model ("text-embedding-3-small"); the
    vectors of different models are never compared.
    """

    min_length = 1
    max_length = 100
    pattern = r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$"


class KnowledgeAliasText(BaseConstrainedTypedString):
    """
    A knowledge item's title in another language of the business (or a
    synonym customers use): "Is there parking?" for "Есть ли парковка?".
    Searched like the title; an approved one is a starter question in its
    language.

    Example:
        alias = KnowledgeAliasText("Is there parking?")
    """

    min_length = 1
    max_length = 200
    pattern = r"\S"


class KnowledgeAttributeKey(BaseConstrainedTypedString):
    """Snake-case key of a structured knowledge attribute ("season", "floor")."""

    min_length = 1
    max_length = 64
    pattern = r"^[a-z][a-z0-9_]*$"


class KnowledgeEmbeddingFingerprint(BaseConstrainedTypedString):
    """
    SHA-256 (hex) of the model and the text a knowledge item's embedding was
    computed from: a stored vector whose fingerprint differs is stale.
    """

    min_length = 64
    max_length = 64
    pattern = r"^[0-9a-f]{64}$"


class KnowledgeShareKey(BaseConstrainedTypedString):
    """
    The key that ties a location's knowledge item to a brand's shared one:
    a location item with the brand item's key replaces it in that
    location's assistant ("parking", "delivery-zone").

    Example:
        key = KnowledgeShareKey("parking")
    """

    min_length = 1
    max_length = 64
    pattern = r"^[a-z0-9][a-z0-9_\-]*$"


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
