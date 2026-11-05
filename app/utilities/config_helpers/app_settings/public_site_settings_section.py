"""
PUBLIC_DEMO_BUSINESS_IDS, PUBLIC_DEMO_MESSAGES_PER_HOUR and
LEGAL_TEXTS_FINAL: the landing page's sandbox demos and the legal pages.
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.public_site_settings import (
    DEFAULT_PUBLIC_DEMO_MESSAGES_PER_HOUR,
    PublicSiteSettings,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.public_site.constrained_integers import (
    PublicDemoMessagesPerHour,
)
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    parse_setting,
    read_boolean,
    read_integer,
    read_raw_list,
)


class PublicSiteSettingsSection(TypedDict):
    """The `AppSettings` field of the public site."""

    public_site: PublicSiteSettings


def read_public_site_settings(
    environment_variables: Mapping[str, str],
) -> PublicSiteSettingsSection:
    """
    Raises:
        ValidationFailedError: a demo business id is malformed or named
            twice, or the hourly demo budget is out of range.
    """

    demo_business_ids: list[BusinessId] = [
        parse_business_id(raw_id)
        for raw_id in read_raw_list(environment_variables, "PUBLIC_DEMO_BUSINESS_IDS")
    ]
    if len(set(demo_business_ids)) != len(demo_business_ids):
        raise ValidationFailedError("PUBLIC_DEMO_BUSINESS_IDS names a business twice.")

    return PublicSiteSettingsSection(
        public_site=PublicSiteSettings(
            demo_business_ids=demo_business_ids,
            demo_messages_per_hour=parse_setting(
                "PUBLIC_DEMO_MESSAGES_PER_HOUR",
                read_integer(
                    environment_variables,
                    "PUBLIC_DEMO_MESSAGES_PER_HOUR",
                    DEFAULT_PUBLIC_DEMO_MESSAGES_PER_HOUR,
                ),
                PublicDemoMessagesPerHour,
            ),
            are_legal_texts_final=read_boolean(
                environment_variables, "LEGAL_TEXTS_FINAL", False
            ),
        )
    )


def parse_business_id(raw_id: str) -> BusinessId:
    try:
        return BusinessId(raw_id)
    except (TypeError, ValueError) as error:
        raise ValidationFailedError(
            "PUBLIC_DEMO_BUSINESS_IDS has an invalid business id."
        ) from error
