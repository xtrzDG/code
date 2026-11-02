"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class FactKey(BaseConstrainedTypedString):
    """
    Snake-case key of one business fact, e.g. "opening_hours".

    Example:
        key = FactKey("parking")
    """

    min_length = 2
    max_length = 64
    pattern = r"^[a-z][a-z0-9_]*$"


class OwnerRuleInstruction(BaseConstrainedTypedString):
    """
    One case the owner wants handed to staff, or one thing the assistant
    must never do, as checked on save: 1 to 300 characters on one line, no
    spaces at either end, no "#" at the start, no control or invisible
    characters and none of < > [ ] { } `, so it can never pose as a
    section, a platform line or a fence of the instruction it joins.

    Example:
        rule = OwnerRuleInstruction("Banquets of more than 20 guests")
    """

    min_length = 1
    max_length = 300
    # Invisible: the characters `CustomerGivenName` refuses (controls, soft
    # hyphen, zero-width, direction and format marks, tag letters).
    pattern = (
        r"^[^\s#<>\[\]{}`\x00-\x1f\x7f-\x9f\u00ad\u061c\u180e\u200b-\u200f"
        r"\u2028-\u202e\u2060-\u206f\ufeff\ufff9-\ufffb\U000e0000-\U000e007f]"
        r"(?:[^<>\[\]{}`\x00-\x1f\x7f-\x9f\u00ad\u061c\u180e\u200b-\u200f"
        r"\u2028-\u202e\u2060-\u206f\ufeff\ufff9-\ufffb\U000e0000-\U000e007f]{0,298}"
        r"[^\s<>\[\]{}`\x00-\x1f\x7f-\x9f\u00ad\u061c\u180e\u200b-\u200f"
        r"\u2028-\u202e\u2060-\u206f\ufeff\ufff9-\ufffb\U000e0000-\U000e007f])?\Z"
    )


class OwnerToneInstruction(BaseConstrainedTypedString):
    """
    The tone the owner wants the assistant to keep, as checked on save: 1
    to 200 characters on one line, with the limits of an
    `OwnerRuleInstruction`.

    Example:
        tone = OwnerToneInstruction("Warm and brief, address guests formally")
    """

    min_length = 1
    max_length = 200
    pattern = (
        r"^[^\s#<>\[\]{}`\x00-\x1f\x7f-\x9f\u00ad\u061c\u180e\u200b-\u200f"
        r"\u2028-\u202e\u2060-\u206f\ufeff\ufff9-\ufffb\U000e0000-\U000e007f]"
        r"(?:[^<>\[\]{}`\x00-\x1f\x7f-\x9f\u00ad\u061c\u180e\u200b-\u200f"
        r"\u2028-\u202e\u2060-\u206f\ufeff\ufff9-\ufffb\U000e0000-\U000e007f]{0,198}"
        r"[^\s<>\[\]{}`\x00-\x1f\x7f-\x9f\u00ad\u061c\u180e\u200b-\u200f"
        r"\u2028-\u202e\u2060-\u206f\ufeff\ufff9-\ufffb\U000e0000-\U000e007f])?\Z"
    )


class QuestionChoiceKey(BaseConstrainedTypedString):
    """Snake-case key of one predefined answer choice."""

    min_length = 1
    max_length = 64
    pattern = r"^[a-z0-9][a-z0-9_]*$"


class QuestionKey(BaseConstrainedTypedString):
    """
    Snake-case key of one niche-specific profile question.

    Example:
        key = QuestionKey("live_music")
    """

    min_length = 2
    max_length = 64
    pattern = r"^[a-z][a-z0-9_]*$"


# Keep abc order for all non example types, if possible.
