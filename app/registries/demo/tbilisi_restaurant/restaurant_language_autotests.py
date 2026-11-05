"""
The language scenarios of the restaurant's autotest run: a guest who writes
Hebrew or German, which the restaurant does not list, and guests who type
Georgian or Russian in Latin letters. Each answer opens with the AI
disclosure the platform puts in the guest's language.
"""

from app.schemas.constants.assistants import AutotestScenarioKind as Kind

# (kind, language) -> the customer's opening line and the assistant's answer.
LANGUAGE_LINES: dict[tuple[Kind, str], tuple[str, str]] = {
    (Kind.FOREIGN_LANGUAGE, "he"): (
        "שלום, אתם פתוחים מחר בערב? מה כדאי להזמין?",
        "שלום! אני עוזר ה-AI של Mtsvane Ezo.\n"
        "כן, מחר אנחנו פתוחים מ-12:00. מומלץ לנסות חצ'פורי אג'רי וחינקלי. "
        "לשמור לכם שולחן?",
    ),
    (Kind.FOREIGN_LANGUAGE, "de"): (
        "Hallo, haben Sie morgen Abend geöffnet? Was empfehlen Sie?",
        "Hallo! Ich bin der KI-Assistent von Mtsvane Ezo.\n"
        "Ja, morgen haben wir ab 12:00 geöffnet. Probieren Sie Chatschapuri "
        "nach adscharischer Art und Chinkali. Soll ich einen Tisch reservieren?",
    ),
    (Kind.TRANSLITERATED, "ka"): (
        "gamarjoba, xval saghamos ghia xart? acharuli xachapuri ramdeni ghirs?",
        "გამარჯობა! მე ვარ Mtsvane Ezo-ის AI-ასისტენტი.\n"
        "დიახ, ხვალ 12:00-დან ვმუშაობთ. აჭარული ხაჭაპური 22 ლარი ღირს.",
    ),
    (Kind.TRANSLITERATED, "ru"): (
        "zdravstvuyte, vy zavtra vecherom rabotaete? skolko stoit hachapuri?",
        "Здравствуйте! Я AI-ассистент «Mtsvane Ezo».\n"
        "Да, завтра работаем с 12:00. Хачапури по-аджарски стоит 22 лари.",
    ),
}
