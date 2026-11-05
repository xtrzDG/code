"""
The texts of the deletion certificate PDF in every language whose texts are
reviewed (other languages read English): a certificate is kept as printed,
so it never carries a draft. Placeholders in braces are filled by the page.
"""

from app.schemas.constants.business_closures import (
    BusinessClosureReason,
    DeprovisionOutcome,
    DeprovisionTarget,
)
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.owner_texts import reviewed_owner_text

TITLE = reviewed_owner_text("closure.certificate.title")
INTRO = reviewed_owner_text("closure.certificate.intro")
BUSINESS = reviewed_owner_text("closure.certificate.business")
BUSINESS_ID = reviewed_owner_text("closure.certificate.business_id")
NUMBER = reviewed_owner_text("closure.certificate.number")
REQUESTED = reviewed_owner_text("closure.certificate.requested")
STARTED = reviewed_owner_text("closure.certificate.started")
COMPLETED = reviewed_owner_text("closure.certificate.completed")
IN_PROGRESS = reviewed_owner_text("closure.certificate.in_progress")
DELETED_HEADING = reviewed_owner_text("closure.certificate.deleted_heading")
DELETED_ROWS = reviewed_owner_text("closure.certificate.deleted_rows")
DELETED_FILES = reviewed_owner_text("closure.certificate.deleted_files")
PROCESSORS = reviewed_owner_text("closure.certificate.processors")
PROVIDERS_HEADING = reviewed_owner_text("closure.certificate.providers_heading")
RETAINED_HEADING = reviewed_owner_text("closure.certificate.retained_heading")
RETAINED_AUDIT = reviewed_owner_text("closure.certificate.retained_audit")
RETAINED_BILLING = reviewed_owner_text("closure.certificate.retained_billing")
BACKUPS = reviewed_owner_text("closure.certificate.backups")
DIGEST = reviewed_owner_text("closure.certificate.digest")
FOOTER = reviewed_owner_text("closure.certificate.footer")

REASONS: dict[BusinessClosureReason, LocalizedText] = {
    BusinessClosureReason.OWNER_REQUEST: reviewed_owner_text(
        "closure.certificate.reason_owner"
    ),
    BusinessClosureReason.UNPAID_SUBSCRIPTION: reviewed_owner_text(
        "closure.certificate.reason_unpaid"
    ),
}
TARGETS: dict[DeprovisionTarget, LocalizedText] = {
    target: reviewed_owner_text(f"closure.certificate.targets.{target.value}")
    for target in DeprovisionTarget
}
OUTCOMES: dict[DeprovisionOutcome, LocalizedText] = {
    outcome: reviewed_owner_text(f"closure.certificate.outcomes.{outcome.value}")
    for outcome in DeprovisionOutcome
}
