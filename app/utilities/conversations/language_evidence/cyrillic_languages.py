"""Evidence of the languages written in the Cyrillic script."""

from app.utilities.conversations.language_evidence.language_evidence import (
    LanguageEvidence,
    letters,
    words,
)

RUSSIAN_ALPHABET: str = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"

CYRILLIC_LANGUAGE_EVIDENCE: dict[str, LanguageEvidence] = {
    "ru": LanguageEvidence(
        "Cyrl",
        letters(RUSSIAN_ALPHABET),
        letters("ыэё"),
        words(
            "и в не на я что с это как а здравствуйте привет добрый день вечер "
            "спасибо пожалуйста хочу столик завтра сегодня сколько стоит можно "
            "есть у вас мне нам на двоих забронировать бронь цена меню да нет "
            "хорошо ладно спасибки"
        ),
    ),
    "uk": LanguageEvidence(
        "Cyrl",
        letters("абвгґдеєжзиіїйклмнопрстуфхцчшщьюя'’"),
        letters("ґєії"),
        words(
            "і в не на я що це як з у вас привіт вітаю добрий день вечір дякую "
            "будь ласка хочу столик завтра сьогодні скільки коштує можна є мені "
            "нам забронювати ціна меню ні добре"
        ),
    ),
    "be": LanguageEvidence(
        "Cyrl",
        letters("абвгдеёжзійклмнопрстуўфхцчшыьэюя'’"),
        letters("ў"),
        words(
            "і у не на я што гэта як з вас прывітанне добры дзень дзякуй калі "
            "ласка хачу столік заўтра сёння колькі каштуе можна ёсць мне"
        ),
    ),
    "kk": LanguageEvidence(
        "Cyrl",
        letters(RUSSIAN_ALPHABET + "әғқңөұүһі"),
        letters("әғқңөұүһ"),
        words(
            "және бір бұл мен сен сіз не қалай сәлем сәлеметсіз бе рақмет үстел "
            "ертең бүгін қанша тұрады бар жоқ керек маған бізге"
        ),
    ),
    "sr": LanguageEvidence(
        "Cyrl",
        letters("абвгдђежзијклљмнњопрстћуфхцчџш"),
        letters("ђћџ"),
        words(
            "и у не на је да се што шта за са здраво хвала молим сто сутра "
            "данас колико кошта има ли можете"
        ),
    ),
    "bg": LanguageEvidence(
        "Cyrl",
        letters("абвгдежзийклмнопрстуфхцчшщъьюяѝ"),
        letters("ъѝ"),
        words(
            "и в не на аз че се това как за с здравейте здравей благодаря моля "
            "искам маса утре днес колко струва има ли може"
        ),
    ),
    "mk": LanguageEvidence(
        "Cyrl",
        letters("абвгдѓежзѕијклљмнњопрстќуфхцчџш"),
        letters("ѓќѕ"),
        words(
            "и во не на јас дека се ова како за со здраво благодарам ве молам "
            "сакам маса утре денес колку чини има"
        ),
    ),
}
