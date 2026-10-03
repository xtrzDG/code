"""
Owner-facing billing texts in English, Russian and Georgian.

Tax rule of the concept: invoices name a service ("call and message
handling service"), never a "license" or a "consultation". Placeholders in
braces are filled by the billing transformers.
"""

import re

from app.schemas.constants.billing import BillingNoticeKind, BillingPeriod
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import split_language_tag_text
from app.utilities.localization.localized_texts import build_localized_text

FALLBACK_LANGUAGE_TAG: LanguageTag = LanguageTag("en")
PLACEHOLDER_PATTERN: re.Pattern[str] = re.compile(r"\{([a-z_]+)\}")

SERVICE_NAME: LocalizedText = build_localized_text(
    en="Call and message handling service",
    ru="Услуга приёма и обработки обращений",
    ka="ზარებისა და შეტყობინებების მიღებისა და დამუშავების მომსახურება",
)
SETUP_FEE_LINE: LocalizedText = build_localized_text(
    en="{service} — setup",
    ru="{service} — подключение",
    ka="{service} — ჩართვა",
)
USAGE_OVERAGE_LINE: LocalizedText = build_localized_text(
    en="{service} — {minutes} call minutes above the package, {start} – {end}",
    ru="{service} — {minutes} мин. звонков сверх пакета, {start} – {end}",
    ka="{service} — პაკეტს ზემოთ {minutes} წუთი ზარი, {start} – {end}",
)
SERVICE_PERIOD_LINE: LocalizedText = build_localized_text(
    en="{service} — {plan}, {billing_period}, {start} – {end}",
    ru="{service} — {plan}, {billing_period}, {start} – {end}",
    ka="{service} — {plan}, {billing_period}, {start} – {end}",
)
BILLING_PERIOD_NAMES: dict[BillingPeriod, LocalizedText] = {
    BillingPeriod.MONTHLY: build_localized_text(
        en="monthly",
        ru="помесячно",
        ka="ყოველთვიური",
    ),
    BillingPeriod.ANNUAL: build_localized_text(
        en="annual",
        ru="за год",
        ka="წლიური",
    ),
}

NOTICE_TEXTS: dict[BillingNoticeKind, LocalizedText] = {
    BillingNoticeKind.PAYMENT_FAILED: build_localized_text(
        en="{business}: the payment of {amount} for the assistant did not go "
        "through. Please check the card and pay again in Billing.",
        ru="{business}: оплата {amount} за ассистента не прошла. Проверьте "
        "карту и оплатите снова в разделе «Тариф и счета».",
        ka="{business}: ასისტენტის გადახდა ({amount}) ვერ შესრულდა. გთხოვთ, "
        "შეამოწმოთ ბარათი და ხელახლა გადაიხადოთ განყოფილებაში „ბილინგი“.",
    ),
    BillingNoticeKind.TRIAL_ENDED_UNPAID: build_localized_text(
        en="{business}: the free trial has ended. Pay {amount} in Billing to "
        "keep the assistant working.",
        ru="{business}: бесплатный пробный период закончился. Оплатите "
        "{amount} в разделе «Тариф и счета», чтобы ассистент продолжал работу.",
        ka="{business}: უფასო საცდელი პერიოდი დასრულდა. ასისტენტის მუშაობის "
        "გასაგრძელებლად გადაიხადეთ {amount} განყოფილებაში „ბილინგი“.",
    ),
    BillingNoticeKind.RENEWAL_MISSED: build_localized_text(
        en="{business}: the payment of {amount} for the new period has not "
        "arrived. Please pay in Billing.",
        ru="{business}: оплата {amount} за новый период не поступила. "
        "Оплатите в разделе «Тариф и счета».",
        ka="{business}: ახალი პერიოდის გადახდა ({amount}) არ შემოსულა. "
        "გთხოვთ, გადაიხადოთ განყოფილებაში „ბილინგი“.",
    ),
    BillingNoticeKind.LEADS_ONLY_STARTED: build_localized_text(
        en="{business}: the subscription is unpaid, so the assistant now only "
        "takes requests and passes them to your team. Pay in Billing to "
        "restore full service.",
        ru="{business}: подписка не оплачена, поэтому ассистент теперь только "
        "принимает заявки и передаёт их команде. Оплатите в разделе «Тариф и "
        "счета», чтобы вернуть полный режим.",
        ka="{business}: გამოწერა გადაუხდელია, ამიტომ ასისტენტი ახლა მხოლოდ "
        "მოთხოვნებს იღებს და თქვენს გუნდს გადასცემს. სრული რეჟიმის "
        "აღსადგენად გადაიხადეთ განყოფილებაში „ბილინგი“.",
    ),
    BillingNoticeKind.OVERAGE_INVOICED: build_localized_text(
        en="{business}: calls went over the minutes in your plan last month. "
        "The bill for the extra minutes is {amount}; please pay it in Billing.",
        ru="{business}: в прошлом месяце звонки превысили минуты тарифа. Счёт "
        "за минуты сверх пакета — {amount}; оплатите его в разделе «Тариф и "
        "счета».",
        ka="{business}: გასულ თვეში ზარებმა ტარიფის წუთებს გადააჭარბა. "
        "პაკეტს ზემოთ წუთების ანგარიშია {amount}; გთხოვთ, გადაიხადოთ "
        "განყოფილებაში „ბილინგი“.",
    ),
    BillingNoticeKind.SUBSCRIPTION_ENDED: build_localized_text(
        en="{business}: the subscription has ended, so the assistant now only "
        "takes requests and passes them to your team. Resume the "
        "subscription in Billing to restore full service.",
        ru="{business}: подписка закончилась, поэтому ассистент теперь только "
        "принимает заявки и передаёт их команде. Возобновите подписку в "
        "разделе «Тариф и счета», чтобы вернуть полный режим.",
        ka="{business}: გამოწერა დასრულდა, ამიტომ ასისტენტი ახლა მხოლოდ "
        "მოთხოვნებს იღებს და თქვენს გუნდს გადასცემს. სრული რეჟიმის "
        "აღსადგენად განაახლეთ გამოწერა განყოფილებაში „ბილინგი“.",
    ),
}
FULL_SERVICE_DEADLINE: LocalizedText = build_localized_text(
    en=" The assistant keeps full service until {date}; after that it will "
    "only take requests.",
    ru=" Ассистент работает в полном режиме до {date}, потом будет только "
    "принимать заявки.",
    ka=" ასისტენტი სრულ რეჟიმში იმუშავებს ამ თარიღამდე: {date}; შემდეგ კი "
    "მხოლოდ მოთხოვნებს მიიღებს.",
)
VOICE_MINUTES_WARNING: LocalizedText = build_localized_text(
    en="{business}: {percent}% of the call minutes in your plan are used this "
    "period ({used} of {included}). Minutes above the package cost {price} "
    "each.",
    ru="{business}: в этом периоде использовано {percent}% минут звонков из "
    "тарифа ({used} из {included}). Минуты сверх пакета стоят {price} за "
    "минуту.",
    ka="{business}: ამ პერიოდში გამოყენებულია ტარიფის ზარის წუთების "
    "{percent}% ({used} / {included}). პაკეტს ზემოთ ყოველი წუთი ღირს {price}.",
)
DIALOGS_WARNING: LocalizedText = build_localized_text(
    en="{business}: {percent}% of the dialogs in your plan are used this "
    "period ({used} of {included}). If they run short, choose a larger plan "
    "in Billing.",
    ru="{business}: в этом периоде использовано {percent}% диалогов из тарифа "
    "({used} из {included}). Если диалогов не хватает, выберите тариф больше "
    "в разделе «Тариф и счета».",
    ka="{business}: ამ პერიოდში გამოყენებულია ტარიფის დიალოგების {percent}% "
    "({used} / {included}). თუ დიალოგები არ გეყოფათ, აირჩიეთ უფრო დიდი "
    "ტარიფი განყოფილებაში „ბილინგი“.",
)


def select_text_language(
    text: LocalizedText,
    requested_language: LanguageTag,
) -> LanguageTag:
    """
    Language the text will actually be shown in: the requested one when the
    text has its base language, English otherwise. Numbers and dates are
    formatted in the same language, so a sentence never mixes conventions.
    """

    requested_base: str = split_language_tag_text(str(requested_language)).language
    for value_language in text.values:
        if split_language_tag_text(str(value_language)).language == requested_base:
            return requested_language

    return FALLBACK_LANGUAGE_TAG


def fill_placeholders(template: str, values: dict[str, str]) -> str:
    """Replace {name} placeholders in one pass (values are never re-read)."""

    return PLACEHOLDER_PATTERN.sub(
        lambda match: values.get(match.group(1), match.group(0)),
        template,
    )
