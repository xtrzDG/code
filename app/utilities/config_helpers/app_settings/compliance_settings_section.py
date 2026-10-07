"""Restricted countries, data region, retention, message limits and the DPA."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.constants.localization import DataRegion
from app.schemas.typings.businesses.constrained_integers import (
    RecordingRetentionDays,
)
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.conversations.constrained_integers import (
    ContactMessageLimit,
)
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    read_integer,
    read_list,
    read_text,
)

# Comprehensively sanctioned jurisdictions for a US-person founder. Confirm the
# list with a lawyer before launch; override with RESTRICTED_COUNTRY_CODES
# (comma-separated, an empty value disables the restriction).
DEFAULT_RESTRICTED_COUNTRY_CODES: str = "CU,IR,KP,SY"
DEFAULT_DPA_DOCUMENT_VERSION: str = "2026-10-06"


class ComplianceSettingsSection(TypedDict):
    """The `AppSettings` fields of legal and data protection limits."""

    restricted_country_codes: list[CountryCode]
    default_data_region: DataRegion
    default_recording_retention_days: RecordingRetentionDays
    contact_message_limit_per_hour: ContactMessageLimit
    dpa_document_version: DpaDocumentVersion


def read_compliance_settings(
    environment_variables: Mapping[str, str],
) -> ComplianceSettingsSection:
    return ComplianceSettingsSection(
        restricted_country_codes=[
            CountryCode(country_code)
            for country_code in read_list(
                environment_variables,
                "RESTRICTED_COUNTRY_CODES",
                DEFAULT_RESTRICTED_COUNTRY_CODES,
            )
        ],
        default_data_region=DataRegion(
            read_text(environment_variables, "DEFAULT_DATA_REGION", DataRegion.EU)
        ),
        default_recording_retention_days=RecordingRetentionDays(
            read_integer(environment_variables, "RECORDING_RETENTION_DAYS", 90)
        ),
        contact_message_limit_per_hour=ContactMessageLimit(
            read_integer(environment_variables, "CONTACT_MESSAGE_LIMIT_PER_HOUR", 60)
        ),
        dpa_document_version=DpaDocumentVersion(
            read_text(
                environment_variables,
                "DPA_DOCUMENT_VERSION",
                DEFAULT_DPA_DOCUMENT_VERSION,
            )
        ),
    )
