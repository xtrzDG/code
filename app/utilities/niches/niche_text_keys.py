"""
The keys of a niche template's owner-facing texts.

A template text lives in the owner text catalog under
`niches.<niche>.<field>` (`app/registries/localization/texts/`), and its
field key is the `<field>` part ("questions.cuisine.label"); the starter
answers, written in code, have field keys under `starters.`. The longest
wording of each kind is what the profile or the knowledge base accepts
where the text ends up (a handoff rule, a tone, a knowledge item's title).
"""

from app.schemas.constants.niches import NicheKey
from app.schemas.typings.niches.constrained_integers import NicheTextLengthLimit
from app.schemas.typings.niches.constrained_strings import NicheTextFieldKey
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey,
    QuestionKey,
)
from app.schemas.typings.setup.constrained_strings import StarterEntryKey

NICHE_TEXT_AREA: str = "niches"
STARTERS: str = "starters"
QUESTIONS: str = "questions"
CHOICES: str = "choices"
HANDOFF_RULES: str = "handoff_rules"
FORBIDDEN_RULES: str = "forbidden_rules"
# The platform's forbidden rules, which every niche's list starts with.
COMMON_FORBIDDEN_RULES: str = f"{NICHE_TEXT_AREA}.common.{FORBIDDEN_RULES}"

NAME_FIELD: NicheTextFieldKey = NicheTextFieldKey("name")
DESCRIPTION_FIELD: NicheTextFieldKey = NicheTextFieldKey("description")
RESOURCE_NOUN_FIELD: NicheTextFieldKey = NicheTextFieldKey("resource_noun")
TONE_FIELD: NicheTextFieldKey = NicheTextFieldKey(f"{STARTERS}.tone")
CANCELLATION_POLICY_FIELD: NicheTextFieldKey = NicheTextFieldKey(
    f"{STARTERS}.cancellation_policy"
)
RESOURCE_NAME_FIELD: NicheTextFieldKey = NicheTextFieldKey(f"{STARTERS}.resource_name")

NAME_LIMIT: NicheTextLengthLimit = NicheTextLengthLimit(80)
DESCRIPTION_LIMIT: NicheTextLengthLimit = NicheTextLengthLimit(400)
RESOURCE_NOUN_LIMIT: NicheTextLengthLimit = NicheTextLengthLimit(60)
LABEL_LIMIT: NicheTextLengthLimit = NicheTextLengthLimit(200)
HINT_LIMIT: NicheTextLengthLimit = NicheTextLengthLimit(400)
CHOICE_LIMIT: NicheTextLengthLimit = NicheTextLengthLimit(120)
# MAX_RULE_LENGTH and MAX_TONE_LENGTH of the profile's sections.
RULE_LIMIT: NicheTextLengthLimit = NicheTextLengthLimit(300)
TONE_LIMIT: NicheTextLengthLimit = NicheTextLengthLimit(200)
CANCELLATION_POLICY_LIMIT: NicheTextLengthLimit = NicheTextLengthLimit(500)
# MAX_RESOURCE_NAME_LENGTH of a resource; a knowledge item's title.
RESOURCE_NAME_LIMIT: NicheTextLengthLimit = NicheTextLengthLimit(120)
FAQ_QUESTION_LIMIT: NicheTextLengthLimit = NicheTextLengthLimit(300)
FAQ_ANSWER_LIMIT: NicheTextLengthLimit = NicheTextLengthLimit(1000)
OFFER_TITLE_LIMIT: NicheTextLengthLimit = NicheTextLengthLimit(200)


def niche_text_key(niche: NicheKey, *path: str) -> str:
    """The catalog key of a niche text: `niches.<niche>.<path...>`."""

    return ".".join((NICHE_TEXT_AREA, niche.value, *path))


def catalog_key_of(niche: NicheKey, field_key: NicheTextFieldKey) -> str:
    """The catalog key a template field's code text is read from."""

    return niche_text_key(niche, str(field_key))


def label_field(question: QuestionKey) -> NicheTextFieldKey:
    return NicheTextFieldKey(f"{QUESTIONS}.{question}.label")


def hint_field(question: QuestionKey) -> NicheTextFieldKey:
    return NicheTextFieldKey(f"{QUESTIONS}.{question}.hint")


def choice_field(question: QuestionKey, choice: QuestionChoiceKey) -> NicheTextFieldKey:
    return NicheTextFieldKey(f"{QUESTIONS}.{question}.{CHOICES}.{choice}")


def rule_field(rules: str, position: int) -> NicheTextFieldKey:
    """Line `position` (from 1) of the niche's handoff or forbidden rules."""

    return NicheTextFieldKey(f"{rules}.{position}")


def faq_question_field(entry: StarterEntryKey) -> NicheTextFieldKey:
    return NicheTextFieldKey(f"{STARTERS}.faq.{entry}.question")


def faq_answer_field(entry: StarterEntryKey) -> NicheTextFieldKey:
    return NicheTextFieldKey(f"{STARTERS}.faq.{entry}.answer")


def offer_title_field(entry: StarterEntryKey) -> NicheTextFieldKey:
    return NicheTextFieldKey(f"{STARTERS}.offers.{entry}.title")
