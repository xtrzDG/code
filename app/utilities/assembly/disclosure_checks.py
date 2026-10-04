"""
Is the AI disclosure in the customer's language? A deterministic autotest
check: the platform, not the model, writes the disclosure, in the language
it read the customer's first message in.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AutotestCheckCode
from app.schemas.dto.assistants.autotest_runs import (
    AutotestCheckFailure,
    AutotestScenario,
)
from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.assistants.strings import AutotestCheckNote
from app.utilities.assembly.script_detection import is_written_in_script
from app.utilities.localization.language_tags import base_language_code


def check_disclosure_language(
    scenario: AutotestScenario,
    replies: Sequence[AssistantReply],
    business_name: str | None,
) -> list[AutotestCheckFailure]:
    """
    The first reply's disclosure is in the scenario language and its script
    (the business name, often Latin, is left out of the script check).
    Nothing to check when no reply carries a disclosure.
    """

    disclosed: AssistantReply | None = next(
        (reply for reply in replies if reply.disclosure_text is not None), None
    )
    if disclosed is None or disclosed.disclosure_text is None:
        return []

    own_words: str = str(disclosed.disclosure_text)
    if business_name:
        own_words = own_words.replace(business_name, " ")

    if base_language_code(disclosed.language) == base_language_code(
        scenario.language
    ) and (is_written_in_script(own_words, scenario.language_script) is not False):
        return []

    return [
        AutotestCheckFailure(
            code=AutotestCheckCode.WRONG_DISCLOSURE_LANGUAGE,
            note=AutotestCheckNote(
                f"The AI disclosure was given in {disclosed.language}, not in "
                f"{scenario.language_name} ({scenario.language})."
            ),
        )
    ]
