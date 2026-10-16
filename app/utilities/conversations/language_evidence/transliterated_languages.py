"""
Languages customers often type in Latin letters on a phone without their
own keyboard: Georgian ("gamarjoba, xval magida mchirdeba"), Russian
("privet, mozhno stolik"), Ukrainian, Armenian and Hebrew.

Each lexicon holds the common spellings of the words of a first message to
a business (greetings, thanks, "can I", "table", "tomorrow", "how much",
"people") and of everyday chat words. Words that are also English, or very
frequent words of another Latin-script language, are left out so that they
cannot turn an English message into Georgian.
"""

from app.utilities.conversations.language_evidence.language_evidence import (
    LanguageEvidence,
    words,
)

TRANSLITERATED_SCRIPT: str = "Latn"

TRANSLITERATED_LANGUAGE_EVIDENCE: dict[str, LanguageEvidence] = {
    "ka": LanguageEvidence(
        TRANSLITERATED_SCRIPT,
        None,
        frozenset(),
        words(
            "gamarjoba gamarjobat gaumarjos salami madloba madlobt gmadlobt "
            "gmadlob didi dzalian rogor rogora xar khar xart kargad kargi "
            "kai kaia diax ki ara minda mindoda mchirdeba mchirdeboda "
            "sheidzleba shegidzliat shemidzlia shegvidzlia magida "
            "magidas magidis magidebi dajavshna davajavshno javshani "
            "javshna xval khval xvale dges dghes zeg saghamos sagamos dilit "
            "ramdeni ramdenia ghirs girs pasi fasi sadaa ra aris ar aris "
            "gaqvt gakvt gaqvs gakvs kaci kacze kacistvis kacisatvis "
            "adamiani adamianze ori sami otxi otkhi xuti saati saatze "
            "gtxovt gthxovt mogesalmebit nakhvamdis naxvamdis momeci "
            "mogvwerot gavige gasagebia shemdeg rodis gixsnit gaxsnili "
            "dakhurulia daxurulia mainc ertad chven tqven tkven "
        ),
    ),
    "ru": LanguageEvidence(
        TRANSLITERATED_SCRIPT,
        None,
        frozenset(),
        words(
            "privet privetik zdravstvuyte zdravstvuite zdrastvuyte "
            "zdrastvuite zdravstvujte dobriy dobryy dobryi dobrij dobroe "
            "dobrogo vecher vechera utro spasibo spasiba pozhaluysta "
            "pozhalujsta pojaluysta pozhalusta mozhno mojno hochu khochu "
            "hoteli khoteli stolik stol zabronirovat zabronirujte "
            "bron bronirovat zavtra segodnya sevodnya sejchas seychas "
            "skolko stoit stoyat tsena yest vas mne nam "
            "dvoih dvoikh troih troikh chetveryh chelovek cheloveka "
            "vecherom utrom dnem kogda gde kak chto shto eto horosho "
            "khorosho ladno davayte davaite konechno netu tolko ili "
            "budet mojete mozhete podskazhite skazhite "
        ),
    ),
    "uk": LanguageEvidence(
        TRANSLITERATED_SCRIPT,
        None,
        frozenset(),
        words(
            "pryvit vitayu vitaju dobryi dobrogo dyakuyu diakuiu dyakuju "
            "bud laska khochu hochu stolyk zabronyuvaty zavtra sohodni "
            "skilky skilki koshtuye koshtuie mozhna meni nam dlya "
            "dvokh dvoh lyudey osib vvecheri shcho shho "
        ),
    ),
    "hy": LanguageEvidence(
        TRANSLITERATED_SCRIPT,
        None,
        frozenset(),
        words(
            "barev barevdzez dzez shnorhakalutyun shnorakalutyun "
            "shnorhakalut inchpes vonc vonts vortegh vortex "
            "uzum uzumem kuzei seghan sexan sexanik seghanik amragrel "
            "vaghy vaxy vaghe aysor aisor qani kani arje arzhe arji "
            "ginn chka ka ayo voch lav lavem shat hajox hajogh "
        ),
    ),
    "he": LanguageEvidence(
        TRANSLITERATED_SCRIPT,
        None,
        frozenset(),
        words(
            "shalom toda todah raba bevakasha bevakashah beseder ken yesh "
            "makom mekomot shulchan shulhan machar mahar hayom kama "
            "ole oleh rotze rotza rotse rotsa ani anachnu lehazmin "
            "hazmana slicha sliha erev boker tov lehitraot shnayim "
            "shtayim arba anashim "
        ),
    ),
}
