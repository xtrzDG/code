"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class ActivationEventId(BasePrefixedTypedId):
    """
    Identifier of one activation milestone of a business.

    Derived (UUID v5) from the business and the milestone kind, so a
    milestone is stored once however often it is noticed.
    """

    prefix = "activation_event"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class AssistantApplyId(BasePrefixedTypedId):
    """
    Identifier of the "Apply changes" record of a business.

    Derived (UUID v5) from the business: a business has one current apply,
    which every new apply replaces.
    """

    prefix = "assistant_apply"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class SetupStateId(BasePrefixedTypedId):
    """
    Identifier of the setup state of a business (the steps it skipped).

    Derived (UUID v5) from the business: one state per business.
    """

    prefix = "setup_state"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
