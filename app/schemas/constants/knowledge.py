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


class KnowledgeAliasStatus(StrEnum):
    """
    Whether the owner has reviewed an alias of a knowledge item: SUGGESTED
    by the model (searched, but never offered to visitors as a starter
    question) or APPROVED by the owner (typed by them, or a suggestion
    they accepted in the editor).
    """

    SUGGESTED = "suggested"
    APPROVED = "approved"


class AnswerCorrectionScope(StrEnum):
    """
    What an owner's correction of an assistant answer teaches: a question
    and its answer (FAQ), the price of an offer, the opening hours (a
    policy line next to the profile's hours) or a rule (policy).
    """

    FAQ = "faq"
    PRICE = "price"
    HOURS = "hours"
    RULE = "rule"
