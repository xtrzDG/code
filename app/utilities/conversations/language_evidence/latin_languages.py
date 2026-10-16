"""Evidence of the languages written in the Latin script."""

from app.utilities.conversations.language_evidence.language_evidence import (
    LanguageEvidence,
    letters,
    words,
)

ASCII_LETTERS: frozenset[str] = frozenset("abcdefghijklmnopqrstuvwxyz")
# Vietnamese letters with tone marks (Latin Extended Additional) and its
# unique base letters.
VIETNAMESE_LETTERS: frozenset[str] = frozenset(
    {chr(code) for code in range(0x1EA0, 0x1EFA) if chr(code).islower()}
    | {"đ", "ơ", "ư"}
)


LATIN_LANGUAGE_EVIDENCE: dict[str, LanguageEvidence] = {
    "en": LanguageEvidence(
        "Latn",
        ASCII_LETTERS,
        frozenset(),
        words(
            "the and is are you your i a an to for of in on at have has do does "
            "can could would what how when where hello hi hey please thanks "
            "thank table tomorrow today tonight my me we want book there much "
            "price open with it this that be will not no yes good great sure need "
            "like get here us our see then any some evening morning night people "
            "person booking reservation available address hours menu card pay"
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
        letters("œÿ"),
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
}
