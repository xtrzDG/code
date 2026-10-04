"""Keep abc order.

The texts of a breach notice (DPA section 12.1) are what the platform team
writes for the owners; each is one meaning of the notice, at most a few
paragraphs, with at least one visible character.
"""

from base_typed_string import BaseConstrainedTypedString


class BreachMeasuresText(BaseConstrainedTypedString):
    """
    The measures taken or proposed to address a data breach and to limit
    its effects (DPA section 12.1).

    Example:
        measures = BreachMeasuresText("The token was revoked within an hour.")
    """

    min_length = 1
    max_length = 2000
    pattern = r"\S"


class BreachNatureText(BaseConstrainedTypedString):
    """
    The nature of a personal data breach: what happened, when and how it
    was found (DPA section 12.1).

    Example:
        nature = BreachNatureText("A support export was sent to a wrong address.")
    """

    min_length = 1
    max_length = 2000
    pattern = r"\S"


class IncidentTitle(BaseConstrainedTypedString):
    """
    The short name of an incident in the platform's incident log and in
    the subject of its notices.

    Example:
        title = IncidentTitle("WhatsApp replies delayed")
    """

    min_length = 3
    max_length = 160
    pattern = r"^\S(.*\S)?\Z"


class LikelyConsequencesText(BaseConstrainedTypedString):
    """
    The likely consequences of a data breach for the people concerned
    (DPA section 12.1).

    Example:
        consequences = LikelyConsequencesText("Unwanted messages are possible.")
    """

    min_length = 1
    max_length = 2000
    pattern = r"\S"


class RecordCategoriesText(BaseConstrainedTypedString):
    """
    The categories of records a data breach concerns, e.g. "chat messages
    and phone numbers" (DPA section 12.1).

    Example:
        records = RecordCategoriesText("Chat messages and phone numbers")
    """

    min_length = 1
    max_length = 1000
    pattern = r"\S"


class SubjectCategoriesText(BaseConstrainedTypedString):
    """
    The categories of people a data breach concerns, e.g. "customers who
    wrote on WhatsApp in March" (DPA section 12.1).

    Example:
        subjects = SubjectCategoriesText("Customers who wrote on WhatsApp")
    """

    min_length = 1
    max_length = 1000
    pattern = r"\S"


# Keep abc order for all non example types, if possible.
