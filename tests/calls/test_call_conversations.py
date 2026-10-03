"""
Every answered call has a conversation (its card shows the summary), and
a text-back joins the caller's WhatsApp conversation, whoever they are.
"""

import json

import pytest

from app.schemas.constants.calls import TextBackChannel, TextBackStatus
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.exceptions.application_errors import DeliveryNotConfiguredError
from app.schemas.typings.conversations.strings import ChannelUserId
from app.transformers.conversations.call_view_transformer import CallViewTransformer
from app.use_cases.voice.missed_calls.text_back_messages import TextBackSender
from tests.calls.call_steps import (
    WHATSAPP_NUMBER_ID,
    connect_whatsapp,
    missed_calls,
    report_missed_call,
    save_call_settings,
)
from tests.channels.post_call_steps import post_call_payload, process_call, stored_calls
from tests.channels.voice_setup import VoiceSetup, build_voice_setup

STRANGER: str = "+995599765432"


@pytest.fixture
def setup() -> VoiceSetup:
    voice_setup = build_voice_setup()
    save_call_settings(voice_setup)
    connect_whatsapp(voice_setup)
    return voice_setup


class TestCallConversations:
    def test_a_new_caller_gets_a_contact_and_a_conversation(
        self, setup: VoiceSetup
    ) -> None:
        setup.testbed.summary_answers.append(json.dumps({"ka": "ჯავშანი უნდა."}))

        process_call(
            setup,
            post_call_payload("conv_new", external_number="+995 599 76 54 32"),
        )

        [call] = stored_calls(setup)
        assert call.conversation_id is not None
        conversation = setup.testbed.conversation_repo.get(
            setup.business.id, call.conversation_id
        )
        assert conversation is not None
        assert conversation.channel is ChannelKind.PHONE
        assert str(conversation.channel_user_id) == "conv_new"
        contact = setup.testbed.contact_repo.get(
            setup.business.id, conversation.contact_id
        )
        assert contact is not None
        assert contact.verified_phone_number == STRANGER
        # The call card shows the summary with the transcript.
        view = CallViewTransformer().transform(call)
        assert [(str(s.language), str(s.text)) for s in view.summaries] == [
            ("ka", "ჯავშანი უნდა.")
        ]

    def test_a_call_with_a_hidden_number_gets_one_too(self, setup: VoiceSetup) -> None:
        process_call(setup, post_call_payload("conv_hidden", external_number=None))

        [call] = stored_calls(setup)
        assert call.conversation_id is not None


class TestTextBackConversations:
    def test_a_known_caller_without_whatsapp_gets_it_added(
        self, setup: VoiceSetup
    ) -> None:
        setup.contact.channel_identities = [
            identity
            for identity in setup.contact.channel_identities
            if identity.channel is not ChannelKind.WHATSAPP
        ]
        setup.contact.verified_phone_number = setup.contact.phone_number
        setup.testbed.contact_repo.save(setup.contact)

        report_missed_call(setup)
        setup.testbed.run_worker()

        contact = setup.testbed.contact_repo.get(setup.business.id, setup.contact.id)
        assert contact is not None
        assert ChannelKind.WHATSAPP in {
            identity.channel for identity in contact.channel_identities
        }

    def test_a_conversation_opened_meanwhile_is_continued(
        self, setup: VoiceSetup
    ) -> None:
        report_missed_call(setup)
        # The caller wrote on WhatsApp after the call, before the worker ran.
        conversation = ConversationDocument(
            business_id=setup.business.id,
            contact_id=setup.contact.id,
            assistant_version_id=setup.conversation.assistant_version_id,
            channel=ChannelKind.WHATSAPP,
            channel_user_id=ChannelUserId("995599123456"),
            last_message_at=setup.testbed.clock.now_microseconds(),
        )
        setup.testbed.conversation_repo.save(conversation)

        setup.testbed.run_worker()

        [missed] = missed_calls(setup)
        assert missed.conversation_id == conversation.id

    def test_a_number_disconnected_meanwhile_falls_back_to_sms(
        self, setup: VoiceSetup
    ) -> None:
        report_missed_call(setup)
        [channel] = [
            channel
            for channel in setup.testbed.channel_repo.list_by_business(
                setup.business.id
            )
            if str(channel.external_id) == WHATSAPP_NUMBER_ID
        ]
        channel.status = ChannelStatus.DISABLED
        setup.testbed.channel_repo.save(channel)

        setup.testbed.run_worker()

        [missed] = missed_calls(setup)
        assert missed.status is TextBackStatus.SENT
        assert missed.channel is TextBackChannel.SMS
        assert setup.testbed.meta_transport.requests_to("/messages") == []

    def test_a_sender_without_sms_or_a_template_refuses(
        self, setup: VoiceSetup
    ) -> None:
        report_missed_call(setup)
        [missed] = missed_calls(setup)
        assert missed.caller_phone_number is not None
        sender = TextBackSender(
            setup.testbed.channel_repo,
            setup.testbed.channel_message_sender,
            None,
            setup.testbed.text_resolver,
        )

        with pytest.raises(DeliveryNotConfiguredError):
            sender.send_sms(setup.business, missed, missed.caller_phone_number)
        with pytest.raises(DeliveryNotConfiguredError):
            sender.send_whatsapp(
                setup.business, missed, missed.caller_phone_number, None
            )
