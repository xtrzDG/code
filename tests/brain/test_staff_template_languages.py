"""
After the WhatsApp window a staff reply goes in the template of the
customer's language: a Hebrew or Arabic guest no longer gets the staff text
inside the Russian template.
"""

from datetime import timedelta

import pytest

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.channels import ChannelDocument, WhatsAppStaffTemplate
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.conversation_cabinet_helpers import Cabinet
from tests.brain.scripted_turns import say, scripted


def template(language: str) -> WhatsAppStaffTemplate:
    return WhatsAppStaffTemplate(
        name=WhatsAppTemplateName("staff_reply"),
        language_code=WhatsAppTemplateLanguageCode(language),
    )


def connect_whatsapp(world: BrainWorld, languages: list[str]) -> None:
    templates = [template(language) for language in languages]
    world.channel_repo.save(
        ChannelDocument(
            business_id=world.business.id,
            kind=ChannelKind.WHATSAPP,
            status=ChannelStatus.CONNECTED,
            whatsapp_staff_template=templates[0] if templates else None,
            whatsapp_staff_templates=templates,
        )
    )


def conversation_in(world: BrainWorld, language: str) -> ConversationId:
    """A WhatsApp conversation whose customer writes in `language`."""

    reply = world.send("Hi")
    for conversation in world.conversations():
        if conversation.id == reply.conversation_id:
            conversation.language = LanguageTag(language)
            world.conversation_repo.save(conversation)

    return reply.conversation_id


@pytest.mark.parametrize("language", ["he", "ar", "ru"])
def test_the_reply_goes_in_the_template_of_the_customer_language(
    language: str,
) -> None:
    world = build_world(scripted(say("Hello!")))
    conversation_id = conversation_in(world, language)
    connect_whatsapp(world, [str(world.business.default_language), "ru", "he", "ar"])
    world.clock.advance(timedelta(hours=26))
    cabinet = Cabinet(world)

    offered = cabinet.card(conversation_id)["reply"]["template"]
    sent = cabinet.reply(conversation_id, "Your table is ready", as_template=True)

    assert offered["language_code"] == language
    assert sent.status_code == 201, sent.text
    [queued] = cabinet.storage.outbox.queued()
    assert queued.template is not None
    assert str(queued.template.language_code) == language
    assert [str(parameter) for parameter in queued.template.body_parameters] == [
        "Your table is ready"
    ]


def test_a_language_without_a_template_gets_the_business_default_one() -> None:
    world = build_world(scripted(say("Hello!")))
    default = str(world.business.default_language)
    conversation_id = conversation_in(world, "fr")
    connect_whatsapp(world, ["ru", default])
    world.clock.advance(timedelta(hours=26))

    offered = Cabinet(world).card(conversation_id)["reply"]["template"]

    assert offered["language_code"] == default
