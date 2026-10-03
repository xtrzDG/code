"""
What the rehearsal customer writes (LLM_PROVIDER=scripted), by language
and intent, and the words its assistant recognizes in any chat.

The rehearsal plays the automatic checks without a language model: the
customer says one sentence for its scenario goal in the scenario
language, and the assistant tells the intent from these sentences (or
from the keywords below, for a person writing in a test chat).
"""

from enum import StrEnum


class RehearsalIntent(StrEnum):
    """What a rehearsal customer wants; what the rehearsal assistant does about it."""

    BOOKING = "booking"
    PRICE = "price"
    PERSON = "person"
    EMERGENCY = "emergency"
    OTHER = "other"


CUSTOMER_PHRASES: dict[str, dict[RehearsalIntent, str]] = {
    "en": {
        RehearsalIntent.BOOKING: "I would like to book, please. My phone number:",
        RehearsalIntent.PRICE: "How much does it cost?",
        RehearsalIntent.PERSON: "Can I talk to a manager, please?",
        RehearsalIntent.EMERGENCY: "Help, someone has fainted here!",
        RehearsalIntent.OTHER: "Hello, I have a question.",
    },
    "ru": {
        RehearsalIntent.BOOKING: "Хочу забронировать, пожалуйста. Мой телефон:",
        RehearsalIntent.PRICE: "Сколько это стоит?",
        RehearsalIntent.PERSON: "Позовите менеджера, пожалуйста.",
        RehearsalIntent.EMERGENCY: "Помогите, здесь человеку плохо!",
        RehearsalIntent.OTHER: "Здравствуйте, у меня вопрос.",
    },
    "uk": {
        RehearsalIntent.BOOKING: "Хочу забронювати, будь ласка. Мій телефон:",
        RehearsalIntent.PRICE: "Скільки це коштує?",
        RehearsalIntent.PERSON: "Покличте менеджера, будь ласка.",
        RehearsalIntent.EMERGENCY: "Допоможіть, тут людині погано!",
        RehearsalIntent.OTHER: "Добрий день, у мене питання.",
    },
    "ka": {
        RehearsalIntent.BOOKING: "მინდა დაჯავშნა, გთხოვთ. ჩემი ტელეფონი:",
        RehearsalIntent.PRICE: "რა ღირს?",
        RehearsalIntent.PERSON: "მენეჯერთან დამაკავშირეთ, გთხოვთ.",
        RehearsalIntent.EMERGENCY: "დამეხმარეთ, აქ ადამიანს ცუდად გახდა!",
        RehearsalIntent.OTHER: "გამარჯობა, კითხვა მაქვს.",
    },
    "de": {
        RehearsalIntent.BOOKING: "Ich möchte gern buchen. Meine Telefonnummer:",
        RehearsalIntent.PRICE: "Wie viel kostet das?",
        RehearsalIntent.PERSON: "Kann ich bitte mit einem Mitarbeiter sprechen?",
        RehearsalIntent.EMERGENCY: "Hilfe, hier ist jemand ohnmächtig geworden!",
        RehearsalIntent.OTHER: "Hallo, ich habe eine Frage.",
    },
    "fr": {
        RehearsalIntent.BOOKING: "Je voudrais réserver, s'il vous plaît. Mon numéro :",
        RehearsalIntent.PRICE: "Combien ça coûte ?",
        RehearsalIntent.PERSON: "Puis-je parler à un responsable, s'il vous plaît ?",
        RehearsalIntent.EMERGENCY: "Au secours, quelqu'un s'est évanoui ici !",
        RehearsalIntent.OTHER: "Bonjour, j'ai une question.",
    },
    "es": {
        RehearsalIntent.BOOKING: "Quisiera reservar, por favor. Mi teléfono:",
        RehearsalIntent.PRICE: "¿Cuánto cuesta?",
        RehearsalIntent.PERSON: "¿Puedo hablar con un encargado, por favor?",
        RehearsalIntent.EMERGENCY: "¡Ayuda, alguien se ha desmayado aquí!",
        RehearsalIntent.OTHER: "Hola, tengo una pregunta.",
    },
    "it": {
        RehearsalIntent.BOOKING: "Vorrei prenotare, per favore. Il mio telefono:",
        RehearsalIntent.PRICE: "Quanto costa?",
        RehearsalIntent.PERSON: "Posso parlare con un responsabile, per favore?",
        RehearsalIntent.EMERGENCY: "Aiuto, qui qualcuno è svenuto!",
        RehearsalIntent.OTHER: "Buongiorno, ho una domanda.",
    },
    "pt": {
        RehearsalIntent.BOOKING: "Gostaria de reservar, por favor. Meu telefone:",
        RehearsalIntent.PRICE: "Quanto custa?",
        RehearsalIntent.PERSON: "Posso falar com um responsável, por favor?",
        RehearsalIntent.EMERGENCY: "Socorro, alguém desmaiou aqui!",
        RehearsalIntent.OTHER: "Olá, tenho uma pergunta.",
    },
    "tr": {
        RehearsalIntent.BOOKING: "Rezervasyon yapmak istiyorum. Telefonum:",
        RehearsalIntent.PRICE: "Bu ne kadar?",
        RehearsalIntent.PERSON: "Bir yetkiliyle görüşebilir miyim?",
        RehearsalIntent.EMERGENCY: "Yardım edin, burada biri bayıldı!",
        RehearsalIntent.OTHER: "Merhaba, bir sorum var.",
    },
    "pl": {
        RehearsalIntent.BOOKING: "Chciałbym zarezerwować. Mój telefon:",
        RehearsalIntent.PRICE: "Ile to kosztuje?",
        RehearsalIntent.PERSON: "Czy mogę porozmawiać z kierownikiem?",
        RehearsalIntent.EMERGENCY: "Pomocy, ktoś tu zemdlał!",
        RehearsalIntent.OTHER: "Dzień dobry, mam pytanie.",
    },
    "az": {
        RehearsalIntent.BOOKING: "Rezerv etmək istəyirəm. Telefonum:",
        RehearsalIntent.PRICE: "Bu neçəyədir?",
        RehearsalIntent.PERSON: "Menecerlə danışa bilərəmmi?",
        RehearsalIntent.EMERGENCY: "Kömək edin, burada kimsə huşunu itirdi!",
        RehearsalIntent.OTHER: "Salam, bir sualım var.",
    },
    "hy": {
        RehearsalIntent.BOOKING: "Ուզում եմ ամրագրել։ Իմ հեռախոսը՝",
        RehearsalIntent.PRICE: "Ի՞նչ արժե։",
        RehearsalIntent.PERSON: "Կարո՞ղ եմ խոսել մենեջերի հետ։",
        RehearsalIntent.EMERGENCY: "Օգնեք, այստեղ մեկը ուշագնաց է եղել։",
        RehearsalIntent.OTHER: "Բարև, հարց ունեմ։",
    },
    "el": {
        RehearsalIntent.BOOKING: "Θα ήθελα να κάνω κράτηση. Το τηλέφωνό μου:",
        RehearsalIntent.PRICE: "Πόσο κοστίζει;",
        RehearsalIntent.PERSON: "Μπορώ να μιλήσω με έναν υπεύθυνο;",
        RehearsalIntent.EMERGENCY: "Βοήθεια, κάποιος λιποθύμησε εδώ!",
        RehearsalIntent.OTHER: "Γεια σας, έχω μια ερώτηση.",
    },
    "he": {
        RehearsalIntent.BOOKING: "אני רוצה להזמין, בבקשה. הטלפון שלי:",
        RehearsalIntent.PRICE: "כמה זה עולה?",
        RehearsalIntent.PERSON: "אפשר לדבר עם מנהל, בבקשה?",
        RehearsalIntent.EMERGENCY: "עזרה, מישהו התעלף כאן!",
        RehearsalIntent.OTHER: "שלום, יש לי שאלה.",
    },
    "ar": {
        RehearsalIntent.BOOKING: "أريد الحجز من فضلك. رقم هاتفي:",
        RehearsalIntent.PRICE: "كم السعر؟",
        RehearsalIntent.PERSON: "هل يمكنني التحدث مع المدير من فضلك؟",
        RehearsalIntent.EMERGENCY: "النجدة، شخص فقد وعيه هنا!",
        RehearsalIntent.OTHER: "مرحبا، لدي سؤال.",
    },
}

# What a person in a test chat may write to reach a colleague or to book.
PERSON_KEYWORDS: tuple[str, ...] = (
    "manager",
    "human",
    "person",
    "operator",
    "менеджер",
    "человек",
    "оператор",
    "администратор",
    "მენეჯერ",
    "ადამიან",
    "mitarbeiter",
    "responsable",
    "encargado",
    "yetkili",
    "kierownik",
    "מנהל",
    "المدير",
    "մենեջեր",
    "υπεύθυν",
)
BOOKING_KEYWORDS: tuple[str, ...] = (
    "book",
    "reserv",
    "заброн",
    "бронир",
    "დაჯავშნ",
    "buchen",
    "prenot",
    "rezerw",
    "rezerv",
    "להזמין",
    "الحجز",
    "ամրագր",
    "κράτηση",
)
