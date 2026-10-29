"""
The greeting's offer of the business's other languages: a caller who does
not follow the greeting's language hears which others the assistant
speaks and that they may answer in any of them (the voice agent detects
the language of the answer and switches).

The sentence exists only in the languages it is written in: a greeting in
another language leaves it out rather than say it in English. The
`{languages}` placeholder takes the other languages named in the
greeting's language, as one list ("georgiano, russo e inglese").
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

CALL_LANGUAGE_OFFER: LocalizedText = build_localized_text(
    en="I can also speak other languages: {languages}. Just answer in the "
    "language you prefer.",
    it="Posso parlare anche in altre lingue: {languages}. Risponda pure nella "
    "lingua che preferisce.",
    de="Ich spreche auch andere Sprachen: {languages}. Antworten Sie einfach in "
    "der Sprache, die Ihnen lieber ist.",
    fr="Je parle aussi d'autres langues : {languages}. Répondez simplement dans "
    "la langue que vous préférez.",
    es="También hablo otros idiomas: {languages}. Responda en el idioma que prefiera.",
    pt="Também falo outros idiomas: {languages}. Responda no idioma que preferir.",
    nl="Ik spreek ook andere talen: {languages}. Antwoord gerust in de taal die "
    "u verkiest.",
    pl="Mówię też w innych językach: {languages}. Proszę odpowiadać w wybranym języku.",
    ru="Я говорю и на других языках: {languages}. Отвечайте на том, который вам "
    "удобнее.",
    uk="Я розмовляю й іншими мовами: {languages}. Відповідайте тією, якою вам "
    "зручніше.",
    ka="სხვა ენებზეც ვსაუბრობ: {languages}. უპასუხეთ იმ ენაზე, რომელიც გირჩევნიათ.",
    he="אני מדבר גם בשפות אחרות: {languages}. אפשר לענות בשפה הנוחה לכם.",
    ar="أتحدث أيضًا لغات أخرى: {languages}. يمكنك الرد باللغة التي تفضلها.",
    tr="Başka dillerde de konuşabilirim: {languages}. Size uygun olan dilde "
    "yanıt verebilirsiniz.",
)

LANGUAGES_PLACEHOLDER: str = "{languages}"
