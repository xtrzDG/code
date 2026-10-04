"""Evidence of Catalan and the Latin-script languages of central Europe."""

from app.utilities.conversations.language_evidence.language_evidence import (
    LanguageEvidence,
    letters,
    words,
)
from app.utilities.conversations.language_evidence.latin_languages import (
    ASCII_LETTERS,
)

CENTRAL_LATIN_LANGUAGE_EVIDENCE: dict[str, LanguageEvidence] = {
    "ca": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("àçèéíïòóúü·"),
        letters("·"),
        words(
            "els amb és per hola bon dia bona tarda nit gràcies si us plau "
            "voldria reservar taula demà avui quant costa preu obert puc "
            "persones hores tenim teniu podeu fins aquí molt"
        ),
    ),
    "cs": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("áčďéěíňóřšťúůýž"),
        letters("ěřů"),
        words(
            "a je to se na že s z do dobrý den večer ahoj děkuji děkuju prosím "
            "chtěl chtěla bych rezervovat stůl zítra dnes kolik stojí cena máte "
            "otevřeno můžu můžeme lidi osoby hodin pro nás"
        ),
    ),
    "sk": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("áäčďéíĺľňóôŕšťúýž"),
        letters("ĺľŕô"),
        words(
            "a je to sa na že s z do dobrý deň večer ahoj ďakujem prosím chcel "
            "chcela by som rezervovať stôl zajtra dnes koľko stojí cena máte "
            "otvorené môžem môžeme ľudí osoby hodín pre nás"
        ),
    ),
    "sl": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("čšž"),
        frozenset(),
        words(
            "in je to se na da s z za dober dan zdravo živjo pozdravljeni hvala "
            "prosim rad rada bi rezerviral rezervirala mizo jutri danes koliko "
            "stane cena imate odprto lahko oseb ure zvečer nas"
        ),
    ),
    "hr": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("čćđšž"),
        frozenset(),
        words(
            "i je to se na u da s sa za dobar dan bok pozdrav hvala molim htio "
            "htjela bih rezervirati stol sutra danas koliko košta cijena imate "
            "otvoreno mogu osobe sati večeras nas"
        ),
    ),
    "bs": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("čćđšž"),
        frozenset(),
        words(
            "i je to se na u da s sa za dobar dan zdravo selam hvala molim htio "
            "htjela bih rezervisati sto sutra danas koliko košta cijena imate "
            "otvoreno mogu osobe sati večeras nas"
        ),
    ),
    "hu": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("áéíóöőúüű"),
        letters("őű"),
        words(
            "a az és egy is nem van szia szervusz jó napot estét köszönöm "
            "kérem szeretnék asztalt foglalni holnap ma mennyibe kerül ár "
            "nyitva lehet fő főre órára este hány"
        ),
    ),
    "sq": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("çë"),
        letters("ë"),
        words(
            "dhe në një të është për me nga përshëndetje mirëdita faleminderit "
            "ju lutem dua tavolinë nesër sot sa kushton çmimi keni hapur mund "
            "persona ora darkë mbrëmje"
        ),
    ),
}
