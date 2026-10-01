from enum import StrEnum


class KnowledgeItemKind(StrEnum):
    """Kind of a knowledge item, as in the concept's knowledge_items table."""

    FAQ = "faq"
    POLICY = "policy"
    MENU_ITEM = "menu_item"
    SERVICE = "service"
    ROOM_TYPE = "room_type"
    PACKAGE = "package"
    VEHICLE = "vehicle"
    PRODUCT = "product"


class KnowledgeItemSource(StrEnum):
    """Where a knowledge item came from."""

    PROFILE = "profile"
    OWNER = "owner"
    UNANSWERED_QUESTION = "unanswered_question"
    MENU_IMPORT = "menu_import"
