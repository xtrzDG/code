"""
Evidence for telling languages apart in short customer messages.

Writing systems are recognized by Unicode blocks. Languages that share a
script are told apart by letters (an alphabet, letters that only this
language uses) and by short lists of very frequent words, including the
words of a typical first message to a business (greetings, "table",
"tomorrow", "how much"). No external model is involved, so detection is
instant and deterministic.
"""

from typing import NamedTuple

ASCII_LETTERS: frozenset[str] = frozenset("abcdefghijklmnopqrstuvwxyz")
# Unicode blocks of the scripts the assistant meets, as ISO 15924 codes.
SCRIPT_RANGES: tuple[tuple[int, int, str], ...] = (
    (0x0041, 0x005A, "Latn"),
    (0x0061, 0x007A, "Latn"),
    (0x00C0, 0x024F, "Latn"),
    (0x1E00, 0x1EFF, "Latn"),
    (0x0370, 0x03FF, "Grek"),
    (0x1F00, 0x1FFF, "Grek"),
    (0x0400, 0x052F, "Cyrl"),
    (0x1C80, 0x1C8F, "Cyrl"),
    (0x2DE0, 0x2DFF, "Cyrl"),
    (0xA640, 0xA69F, "Cyrl"),
    (0x0530, 0x058F, "Armn"),
    (0xFB13, 0xFB17, "Armn"),
    (0x0590, 0x05FF, "Hebr"),
    (0xFB1D, 0xFB4F, "Hebr"),
    (0x0600, 0x06FF, "Arab"),
    (0x0750, 0x077F, "Arab"),
    (0x08A0, 0x08FF, "Arab"),
    (0xFB50, 0xFDFF, "Arab"),
    (0xFE70, 0xFEFF, "Arab"),
    (0x0900, 0x097F, "Deva"),
    (0xA8E0, 0xA8FF, "Deva"),
    (0x0E00, 0x0E7F, "Thai"),
    (0x10A0, 0x10FF, "Geor"),
    (0x1C90, 0x1CBF, "Geor"),
    (0x2D00, 0x2D2F, "Geor"),
    (0x1100, 0x11FF, "Hang"),
    (0x3130, 0x318F, "Hang"),
    (0xAC00, 0xD7AF, "Hang"),
    (0x3040, 0x309F, "Kana"),
    (0x30A0, 0x30FF, "Kana"),
    (0x31F0, 0x31FF, "Kana"),
    (0xFF66, 0xFF9F, "Kana"),
    (0x3400, 0x4DBF, "Hani"),
    (0x4E00, 0x9FFF, "Hani"),
    (0xF900, 0xFAFF, "Hani"),
    (0x20000, 0x2A6DF, "Hani"),
)
# Detected script -> script codes of language tags written in it (CLDR
# likely subtags give "Hans"/"Hant" for Chinese, "Jpan" for Japanese).
COMPATIBLE_TAG_SCRIPTS: dict[str, frozenset[str]] = {
    "Hani": frozenset({"Hani", "Hans", "Hant", "Jpan"}),
    "Kana": frozenset({"Jpan"}),
    "Hang": frozenset({"Hang", "Kore"}),
}
# Vietnamese letters with tone marks (Latin Extended Additional) and its
# unique base letters.
VIETNAMESE_LETTERS: frozenset[str] = frozenset(
    {chr(code) for code in range(0x1EA0, 0x1EFA) if chr(code).islower()}
    | {"đ", "ơ", "ư"}
)


class LanguageEvidence(NamedTuple):
    """
    How a language looks in writing (a technical lookup record).

    `script` is the ISO 15924 code the evidence is written in (a language
    may also be written in another script, like "sr-Latn"). `alphabet`
    lists every letter of that script the language uses; letters of the
    script outside it count against the language. None means the alphabet
    is not checked.
    """

    script: str
    alphabet: frozenset[str] | None
    distinctive_letters: frozenset[str]
    frequent_words: frozenset[str]


def words(text: str) -> frozenset[str]:
    return frozenset(text.split())


def letters(text: str) -> frozenset[str]:
    return frozenset(text)


RUSSIAN_ALPHABET: str = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"

LANGUAGE_EVIDENCE: dict[str, LanguageEvidence] = {
    # Latin script.
    "en": LanguageEvidence(
        "Latn",
        ASCII_LETTERS,
        frozenset(),
        words(
            "the and is are you your i a an to for of in on at have has do does "
            "can could would what how when where hello hi hey please thanks "
            "thank table tomorrow today tonight my me we want book there much "
            "price open with it this that be will not no yes"
        ),
    ),
    "tr": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("çğıöşüâîû"),
        frozenset(),
        words(
            "ve bir bu için ne mi mı mu mü var yok merhaba selam teşekkür "
            "teşekkürler lütfen ben sen siz nasıl kaç masa yarın bugün akşam "
            "istiyorum değil çok ile de da fiyat kadar rezervasyon saat kişilik "
            "kişi olur mümkün"
        ),
    ),
    "az": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("çəğıöşü"),
        letters("ə"),
        words(
            "və bir bu üçün nə salam təşəkkür edirəm mən sən siz masa sabah gün "
            "axşam istəyirəm var yox necə neçə qiymət qiyməti nədir zəhmət "
            "olmasa nəfər"
        ),
    ),
    "de": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("äöüß"),
        letters("äß"),
        words(
            "der die das und ist nicht ich sie wir ein eine einen mit für auf "
            "haben habe bitte danke hallo guten tag morgen heute abend tisch zu "
            "wie was gibt es möchte können kann viel kostet reservieren uhr "
            "personen noch frei"
        ),
    ),
    "fr": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("àâæçéèêëîïôœùûüÿ"),
        letters("œëÿ"),
        words(
            "le la les et est je vous un une pour avec bonjour bonsoir merci des "
            "du pas qui que il elle nous sur dans ce cette réserver réservation "
            "table demain soir combien coûte prix voudrais plaît heures "
            "personnes ouvert"
        ),
    ),
    "es": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("áéíñóúü"),
        letters("ñ¿¡"),
        words(
            "el la los las y es que de en un una para por con hola gracias quiero "
            "mesa mañana reservar está hay cuánto cuesta precio buenas noches "
            "tardes personas abierto puedo"
        ),
    ),
    "it": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("àèéìíîòóù"),
        letters("ìò"),
        words(
            "il lo la gli le e è che di un una per con ciao buongiorno buonasera "
            "grazie vorrei tavolo domani sera quanto costa prenotare sono non "
            "prezzo persone aperto posso"
        ),
    ),
    "pt": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("áâãàçéêíóôõú"),
        letters("ãõ"),
        words(
            "o a os as e é que de um uma para com olá oi obrigado obrigada quero "
            "mesa amanhã reservar quanto custa você não está gostaria preço "
            "pessoas aberto posso tem"
        ),
    ),
    "pl": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("ąćęłńóśźż"),
        letters("ąćęłńśźż"),
        words(
            "i w z na nie jest to się że do dzień dobry dziękuję proszę "
            "chciałbym chciałabym stolik jutro ile kosztuje czy cena osób "
            "otwarte mogę"
        ),
    ),
    "nl": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("áéèëïóöü"),
        frozenset(),
        words(
            "de het een en is van ik je niet dat op voor met hallo goedendag "
            "dank bedankt graag tafel morgen wil hoeveel kost zijn reserveren "
            "personen open kan"
        ),
    ),
    "ro": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("ăâîșțşţ"),
        letters("ășțţ"),
        words(
            "și de la în este nu un o pentru cu bună ziua mulțumesc vă rog aș "
            "vrea masă mâine cât costă preț persoane deschis pot"
        ),
    ),
    "vi": LanguageEvidence(
        "Latn",
        None,
        VIETNAMESE_LETTERS,
        words(
            "và là của có không tôi bạn một cho với xin chào cảm ơn bàn ngày "
            "mai bao nhiêu giá đặt người mở cửa được"
        ),
    ),
    "id": LanguageEvidence(
        "Latn",
        ASCII_LETTERS,
        frozenset(),
        words(
            "dan yang di ini itu saya anda untuk dengan tidak ada apa halo "
            "terima kasih meja besok berapa harga mau pesan bisa selamat orang "
            "buka"
        ),
    ),
    # Cyrillic script.
    "ru": LanguageEvidence(
        "Cyrl",
        letters(RUSSIAN_ALPHABET),
        letters("ыэё"),
        words(
            "и в не на я что с это как а здравствуйте привет добрый день вечер "
            "спасибо пожалуйста хочу столик завтра сегодня сколько стоит можно "
            "есть у вас мне нам на двоих забронировать бронь цена меню"
        ),
    ),
    "uk": LanguageEvidence(
        "Cyrl",
        letters("абвгґдеєжзиіїйклмнопрстуфхцчшщьюя'’"),
        letters("ґєії"),
        words(
            "і в не на я що це як з у вас привіт вітаю добрий день вечір дякую "
            "будь ласка хочу столик завтра сьогодні скільки коштує можна є мені "
            "нам забронювати ціна меню"
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
    # Arabic script.
    "ar": LanguageEvidence(
        "Arab",
        None,
        letters("ةىإؤ"),
        words(
            "في من على أن هل ما مرحبا شكرا أريد طاولة غدا اليوم كم سعر السعر لو "
            "سمحت فضلك عندكم هذا مساء الخير"
        ),
    ),
    "fa": LanguageEvidence(
        "Arab",
        None,
        letters("پچژگ"),
        words(
            "و در به از که این است را با برای سلام ممنون می خواهم میز فردا "
            "امروز چند قیمت لطفا"
        ),
    ),
    "ur": LanguageEvidence(
        "Arab",
        None,
        letters("ٹڈڑںےھ"),
        words(
            "اور میں کے کی ہے کا سے کو یہ آپ نہیں سلام شکریہ چاہیے میز کل آج "
            "کتنے قیمت براہ کرم"
        ),
    ),
    # Devanagari script.
    "hi": LanguageEvidence(
        "Deva",
        None,
        frozenset(),
        words("है और के में की से को यह नमस्ते धन्यवाद कितना कल आज टेबल चाहिए"),
    ),
    "mr": LanguageEvidence(
        "Deva",
        None,
        letters("ळ"),
        words("आहे आणि च्या मध्ये नमस्कार धन्यवाद किती उद्या आज टेबल हवे"),
    ),
    "ne": LanguageEvidence(
        "Deva",
        None,
        frozenset(),
        words("छ र को मा नमस्ते धन्यवाद कति भोलि आज टेबल चाहियो"),
    ),
}
