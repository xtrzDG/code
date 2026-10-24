"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class AssistantSettingsId(BasePrefixedTypedId):
    """
    Identifier of how the assistant of one business treats its customers
    (Settings → General: remembering returning customers).

    Derived (UUID v5) from the business: one settings document per business.
    """

    prefix = "assistant_settings"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class AssistantVersionId(BasePrefixedTypedId):
    """Random identifier of one assembled assistant version."""

    prefix = "assistant_version"


class AutotestCaseId(BasePrefixedTypedId):
    """Random identifier of one owner check (a permanent autotest case)."""

    prefix = "autotest_case"


class AutotestRunId(BasePrefixedTypedId):
    """Random identifier of one autotest run over an assistant version."""

    prefix = "autotest_run"


# Keep abc order for all non example types, if possible.
