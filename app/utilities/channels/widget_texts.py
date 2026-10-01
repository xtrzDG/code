"""
The website chat's first message. It discloses the AI assistant (as every
chat reply does) and offers help; where the widget's own greeting is not
translated, the AI disclosure of the conversation engine is used alone.
`{business}` is replaced with the business name.
"""

from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.utilities.conversations.assistant_texts import (
    AI_DISCLOSURE,
    fill_business_name,
)
from app.utilities.localization.language_tags import base_language_code
from app.utilities.localization.localized_texts import build_localized_text

WIDGET_GREETING: LocalizedText = build_localized_text(
    en="Hello! I am the AI assistant of {business}. How can I help you?",
    ru="Здравствуйте! Я AI-ассистент «{business}». Чем могу помочь?",
    ka="გამარჯობა! მე ვარ {business}-ის AI-ასისტენტი. რით შემიძლია დაგეხმაროთ?",
    uk="Вітаю! Я AI-асистент «{business}». Чим можу допомогти?",
    tr=(
        "Merhaba! Ben {business} işletmesinin yapay zekâ asistanıyım. Size nasıl "
        "yardımcı olabilirim?"
    ),
    he="שלום! אני עוזר ה-AI של {business}. איך אפשר לעזור?",
    ar="مرحبًا! أنا مساعد الذكاء الاصطناعي لدى {business}. كيف يمكنني مساعدتك؟",
    de="Hallo! Ich bin der KI-Assistent von {business}. Wie kann ich helfen?",
    fr="Bonjour ! Je suis l'assistant IA de {business}. Comment puis-je vous aider ?",
    es="¡Hola! Soy el asistente de IA de {business}. ¿En qué puedo ayudarle?",
    it="Buongiorno! Sono l'assistente IA di {business}. Come posso aiutarla?",
    pt="Olá! Sou o assistente de IA de {business}. Como posso ajudar?",
    pl="Dzień dobry! Jestem asystentem AI w {business}. W czym mogę pomóc?",
    zh="您好！我是{business}的AI助手。有什么可以帮您？",
    ja="こんにちは！{business}のAIアシスタントです。ご用件をどうぞ。",
)


def find_language_value(
    text: LocalizedText,
    language: LanguageTag,
) -> LocalizedTextValue | None:
    """The text in the language or its base language; never another language."""

    exact: LocalizedTextValue | None = text.values.get(language)
    if exact is not None:
        return exact

    base_code: str = base_language_code(language)
    for tag, value in text.values.items():
        if str(tag).lower() == base_code.lower():
            return value

    return None


def build_widget_greeting(language: LanguageTag, business_name: str) -> str | None:
    """
    The greeting in the language (the full one, else the AI disclosure), or
    None when neither exists there (the widget then uses its own text).
    """

    template: LocalizedTextValue | None = find_language_value(
        WIDGET_GREETING, language
    ) or find_language_value(AI_DISCLOSURE, language)
    if template is None:
        return None

    return fill_business_name(str(template), business_name)
