"""
Why one of the owner's checks did not pass, in the owner's words: what the
answer had to do, with the words it had to (not) say, in English, Russian
and Georgian. `{text}` stands for the check's expected text.
"""

from app.schemas.constants.assistants import AutotestExpectation
from app.schemas.dto.localization import LocalizedText
from app.utilities.knowledge.localized_texts import build_localized_text

TEXT_PLACEHOLDER: str = "{text}"

EXPECTATION_REASONS: dict[AutotestExpectation, LocalizedText] = {
    AutotestExpectation.MUST_MENTION: build_localized_text(
        en="The answer must mention “{text}”, and it did not.",
        ru="Ответ должен упомянуть «{text}», а не упомянул.",
        ka="პასუხში უნდა ყოფილიყო „{text}“, მაგრამ არ იყო.",
    ),
    AutotestExpectation.MUST_NOT_MENTION: build_localized_text(
        en="The answer must not mention “{text}”, and it did.",
        ru="Ответ не должен упоминать «{text}», а упомянул.",
        ka="პასუხში არ უნდა ყოფილიყო „{text}“, მაგრამ იყო.",
    ),
    AutotestExpectation.MUST_HAND_OFF: build_localized_text(
        en="The answer must pass the conversation to a person, and it did not.",
        ru="Ответ должен передать разговор человеку, а не передал.",
        ka="პასუხს საუბარი ადამიანისთვის უნდა გადაეცა, მაგრამ არ გადასცა.",
    ),
    AutotestExpectation.MUST_CREATE_LEAD: build_localized_text(
        en="The answer must take the customer's request, and no request was made.",
        ru="Ответ должен принять заявку клиента, а заявка не появилась.",
        ka="პასუხს კლიენტის მოთხოვნა უნდა მიეღო, მაგრამ მოთხოვნა არ შეიქმნა.",
    ),
}
# The check could not be played to the end (a provider error, no answer).
CHECK_NOT_PLAYED_REASON: LocalizedText = build_localized_text(
    en="The check could not run to the end. Try again in a few minutes.",
    ru="Проверку не удалось провести до конца. Попробуйте через несколько минут.",
    ka="შემოწმება ბოლომდე ვერ ჩატარდა. სცადეთ რამდენიმე წუთში.",
)


def fill_expected_text(template: str, expected_text: str | None) -> str:
    """The reason with the check's words in place of `{text}`."""

    return template.replace(TEXT_PLACEHOLDER, expected_text or "")
