"""
What production keeps and how it reports: a database (never in-memory
storage), object storage for recordings and files, JSON logs, a daily spend
budget, an encryption key and the seller its invoices name.
"""

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.configurations.seller_settings import DEFAULT_SELLER_LEGAL_NAME
from app.schemas.constants.observability import LogFormat
from app.schemas.constants.storage import RecordingStorageKind
from app.schemas.typings.platform.strings import ProductionSettingProblem

SELLER_LEGAL_NAME: str = "SELLER_LEGAL_NAME"


def find_platform_problems(settings: AppSettings) -> list[ProductionSettingProblem]:
    problems: list[ProductionSettingProblem] = []
    if settings.database_url is None:
        problems.append(
            ProductionSettingProblem(
                "DATABASE_URL is not set: production never keeps its data in "
                "memory, where a restart loses it and every instance sees "
                "only its own."
            )
        )
    if settings.recording_storage_kind is not RecordingStorageKind.OBJECT_STORAGE:
        problems.append(
            ProductionSettingProblem(
                "RECORDINGS_STORAGE must be s3 in production (with the "
                "RECORDINGS_S3_* variables): recordings, customer files and "
                "export archives would otherwise sit on an instance's disk, "
                "which a deploy wipes."
            )
        )
    if settings.encryption_key is None:
        problems.append(
            ProductionSettingProblem(
                "ENCRYPTION_KEY is not set: channel credentials and the "
                "webhook secrets derived from it need the platform's key."
            )
        )
    if settings.log_format is not LogFormat.JSON:
        problems.append(
            ProductionSettingProblem(
                "LOG_FORMAT must be json in production (leave it unset): log "
                "search and alerts read one JSON object per line."
            )
        )
    if settings.spend_guard.platform_daily_budget_micro_usd is None:
        problems.append(
            ProductionSettingProblem(
                "PLATFORM_DAILY_SPEND_BUDGET_USD must be above 0 in production: "
                "the spend_budget alert warns at 80 % of it."
            )
        )
    problems.extend(find_seller_problems(settings))
    return problems


def find_seller_problems(settings: AppSettings) -> list[ProductionSettingProblem]:
    """Every invoice names its seller: production has no default one."""

    problems: list[ProductionSettingProblem] = [
        ProductionSettingProblem(
            f"{variable_name} is not set: production names the seller on its "
            "invoices itself (docs/LAUNCH.md 4.7.1); the development default "
            "is not a company."
        )
        for variable_name in settings.development_default_variables
    ]
    is_placeholder_name: bool = (
        str(settings.seller.legal_name).strip().casefold()
        == DEFAULT_SELLER_LEGAL_NAME.casefold()
    )
    if is_placeholder_name and SELLER_LEGAL_NAME not in {
        str(variable_name) for variable_name in settings.development_default_variables
    }:
        # Written out (a copied .env.example): still the placeholder.
        problems.append(
            ProductionSettingProblem(
                "SELLER_LEGAL_NAME is the development placeholder "
                f'"{DEFAULT_SELLER_LEGAL_NAME}": name the registered company '
                "with its legal form."
            )
        )
    if settings.seller.address is None:
        problems.append(
            ProductionSettingProblem(
                "SELLER_ADDRESS is not set: every invoice names the seller's "
                "registered address."
            )
        )

    return problems
