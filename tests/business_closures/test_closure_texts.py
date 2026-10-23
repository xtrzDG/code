"""The owners' notices and the deletion certificate's page."""

from typed_time_provider import Microseconds

from app.schemas.constants.business_closures import (
    ClosureNoticeKind,
    DeprovisionOutcome,
    DeprovisionTarget,
)
from app.schemas.domain.business_closures import (
    BusinessDeletionDocument,
    DeprovisionRecord,
)
from app.schemas.dto.business_closures.closure_notices import ClosureNotice
from app.schemas.dto.business_closures.deletion_certificates import (
    DeletionCertificateSource,
)
from app.schemas.typings.business_closures.constrained_integers import (
    DeprovisionedItemCount,
)
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.schemas.typings.users.strings import UserDisplayName
from app.transformers.business_closures.closure_notice_transformer import (
    ClosureNoticeTransformer,
)
from app.transformers.business_closures.deletion_certificate_html_transformer import (
    DeletionCertificateHtmlTransformer,
)
from app.transformers.business_closures.deletion_certificate_page import (
    DeletionCertificatePage,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.storage.document_evolution.sample_documents import sample_document

# 2026-11-04T08:00:00Z: 12:00 on 4 November in Tbilisi.
DELETE_AFTER: Microseconds = Microseconds(1_793_779_200_000_000)


def notice(kind: ClosureNoticeKind, language: str) -> str:
    return str(
        ClosureNoticeTransformer(LocalizedTextResolver()).transform(
            ClosureNotice(
                kind=kind,
                business_name=BusinessName("Mtsvane Ezo"),
                actor_name=UserDisplayName("Nino"),
                delete_after=DELETE_AFTER,
                timezone=TimezoneName("Asia/Tbilisi"),
                language=LanguageTag(language),
            )
        )
    )


def entry(name: str) -> BusinessDeletionDocument:
    return sample_document(
        BusinessDeletionDocument, DocumentCollectionName("business_deletions")
    ).model_copy(
        update={
            "business_name": BusinessName(name),
            "deprovisioned": [
                DeprovisionRecord(
                    target=DeprovisionTarget.PHONE_NUMBER,
                    outcome=DeprovisionOutcome.DONE,
                    item_count=DeprovisionedItemCount(1),
                ),
                DeprovisionRecord(
                    target=DeprovisionTarget.TELEGRAM_WEBHOOK,
                    outcome=DeprovisionOutcome.SKIPPED,
                ),
            ],
        }
    )


def test_the_notice_names_who_closed_and_the_local_deletion_day() -> None:
    english = notice(ClosureNoticeKind.OPENED_BY_OWNER, "en")
    russian = notice(ClosureNoticeKind.OPENED_BY_OWNER, "ru")

    assert english.startswith("Nino closed Mtsvane Ezo.")
    assert "November 4, 2026" in english
    assert "4 ноября 2026" in russian


def test_a_language_the_catalog_lacks_reads_english() -> None:
    assert notice(ClosureNoticeKind.REOPENED_PAID, "pt").startswith(
        "Mtsvane Ezo is open again"
    )


def test_the_certificate_escapes_what_owners_typed() -> None:
    html = str(
        DeletionCertificateHtmlTransformer(LocalizedTextResolver()).transform(
            DeletionCertificateSource(
                entry=entry("<script>Cafe</script>"), language=LanguageTag("en")
            )
        )
    )

    assert "<script>Cafe" not in html
    assert "&lt;script&gt;Cafe&lt;/script&gt;" in html
    assert "Rented phone numbers" in html
    assert "switched off: 1" in html
    assert "provider unreachable" in html
    assert 'dir="ltr"' in html


def test_a_right_to_left_language_turns_the_page() -> None:
    page = DeletionCertificatePage(
        LocalizedTextResolver(),
        DeletionCertificateSource(entry=entry("Cafe"), language=LanguageTag("en")),
    )
    page.language = LanguageTag("he")

    assert page.direction == "rtl"
