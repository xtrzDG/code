"""
A business with a phone assistant line, staff chats and call settings, and
the steps of the call follow-up tests: Zadarma notifications, failed call
starts, the stored missed calls and the staff texts in the outbox.
"""

import base64
import hashlib
import hmac
from typing import Any
from urllib.parse import urlencode

from app.schemas.constants.calls import MissedCallReason, MissedCallSource
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.calls.missed_calls import MissedCallReport
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.utilities.calls.call_follow_up_keys import call_settings_id_of
from tests.channels.channels_settings import ZADARMA_API_SECRET
from tests.channels.outbox_reads import outbox_of
from tests.channels.voice_setup import ASSISTANT_LINE, CALLER, VoiceSetup

WHATSAPP_NUMBER_ID: str = "106540352242922"
TEMPLATE_NAME: str = "missed_call_text_back"
STAFF_CHAT: str = "-100555"


def save_call_settings(
    setup: VoiceSetup,
    is_text_back_enabled: bool = True,
    template_name: str | None = TEMPLATE_NAME,
    is_summary_enabled: bool = True,
    is_sms_fallback_enabled: bool = True,
) -> CallSettingsDocument:
    now = setup.testbed.clock.now_microseconds()
    settings = CallSettingsDocument(
        id=call_settings_id_of(setup.business.id),
        business_id=setup.business.id,
        is_summary_enabled=is_summary_enabled,
        is_text_back_enabled=is_text_back_enabled,
        text_back_template_name=(
            None if template_name is None else WhatsAppTemplateName(template_name)
        ),
        is_sms_fallback_enabled=is_sms_fallback_enabled,
        created_at=now,
        updated_at=now,
    )
    setup.testbed.call_settings_repo.save(settings)
    return settings


def connect_whatsapp(setup: VoiceSetup) -> None:
    """The business's WhatsApp number; Meta accepts every message."""

    setup.testbed.add_channel(
        setup.business.id, ChannelKind.WHATSAPP, WHATSAPP_NUMBER_ID
    )
    setup.testbed.meta_transport.respond(
        "POST", r"/messages$", {"messages": [{"id": "wamid.1"}]}
    )


def add_staff_chat(
    setup: VoiceSetup,
    language: str = "ru",
    channel: ManagerContactChannel = ManagerContactChannel.TELEGRAM,
    address: str = STAFF_CHAT,
) -> None:
    business = setup.testbed.business_repo.get(setup.business.id)
    assert business is not None
    business.manager_contacts.append(
        ManagerContact(
            name=ManagerName("Nino"),
            channel=channel,
            address=ManagerContactAddress(address),
            language=LanguageTag(language),
        )
    )
    setup.testbed.business_repo.save(business)
    setup.business = business


def staff_texts(setup: VoiceSetup) -> list[OutboundMessageDocument]:
    """The staff messages queued for the business, oldest first."""

    return [
        message
        for message in outbox_of(setup.testbed, setup.business.id)
        if message.kind is OutboundMessageKind.STAFF_NOTIFICATION
    ]


def missed_calls(setup: VoiceSetup) -> list[MissedCallDocument]:
    return sorted(
        (
            missed
            for missed in setup.testbed.missed_call_collection.list_all()
            if missed.business_id == setup.business.id
        ),
        key=lambda missed: (int(missed.created_at), str(missed.id)),
    )


def whatsapp_templates(setup: VoiceSetup) -> list[dict[str, Any]]:
    return [
        request.json()
        for request in setup.testbed.meta_transport.requests_to("/messages")
        if request.json().get("type") == "template"
    ]


def report_missed_call(setup: VoiceSetup, caller: str = CALLER) -> None:
    setup.testbed.missed_calls.execute(
        MissedCallReport(
            source=MissedCallSource.PBX,
            provider_call_id=ProviderCallId(f"in_{caller}"),
            reason=MissedCallReason.BUSY,
            called_at=setup.testbed.clock.now_microseconds(),
            assistant_number=RawPhoneNumberInput(ASSISTANT_LINE),
            caller_number=RawPhoneNumberInput(caller),
        )
    )


# --- Zadarma notifications ----------------------------------------------


def zadarma_form(
    disposition: str = "no answer",
    event: str = "NOTIFY_END",
    pbx_call_id: str = "in_1790856000.1",
    caller_id: str = CALLER,
    called_did: str = ASSISTANT_LINE,
    duration: str = "25",
) -> dict[str, str]:
    return {
        "event": event,
        "call_start": "2026-10-03 15:20:00",
        "pbx_call_id": pbx_call_id,
        "caller_id": caller_id,
        "called_did": called_did,
        "internal": "100",
        "duration": duration,
        "disposition": disposition,
        "status_code": "16",
        "is_recorded": "0",
    }


def sign_zadarma(fields: dict[str, str], secret: str = ZADARMA_API_SECRET) -> str:
    """Zadarma's PHP example: base64 of the hex HMAC-SHA1 digest."""

    signed: str = fields["caller_id"] + fields["called_did"] + fields["call_start"]
    digest: str = hmac.new(
        secret.encode("utf-8"), signed.encode("utf-8"), hashlib.sha1
    ).hexdigest()
    return base64.b64encode(digest.encode("ascii")).decode("ascii")


def encode_form(fields: dict[str, str]) -> bytes:
    return urlencode(fields).encode("utf-8")


# --- ElevenLabs failed starts --------------------------------------------


def failed_start_payload(
    conversation_id: str = "conv_failed",
    caller: str = CALLER,
    called: str = ASSISTANT_LINE,
) -> dict[str, Any]:
    return {
        "type": "call_initiation_failure",
        "event_timestamp": 1_790_855_900,
        "data": {
            "agent_id": "agent_1",
            "conversation_id": conversation_id,
            "failure_reason": "busy",
            "metadata": {
                "type": "sip",
                "body": {"from_number": caller, "to_number": called},
            },
        },
    }
