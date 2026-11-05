"""
A text-back never takes the caller id as proof: it still reaches the
number on WhatsApp, but its conversation belongs to the number's WhatsApp
account, never to a contact found by a verified phone, a given phone or
earlier calls; nobody gains an identity from it. Refusals go the other
way: any contact holding the number that is blocked or said STOP, or
writes with the business, holds the text-back back.
"""

import pytest

from app.schemas.constants.calls import TextBackSkipReason, TextBackStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.contacts import ChannelIdentity, ContactBlock, ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.prefixed_id import UserId
from tests.calls.call_steps import (
    connect_whatsapp,
    missed_calls,
    report_missed_call,
    save_call_settings,
    whatsapp_templates,
)
from tests.channels.meta_payloads import post_meta, whatsapp_message, whatsapp_webhook
from tests.channels.post_call_steps import post_call_payload, process_call, stored_calls
from tests.channels.voice_setup import CALLER, VoiceSetup, build_voice_setup

WHATSAPP_ID: str = CALLER.removeprefix("+")


@pytest.fixture
def setup() -> VoiceSetup:
    """The setup's contact is call-only: known from calls from the number."""

    voice_setup = build_voice_setup()
    save_call_settings(voice_setup)
    connect_whatsapp(voice_setup)
    voice_setup.contact.channel_identities = [identity(ChannelKind.PHONE, CALLER)]
    voice_setup.contact.name = ContactName("Nino")
    voice_setup.testbed.contact_repo.save(voice_setup.contact)
    return voice_setup


def stored(setup: VoiceSetup, contact: ContactDocument) -> ContactDocument | None:
    return setup.testbed.contact_repo.get(setup.business.id, contact.id)


def text_back_contact(setup: VoiceSetup) -> ContactDocument:
    [missed] = missed_calls(setup)
    assert missed.status is TextBackStatus.SENT
    assert missed.conversation_id is not None
    conversation = setup.testbed.conversation_repo.get(
        setup.business.id, missed.conversation_id
    )
    assert conversation is not None
    contact = setup.testbed.contact_repo.get(setup.business.id, conversation.contact_id)
    assert contact is not None
    return contact


def identity(channel: ChannelKind, user_id: str) -> ChannelIdentity:
    return ChannelIdentity(channel=channel, channel_user_id=ChannelUserId(user_id))


def other_holder(
    setup: VoiceSetup,
    identities: list[ChannelIdentity],
    is_verified: bool = False,
    opted_out: list[ChannelKind] | None = None,
) -> ContactDocument:
    """Another contact holding the number (given, proved, of a single call)."""

    now = setup.testbed.clock.now_microseconds()
    contact = ContactDocument(
        business_id=setup.business.id,
        phone_number=E164PhoneNumber(CALLER),
        verified_phone_number=E164PhoneNumber(CALLER) if is_verified else None,
        channel_identities=identities,
        opted_out_channels=opted_out or [],
        created_at=now,
        updated_at=now,
    )
    setup.testbed.contact_repo.save(contact)
    return contact


def block(setup: VoiceSetup, contact: ContactDocument) -> None:
    moment = setup.testbed.clock.now_microseconds()

    def blocked_by_staff(card: ContactDocument) -> None:
        card.block = ContactBlock(blocked_at=moment, blocked_by=UserId())

    setup.testbed.contact_repo.change_card(
        setup.business.id, contact.id, blocked_by_staff
    )


def skip_reason(setup: VoiceSetup) -> TextBackSkipReason | None:
    report_missed_call(setup)
    [missed] = missed_calls(setup)
    return missed.skip_reason


class TestCallerResolution:
    @pytest.mark.parametrize("is_verified_by_old_code", [False, True])
    def test_a_call_only_contact_gets_no_whatsapp_account(
        self, setup: VoiceSetup, is_verified_by_old_code: bool
    ) -> None:
        # Earlier releases stored a caller id as a verified phone: that is
        # no proof either.
        if is_verified_by_old_code:
            setup.contact.verified_phone_number = E164PhoneNumber(CALLER)
            setup.testbed.contact_repo.save(setup.contact)
        before = stored(setup, setup.contact)

        report_missed_call(setup)
        setup.testbed.run_worker()

        # The text-back still reaches the number on WhatsApp.
        [template] = whatsapp_templates(setup)
        assert template["to"] == WHATSAPP_ID
        assert stored(setup, setup.contact) == before
        contact = text_back_contact(setup)
        assert contact.id != setup.contact.id
        assert contact.name is None
        assert contact.phone_number == CALLER
        assert contact.verified_phone_number is None
        assert contact.channel_identities == [
            ChannelIdentity(
                channel=ChannelKind.WHATSAPP, channel_user_id=ChannelUserId(WHATSAPP_ID)
            )
        ]

    def test_the_numbers_whatsapp_customer_keeps_the_conversation(
        self, setup: VoiceSetup
    ) -> None:
        customer = other_holder(setup, [identity(ChannelKind.WHATSAPP, WHATSAPP_ID)])

        report_missed_call(setup)
        setup.testbed.run_worker()

        contact = text_back_contact(setup)
        assert contact.id == customer.id
        assert contact.channel_identities == customer.channel_identities

    def test_later_calls_keep_their_call_only_contact(self, setup: VoiceSetup) -> None:
        report_missed_call(setup)
        setup.testbed.run_worker()
        whatsapp_contact = text_back_contact(setup)

        process_call(setup, post_call_payload("conv_after"))

        [call] = [
            call
            for call in stored_calls(setup)
            if str(call.provider_call_id) == "conv_after"
        ]
        assert call.conversation_id is not None
        conversation = setup.testbed.conversation_repo.get(
            setup.business.id, call.conversation_id
        )
        assert conversation is not None
        assert conversation.contact_id == setup.contact.id
        assert conversation.contact_id != whatsapp_contact.id

    def test_the_reply_joins_the_whatsapp_contacts_conversation(
        self, setup: VoiceSetup
    ) -> None:
        report_missed_call(setup)
        setup.testbed.run_worker()
        contact = text_back_contact(setup)
        [missed] = missed_calls(setup)

        post_meta(
            setup.testbed, whatsapp_webhook([whatsapp_message(WHATSAPP_ID, "Ciao")])
        )
        setup.testbed.run_worker()

        assert missed.conversation_id is not None
        [conversation] = setup.testbed.conversation_repo.list_by_channel_user(
            setup.business.id, ChannelKind.WHATSAPP, ChannelUserId(WHATSAPP_ID)
        )
        assert conversation.id == missed.conversation_id
        assert conversation.contact_id == contact.id
        replies = [
            str(message.text)
            for message in setup.testbed.message_repo.list_by_conversation(
                setup.business.id, conversation.id
            )
            if message.author is MessageAuthor.CUSTOMER
        ]
        assert replies == ["Ciao"]


class TestRefusals:
    def test_a_blocked_call_only_contact_is_not_texted(self, setup: VoiceSetup) -> None:
        block(setup, setup.contact)

        assert skip_reason(setup) is TextBackSkipReason.OPTED_OUT
        assert whatsapp_templates(setup) == []

    def test_a_blocked_contact_of_a_single_call_is_not_texted(
        self, setup: VoiceSetup
    ) -> None:
        single_call = other_holder(setup, [identity(ChannelKind.PHONE, "el_call_7")])
        block(setup, single_call)

        assert skip_reason(setup) is TextBackSkipReason.OPTED_OUT

    def test_a_holder_who_said_stop_is_not_texted(self, setup: VoiceSetup) -> None:
        other_holder(
            setup,
            [identity(ChannelKind.TELEGRAM, "555")],
            opted_out=[ChannelKind.TELEGRAM],
        )

        assert skip_reason(setup) is TextBackSkipReason.OPTED_OUT

    def test_a_holder_writing_in_a_messenger_is_not_texted(
        self, setup: VoiceSetup
    ) -> None:
        writer = other_holder(
            setup, [identity(ChannelKind.TELEGRAM, "555")], is_verified=True
        )
        setup.testbed.conversation_repo.save(
            ConversationDocument(
                business_id=setup.business.id,
                contact_id=writer.id,
                assistant_version_id=setup.conversation.assistant_version_id,
                channel=ChannelKind.TELEGRAM,
                channel_user_id=ChannelUserId("555"),
                last_message_at=setup.testbed.clock.now_microseconds(),
            )
        )

        assert skip_reason(setup) is TextBackSkipReason.IN_CONVERSATION
