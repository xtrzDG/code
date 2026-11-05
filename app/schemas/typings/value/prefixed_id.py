"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class DigestPreferencesId(BasePrefixedTypedId):
    """
    Identifier of one owner's digest choices in one business.

    Derived (UUID v5) from the business and the user, so each owner of a
    business has one preferences document.
    """

    prefix = "digest_preferences"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class ValueReportId(BasePrefixedTypedId):
    """
    Identifier of one stored value report (a daily or weekly digest, or a
    monthly report) of a business.

    Derived (UUID v5) from the business, the kind and the period it
    summarizes, so a period is reported once however often the job runs.
    """

    prefix = "value_report"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class ValueSettingsId(BasePrefixedTypedId):
    """
    Identifier of the value settings (the average check) of one business.

    Derived (UUID v5) from the business, so a business has one settings
    document.
    """

    prefix = "value_settings"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
