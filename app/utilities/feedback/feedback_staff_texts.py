"""
The summary of the handoff a low visit rating opens, in the business's
staff language (like a summary the assistant writes): the rating and the
customer's own words.
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

LOW_RATING_SUMMARY: LocalizedText = build_localized_text(
    en=(
        "The customer rated their visit {score} out of 5 in reply to the "
        "feedback request. They wrote: “{words}”. Get in touch and put it right."
    ),
    ru=(
        "Клиент оценил визит на {score} из 5 в ответ на просьбу об отзыве. "
        "Он написал: «{words}». Свяжитесь с ним и помогите исправить ситуацию."
    ),
    ka=(
        "კლიენტმა ვიზიტი შეაფასა {score}-ით 5-დან შეფასების თხოვნის პასუხად. "
        "მან დაწერა: „{words}“. დაუკავშირდით და გამოასწორეთ ვითარება."
    ),
    uk=(
        "Клієнт оцінив візит на {score} з 5 у відповідь на прохання про відгук. "
        "Він написав: «{words}». Зв'яжіться з ним і допоможіть виправити ситуацію."
    ),
)
