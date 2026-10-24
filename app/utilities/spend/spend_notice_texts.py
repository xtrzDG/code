"""
What the owners and the platform team hear when a business passes one of
its daily spend limits. `{business}`, `{spend}` and `{limit}` are filled in
(`compose_owner_notice`, `compose_team_notice`); amounts are US dollars,
the currency providers bill in.
"""

import re
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.constants.spend import SpendLevel
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.spend_guard import SpendLimitPassing
from app.utilities.localization.localized_texts import build_localized_text

MICRO_USD_PER_CENT: int = 10_000
PLACEHOLDER_PATTERN: re.Pattern[str] = re.compile(r"\{(business|spend|limit|day)\}")

SOFT_LIMIT_OWNER_NOTICE: LocalizedText = build_localized_text(
    en="{business}: today's AI and call costs reached {spend}, past the daily "
    "level of {limit} where the assistant saves. Until midnight it answers "
    "on a lighter model; customers are still answered. If today is unusually "
    "busy on purpose, nothing is needed; if not, look at today's "
    "conversations in the inbox.",
    ru="{business}: расходы на ИИ и звонки сегодня достигли {spend} — больше "
    "дневного порога экономии {limit}. До полуночи ассистент отвечает на "
    "облегчённой модели; клиенты по-прежнему получают ответы. Если сегодня "
    "так и задумано, ничего делать не нужно; если нет — посмотрите сегодняшние "
    "разговоры во входящих.",
    ka="{business}: დღეს ხელოვნური ინტელექტისა და ზარების ხარჯმა {spend} "
    "მიაღწია — ეს აღემატება ეკონომიის დღიურ ზღვარს ({limit}). შუაღამემდე "
    "ასისტენტი უფრო მსუბუქ მოდელზე პასუხობს; კლიენტები პასუხს კვლავ იღებენ. "
    "თუ დღეს დატვირთვა განზრახ მაღალია, არაფერია საჭირო; თუ არა, ნახეთ "
    "დღევანდელი საუბრები შემოსულებში.",
)
HARD_LIMIT_OWNER_NOTICE: LocalizedText = build_localized_text(
    en="{business}: today's AI and call costs reached {spend}, the daily limit "
    "of {limit}. Until midnight the assistant no longer answers by itself: "
    "new messages wait for your team in the inbox, and calls are not taken "
    "by the voice assistant. Please answer customers from the inbox. If you "
    "expected this much traffic, ask support to raise the limit.",
    ru="{business}: расходы на ИИ и звонки сегодня достигли {spend} — это "
    "дневной лимит {limit}. До полуночи ассистент больше не отвечает сам: "
    "новые сообщения ждут вашу команду во входящих, а голосовой ассистент не "
    "принимает звонки. Пожалуйста, отвечайте клиентам из входящих. Если вы "
    "ждали такой поток, попросите поддержку поднять лимит.",
    ka="{business}: დღეს ხელოვნური ინტელექტისა და ზარების ხარჯმა {spend} "
    "მიაღწია — ეს დღიური ლიმიტია ({limit}). შუაღამემდე ასისტენტი თავად აღარ "
    "პასუხობს: ახალი შეტყობინებები თქვენს გუნდს შემოსულებში ელოდება, ხმოვანი "
    "ასისტენტი კი ზარებს არ იღებს. გთხოვთ, კლიენტებს შემოსულებიდან უპასუხოთ. "
    "თუ ასეთ დატვირთვას ელოდით, სთხოვეთ მხარდაჭერას ლიმიტის გაზრდა.",
)
OWNER_NOTICES: dict[SpendLevel, LocalizedText] = {
    SpendLevel.SOFT_LIMIT: SOFT_LIMIT_OWNER_NOTICE,
    SpendLevel.HARD_LIMIT: HARD_LIMIT_OWNER_NOTICE,
}
TEAM_NOTICES: dict[SpendLevel, str] = {
    SpendLevel.SOFT_LIMIT: (
        "Spend guard: {business} passed its soft daily limit ({spend} of "
        "{limit}) on {day}; it answers on the cheaper model until its midnight."
    ),
    SpendLevel.HARD_LIMIT: (
        "Spend guard: {business} reached its hard daily limit ({spend} of "
        "{limit}) on {day}; it only takes messages for its team until its "
        "midnight. Runbook: docs/operations/runbooks/spend-spike.md"
    ),
}


def describe_usd(micro_usd: int) -> str:
    """$12.40: dollars and cents, rounded half up."""

    cents: Decimal = (Decimal(micro_usd) / MICRO_USD_PER_CENT).quantize(
        Decimal(1), rounding=ROUND_HALF_UP
    )
    return f"${int(cents) // 100}.{int(cents) % 100:02d}"


def fill_notice(template: str, passing: SpendLimitPassing) -> str:
    """
    The notice with the business, the spend, the limit and the day, filled
    in one pass (a business name holding "{spend}" stays as written).
    """

    values: dict[str, str] = {
        "business": str(passing.business.name),
        "spend": describe_usd(int(passing.spend_micro_usd)),
        "limit": describe_usd(int(passing.limit_micro_usd)),
        "day": str(passing.day),
    }
    return PLACEHOLDER_PATTERN.sub(lambda match: values[match.group(1)], template)
