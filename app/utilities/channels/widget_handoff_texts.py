"""
What staff read about a visitor who pressed "Talk to a person" in the
website chat: the request, then the visitor's last message (quoted, so
staff see what it is about). In the business's staff language; the
cabinet's handoff card shows the same text.
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

# Longer messages are cut: the conversation itself has the whole text.
MAX_QUOTED_MESSAGE_LENGTH: int = 300

PERSON_REQUESTED: LocalizedText = build_localized_text(
    en="The visitor pressed “Talk to a person” in the website chat.",
    ru="Посетитель нажал «Связаться с человеком» в чате на сайте.",
    ka="ვიზიტორმა საიტის ჩატში დააჭირა ღილაკს „ადამიანთან დაკავშირება“.",
    uk="Відвідувач натиснув «Зв’язатися з людиною» в чаті на сайті.",
    de="Die Besucherin oder der Besucher hat im Website-Chat „Mit einem "
    "Menschen sprechen“ gewählt.",
    tr="Ziyaretçi web sitesi sohbetinde “Bir kişiyle konuş” düğmesine bastı.",
)
LAST_MESSAGE: LocalizedText = build_localized_text(
    en="Their last message: “{message}”",
    ru="Последнее сообщение: «{message}»",
    ka="ბოლო შეტყობინება: „{message}“",
    uk="Останнє повідомлення: «{message}»",
    de="Letzte Nachricht: „{message}“",
    tr="Son mesajı: “{message}”",
)


def quote_last_message(text: str) -> str:
    """The message on one line, cut to a readable length."""

    one_line: str = " ".join(text.split())
    if len(one_line) <= MAX_QUOTED_MESSAGE_LENGTH:
        return one_line

    return one_line[: MAX_QUOTED_MESSAGE_LENGTH - 1].rstrip() + "…"
