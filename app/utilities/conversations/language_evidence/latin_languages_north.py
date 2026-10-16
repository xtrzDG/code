"""Evidence of the Nordic and Baltic languages written in the Latin script."""

from app.utilities.conversations.language_evidence.language_evidence import (
    LanguageEvidence,
    letters,
    words,
)
from app.utilities.conversations.language_evidence.latin_languages import (
    ASCII_LETTERS,
)

NORTH_LATIN_LANGUAGE_EVIDENCE: dict[str, LanguageEvidence] = {
    "da": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("æøå"),
        frozenset(),
        words(
            "og er at det en et til på med jeg vi hej goddag tak venligst gerne "
            "vil bord morgen dag hvor meget koster pris åbent kan personer "
            "klokken aften ikke har jeres"
        ),
    ),
    "nb": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("æøå"),
        frozenset(),
        words(
            "og er at det en et til på med jeg vi hei hallo takk vær så snill "
            "vil gjerne bestille bord morgen dag hvor mye koster pris åpent kan "
            "personer klokka kveld ikke har dere"
        ),
    ),
    "sv": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("åäö"),
        frozenset(),
        words(
            "och är att det en ett till på med jag vi hej hallå tack snälla vill "
            "gärna boka bord morgon idag hur mycket kostar pris öppet kan "
            "personer klockan kväll inte har ni"
        ),
    ),
    "fi": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("äöå"),
        frozenset(),
        words(
            "ja on ei se että hei moi terve kiitos kiitoksia haluaisin varata "
            "pöydän pöytä huomenna tänään paljonko paljonka maksaa hinta auki "
            "voinko onko henkilöä hengelle kello illalla"
        ),
    ),
    "et": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("äõöüšž"),
        letters("õ"),
        words(
            "ja on ei see et tere tänan aitäh palun soovin broneerida laua laud "
            "homme täna kui palju maksab hind avatud saab inimest inimesele kell "
            "õhtul"
        ),
    ),
    "lt": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("ąčęėįšųūž"),
        letters("ėįųū"),
        words(
            "ir yra ne kad su labas laba diena ačiū prašau norėčiau rezervuoti "
            "staliuką rytoj šiandien kiek kainuoja kaina atidaryta galima "
            "žmonėms valandą vakare"
        ),
    ),
    "lv": LanguageEvidence(
        "Latn",
        ASCII_LETTERS | letters("āčēģīķļņšūž"),
        letters("āēģīķļņ"),
        words(
            "un ir nav ka ar labdien sveiki paldies lūdzu vēlos rezervēt "
            "galdiņu galdu rīt šodien cik maksā cena atvērts var personām "
            "pulksten vakarā"
        ),
    ),
}
