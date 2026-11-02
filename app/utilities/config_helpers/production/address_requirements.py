"""
Production's public addresses: the API's and the cabinet's own, the
cabinet's origins (CORS) and every provider endpoint are https and never
this machine (localhost serves development only).
"""

import ipaddress
from urllib.parse import urlsplit

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.platform.strings import ProductionSettingProblem

# Names of this machine (loopback and unspecified IP addresses count too).
LOCAL_HOST_NAME: str = "localhost"
LOCAL_HOST_SUFFIX: str = ".localhost"
HTTPS_SCHEME: str = "https"


def find_address_problems(settings: AppSettings) -> list[ProductionSettingProblem]:
    problems: list[ProductionSettingProblem] = [
        ProductionSettingProblem(f"{name} is not set: {why}.")
        for name, value, why in (
            (
                "APP_BASE_URL",
                settings.app_base_url,
                "webhooks, the widget and the hosted pages need the API's "
                "public https address",
            ),
            (
                "CABINET_BASE_URL",
                settings.cabinet_base_url,
                "e-mails, payments and calendar consent send owners back to "
                "the cabinet's public https address",
            ),
        )
        if value is None
    ]
    if not settings.cors_allowed_origins:
        problems.append(
            ProductionSettingProblem(
                "CORS_ALLOWED_ORIGINS is not set: list the cabinet's https "
                "origin (https://app.example.com)."
            )
        )

    for name, value in public_addresses(settings):
        problem: ProductionSettingProblem | None = address_problem(name, value)
        if problem is not None:
            problems.append(problem)

    return problems


def public_addresses(settings: AppSettings) -> list[tuple[str, str]]:
    """`(variable, address)` of every address production calls or names."""

    addresses: list[tuple[str, PublicBaseUrl | CabinetBaseUrl | None]] = [
        ("APP_BASE_URL", settings.app_base_url),
        ("CABINET_BASE_URL", settings.cabinet_base_url),
        *(("CORS_ALLOWED_ORIGINS", origin) for origin in settings.cors_allowed_origins),
        ("OPENAI_BASE_URL", settings.openai_base_url),
        ("ELEVENLABS_API_BASE_URL", settings.elevenlabs_api_base_url),
        ("LANGFUSE_HOST", settings.langfuse_host),
        ("OTEL_EXPORTER_OTLP_ENDPOINT", settings.telemetry.otlp_endpoint),
        (
            "RECORDINGS_S3_ENDPOINT_URL",
            None
            if settings.recordings_object_storage is None
            else settings.recordings_object_storage.endpoint_url,
        ),
        (
            "BACKUP_S3_ENDPOINT_URL",
            None
            if settings.backup.bucket is None
            else settings.backup.bucket.endpoint_url,
        ),
    ]
    return [(name, str(value)) for name, value in addresses if value is not None]


def address_problem(name: str, address: str) -> ProductionSettingProblem | None:
    """Why an address cannot serve production; None when it can."""

    parts = urlsplit(address)
    host: str = (parts.hostname or "").lower()
    if parts.scheme.lower() != HTTPS_SCHEME:
        return ProductionSettingProblem(
            f"{name} must be an https address in production, got {address}."
        )

    if is_this_machine(host):
        return ProductionSettingProblem(
            f"{name} points at this machine ({address}); localhost serves "
            "development only."
        )

    return None


def is_this_machine(host: str) -> bool:
    """localhost, a name under .localhost, or a loopback or unspecified IP."""

    if host == LOCAL_HOST_NAME or host.endswith(LOCAL_HOST_SUFFIX):
        return True

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False

    return address.is_loopback or address.is_unspecified
