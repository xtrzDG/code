"""An owner's report fanned out to Telegram and WhatsApp, once, through the outbox."""

import json

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.value.owner_digest_facilitator import OwnerDigestFacilitator
from app.repositories.value_repositories import DigestPreferencesRepository
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.value import DigestChannel, ValueReportKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.value_settings import DigestPreferencesDocument
from app.schemas.dto.value.value_reports import ValueReportView
from app.schemas.typings.handoffs.strings import ManagerContactAddress
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.value.constrained_strings import ValueReportPeriodKey
from app.transformers.notifications.value_digest_text_transformer import (
    ValueDigestTextTransformer,
)
from app.utilities.notifications.staff_link_signer import StaffLinkSigner
from app.utilities.value.value_keys import digest_preferences_id_of, value_report_id_of
from tests.channels.channels_payloads import telegram_ok
from tests.channels.channels_settings import PLATFORM_BOT_TOKEN, build_settings
from tests.channels.testbed import ChannelsTestbed
from tests.notifications.staff_alert_fakes import (
    TEST_ENCRYPTION_KEY,
    RecordingPushQueue,
    preferences_repo,
)
from tests.operations.builders import manager
from tests.operations.fakes import FakeLocalizedTextResolver

CHAT: str = "-100777"
OWNER_NUMBER: str = "+995555123456"
TOTALS: dict[str, int] = {
    "conversation_count": 40,
    "after_hours_conversation_count": 12,
    "customer_message_count": 160,
    "assistant_reply_count": 150,
    "call_count": 6,
    "booking_count": 22,
    "assistant_booking_count": 20,
    "request_count": 3,
    "handoff_count": 2,
    "staff_minutes_saved": 205,
    "estimated_revenue_minor": 240_000,
}


def monthly_report(business: BusinessDocument) -> ValueReportView:
    report_id = value_report_id_of(
        business.id, ValueReportKind.MONTHLY, ValueReportPeriodKey("2026-09")
    )
    return ValueReportView.model_validate_json(
        json.dumps(
            {
                "id": str(report_id),
                "business_id": str(business.id),
                "kind": "monthly",
                "period_key": "2026-09",
                "date_from": "2026-09-01",
                "date_to": "2026-09-30",
                "previous_date_from": "2026-08-01",
                "previous_date_to": "2026-08-31",
                "currency_code": "GEL",
                "value_basis": "bookings",
                "average_check_minor": 12_000,
                "average_check_source": "owner",
                "current": TOTALS,
                "previous": TOTALS,
                "plan_cost_minor": 29_300,
                "return_multiple": 8.2,
                "delivery": "sent",
                "recipient_count": 0,
                "created_at": 1,
            }
        )
    )


def digest_setup(
    testbed: ChannelsTestbed,
) -> tuple[OwnerDigestFacilitator, BusinessDocument, DigestPreferencesRepository]:
    owner_id: UserId = testbed.add_user("owner-token", "ru")
    business = testbed.add_business(owner_id, name="Cafe Batumi")
    business.manager_contacts.append(
        manager("Owner chat", ManagerContactChannel.TELEGRAM, CHAT, "ru")
    )
    testbed.business_repo.save(business)
    choices = DigestPreferencesRepository(
        InMemoryDocumentCollectionAdapter[DigestPreferencesDocument](
            DigestPreferencesDocument
        )
    )
    choices.save(
        DigestPreferencesDocument(
            id=digest_preferences_id_of(business.id, owner_id),
            business_id=business.id,
            user_id=owner_id,
            channels=[DigestChannel.TELEGRAM, DigestChannel.WHATSAPP],
            telegram_chat=ManagerContactAddress(CHAT),
            whatsapp_number=E164PhoneNumber(OWNER_NUMBER),
        )
    )
    facilitator = OwnerDigestFacilitator(
        user_repo=testbed.user_repo,
        digest_preferences_repo=choices,
        push_subscription_repo=testbed.push_subscription_repo,
        notification_preferences_repo=preferences_repo(),
        manager_notifier=testbed.staff_notifier,
        push_queue=RecordingPushQueue(),
        link_signer=StaffLinkSigner(TEST_ENCRYPTION_KEY),
        text_transformer=ValueDigestTextTransformer(FakeLocalizedTextResolver()),
        app_settings=testbed.settings,
        wall_clock=testbed.wall_clock,
    )
    return facilitator, business, choices


def test_telegram_and_whatsapp_get_the_report_once_each() -> None:
    testbed = ChannelsTestbed(
        build_settings(
            WHATSAPP_OWNER_REPORT_TEMPLATE="owner_report",
            CABINET_BASE_URL="https://cabinet.example.com",
        )
    )
    testbed.telegram_transport.respond(
        "POST", r"/sendMessage$", telegram_ok({"message_id": 7})
    )
    testbed.meta_transport.respond(
        "POST", r"/messages$", {"messages": [{"id": "wamid.1"}]}
    )
    facilitator, business, _ = digest_setup(testbed)
    report = monthly_report(business)

    first = facilitator.send(business, report)
    again = facilitator.send(business, report)
    testbed.run_worker()

    assert (first, again) == (2, 2)
    [telegram] = testbed.telegram_transport.requests
    assert telegram.path == f"/bot{PLATFORM_BOT_TOKEN}/sendMessage"
    assert telegram.json()["chat_id"] == CHAT
    assert "8,2×" in telegram.json()["text"]
    [whatsapp] = testbed.meta_transport.requests
    body = whatsapp.json()
    assert body["to"] == OWNER_NUMBER.lstrip("+")
    assert body["template"]["name"] == "owner_report"
    assert body["template"]["language"] == {"code": "ru"}
    business_name, summary, link = body["template"]["components"][0]["parameters"]
    assert business_name == {"type": "text", "text": "Cafe Batumi"}
    assert "≈ 8,2× тарифа" in summary["text"] and "\n" not in summary["text"]
    assert link["text"].startswith("https://cabinet.example.com/n/")


def test_a_chat_no_longer_linked_and_a_missing_template_get_nothing() -> None:
    testbed = ChannelsTestbed(build_settings())
    facilitator, business, _ = digest_setup(testbed)
    business.manager_contacts.clear()
    testbed.business_repo.save(business)

    sent = facilitator.send(business, monthly_report(business))
    testbed.run_worker()

    assert sent == 0
    assert testbed.telegram_transport.requests == []
    assert testbed.meta_transport.requests == []
