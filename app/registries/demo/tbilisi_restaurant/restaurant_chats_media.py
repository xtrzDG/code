"""
Conversations of the demo restaurant that are not only text: a voice note
in Russian, and a photo, a shared place and a sticker in English.
"""

from app.registries.demo import demo_tool_calls as calls
from app.registries.demo.demo_activity_builder import DemoActivityBuilder
from app.registries.demo.demo_lines import assistant, customer
from app.registries.demo.demo_media_lines import (
    customer_photo,
    customer_place,
    customer_sticker,
    customer_voice,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.assistant_texts.attachment_notice_texts import (
    CANNOT_READ_ATTACHMENT,
)

TELEGRAM = ChannelKind.TELEGRAM
# Freedom Square, a walk from the restaurant in the Old Town.
FREEDOM_SQUARE: tuple[float, float] = (41.693438, 44.801525)


def record_media_chats(
    story: DemoActivityBuilder, guests: dict[str, ContactDocument]
) -> None:
    clock, talk = story.clock, story.talk
    khachapuri = story.item("Хачапури по-аджарски")

    # Irina asks by voice how long the khachapuri takes.
    talk.chat(
        guests["irina"],
        TELEGRAM,
        clock.past(-2, "18:40"),
        [
            customer_voice(
                "Здравствуйте! Сколько у вас готовится хачапури по-аджарски? "
                "Хотим заказать заранее, будем минут через сорок.",
                seconds=7,
            ),
            assistant(
                "Здравствуйте, Ирина! Хачапури по-аджарски готовим 20 минут, "
                "он стоит 22 лари. Заказать заранее в чате нельзя, но если "
                "скажете официанту сразу, как придёте, ждать почти не придётся.",
                calls.search("хачапури по-аджарски время", [khachapuri], "ru"),
            ),
            customer("Отлично, спасибо!"),
            assistant("Ждём вас! Приятного вечера."),
        ],
    )

    # Emily sends a photo, then where she is, then a sticker.
    latitude, longitude = FREEDOM_SQUARE
    talk.chat(
        guests["emily"],
        TELEGRAM,
        clock.past(-1, "13:10"),
        [
            customer_photo("Is this the khachapuri you serve? Saw it on Instagram"),
            assistant(
                "Yes, that's our Adjarian khachapuri: a boat of dough with "
                "suluguni cheese, an egg and butter. It costs 22 GEL and takes "
                "about 20 minutes.",
                calls.search("adjarian khachapuri", [khachapuri], "en"),
            ),
            customer_place(latitude, longitude, "Freedom Square", "Tbilisi"),
            customer("I'm here now, how do I get to you?", pause=20),
            assistant(
                "You're about a 10-minute walk away. Head south down "
                "Pushkin Street towards the Old Town; we're at 27 Kote Abkhazi "
                "Street. See you soon!"
            ),
            customer_sticker(pause=40),
            assistant(str(CANNOT_READ_ATTACHMENT.values[LanguageTag("en")])),
        ],
    )
