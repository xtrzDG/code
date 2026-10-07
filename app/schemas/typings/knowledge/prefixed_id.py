"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class KnowledgeItemId(BasePrefixedTypedId):
    """Random identifier of a knowledge item."""

    prefix = "knowledge_item"


# Keep abc order for all non example types, if possible.
