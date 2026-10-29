"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class NicheOverrideText(BaseConstrainedTypedString):
    """
    A platform admin's wording of one owner-facing text of a niche template
    in one language (a question's label, a choice, a starter answer): one
    line, without spaces around it and without anything that looks like an
    HTML tag. Each field has a shorter limit of its own
    (`NicheTextFieldView.max_length`).

    Example:
        text = NicheOverrideText("Какая у вас кухня?")
    """

    min_length = 1
    max_length = 1000
    pattern = r"^(?![\s\S]*<\s*[A-Za-z/!?])[^\s<][^\r\n]*(?<=\S)\Z"


class NicheTextFieldKey(BaseConstrainedTypedString):
    """
    Which owner-facing text of a niche template an override replaces:
    dotted lower-case segments, the template's own text keys
    ("questions.cuisine.label", "handoff_rules.2", "name") and its starter
    answers ("starters.faq.parking.question", "starters.tone").

    Example:
        field = NicheTextFieldKey("questions.cuisine.label")
    """

    min_length = 2
    max_length = 160
    pattern = r"^[a-z0-9_]+(\.[a-z0-9_]+){0,5}$"


# Keep abc order for all non example types, if possible.
