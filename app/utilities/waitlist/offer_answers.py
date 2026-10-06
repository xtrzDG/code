"""
A customer's whole reply to an offered place read as yes or no, in the
languages the offer is written in. Only a short message that is nothing
but an answer counts ("yes", "Да!", "კი", "no thanks", "👍"); anything
longer is a sentence the assistant answers.
"""

from app.schemas.constants.waitlist import WaitlistAnswer
from app.utilities.channels.opt_out import normalize_command

# An answer is a few words at most.
MAX_ANSWER_LENGTH: int = 24

YES_WORDS: frozenset[str] = frozenset(
    {
        # en
        "yes",
        "yes please",
        "yeah",
        "yep",
        "yup",
        "sure",
        "ok",
        "okay",
        "i'll take it",
        "i will take it",
        "take it",
        "book it",
        "deal",
        "👍",
        "✅",
        "👌",
        # ru
        "да",
        "да, беру",
        "да беру",
        "беру",
        "давайте",
        "конечно",
        "хорошо",
        "ок",
        "ага",
        "согласен",
        "согласна",
        "да, конечно",
        # ka
        "კი",
        "დიახ",
        "ჰო",
        "კარგი",
        "თანახმა ვარ",
        "ki",
        "diax",
        "ho",
        # uk
        "так",
        "так, беру",
        "добре",
        "звісно",
        # hy
        "այո",
        "հա",
        "lav",
        "ayo",
        # az
        "bəli",
        "hə",
        "he",
        "beli",
        "olar",
        # kk
        "иә",
        "иа",
        "жарайды",
        # tr
        "evet",
        "tamam",
        "olur",
        # he
        "כן",
        "בטח",
        "סגור",
        # ar
        "نعم",
        "أجل",
        "اكيد",
        "أكيد",
        "تمام",
        # de
        "ja",
        "ja bitte",
        "gerne",
        "klar",
        # fr
        "oui",
        "d'accord",
        "ok merci",
        # es, it, pt
        "sí",
        "si",
        "claro",
        "vale",
        "sim",
        "certo",
        # pl
        "tak",
        "jasne",
    }
)

NO_WORDS: frozenset[str] = frozenset(
    {
        # en
        "no",
        "no thanks",
        "no thank you",
        "nope",
        "not now",
        "pass",
        "👎",
        "❌",
        # ru
        "нет",
        "нет, спасибо",
        "нет спасибо",
        "не надо",
        "не могу",
        "не получится",
        "неа",
        # ka
        "არა",
        "არა, მადლობა",
        "ara",
        # uk
        "ні",
        "ні, дякую",
        "не треба",
        # hy
        "ոչ",
        "չէ",
        "voch",
        # az
        "xeyr",
        "yox",
        # kk
        "жоқ",
        # tr
        "hayır",
        "hayir",
        "istemiyorum",
        # he
        "לא",
        "לא תודה",
        # ar
        "لا",
        "لا شكرا",
        "لا شكرًا",
        # de
        "nein",
        "nein danke",
        # fr
        "non",
        "non merci",
        # es, it, pt
        "no gracias",
        "no grazie",
        "não",
        "nao",
        "não obrigado",
        # pl
        "nie",
        "nie dziękuję",
    }
)


def read_offer_answer(text: str) -> WaitlistAnswer | None:
    """YES or NO for a message that is only an answer; None for anything else."""

    if len(text) > MAX_ANSWER_LENGTH * 2:
        return None

    answer: str = normalize_command(text)
    if answer == "" or len(answer) > MAX_ANSWER_LENGTH:
        return None

    if answer in YES_WORDS:
        return WaitlistAnswer.YES

    if answer in NO_WORDS:
        return WaitlistAnswer.NO

    return None
