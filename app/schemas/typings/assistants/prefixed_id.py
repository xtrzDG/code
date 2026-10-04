"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


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
