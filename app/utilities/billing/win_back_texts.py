"""
The win-back messages to owners who cancelled, in English, Russian and
Georgian: what the assistant did since (it kept taking requests), that
everything they set up is kept, and a way back. The second message adds a
line for the reason they gave.
"""

from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    WinBackStage,
)
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

WIN_BACK_TITLES: dict[WinBackStage, LocalizedText] = {
    WinBackStage.DAY_14: build_localized_text(
        en="{business}: your assistant is still here",
        ru="{business}: ваш ассистент всё ещё на месте",
        ka="{business}: თქვენი ასისტენტი ისევ აქ არის",
    ),
    WinBackStage.DAY_30: build_localized_text(
        en="{business}: a month without full service",
        ru="{business}: месяц без полного режима",
        ka="{business}: ერთი თვე სრული რეჟიმის გარეშე",
    ),
}
CONVERSATIONS_LINE: LocalizedText = build_localized_text(
    en="Since you cancelled, it has only been taking requests. Customers who "
    "wrote in that time: {count}.",
    ru="После отмены он только принимает заявки. Клиентов, написавших за это "
    "время: {count}.",
    ka="გაუქმების შემდეგ ის მხოლოდ მოთხოვნებს იღებს. ამ ხნის განმავლობაში "
    "მოგწერეს კლიენტებმა: {count}.",
)
KEPT_LINE: LocalizedText = build_localized_text(
    en="Your answers, prices and channels are all kept: full service is back "
    "as soon as you choose a plan in Billing.",
    ru="Ответы, цены и каналы сохранены: полный режим вернётся, как только вы "
    "выберете тариф в разделе «Тариф и счета».",
    ka="პასუხები, ფასები და არხები შენახულია: სრული რეჟიმი დაბრუნდება, "
    "როგორც კი აირჩევთ ტარიფს განყოფილებაში „ბილინგი“.",
)
PAUSE_HINT: LocalizedText = build_localized_text(
    en="Next time the season ends, you can pause for a share of the price "
    "instead of cancelling, and keep taking requests.",
    ru="В следующий раз, когда сезон закончится, можно поставить подписку на "
    "паузу за часть цены вместо отмены и продолжать принимать заявки.",
    ka="შემდეგ ჯერზე, როცა სეზონი დასრულდება, გაუქმების ნაცვლად შეგიძლიათ "
    "პაუზა ფასის ნაწილად და მოთხოვნების მიღება გააგრძელოთ.",
)
PRICE_HINT: LocalizedText = build_localized_text(
    en="Smaller plans cost less, and a seasonal pause costs a share of the price.",
    ru="Тарифы поменьше стоят дешевле, а сезонная пауза — лишь часть цены.",
    ka="მცირე ტარიფები უფრო იაფია, სეზონური პაუზა კი ფასის მხოლოდ ნაწილი ღირს.",
)
QUALITY_HINT: LocalizedText = build_localized_text(
    en="Tell us what the assistant got wrong: reply to this message, and the "
    "team will look at it with you.",
    ru="Расскажите, что ассистент делал не так: ответьте на это сообщение, и "
    "команда разберётся вместе с вами.",
    ka="მოგვწერეთ, რა ვერ გააკეთა ასისტენტმა კარგად: უპასუხეთ ამ "
    "შეტყობინებას და გუნდი თქვენთან ერთად გაარკვევს.",
)
REASON_HINTS: dict[CancellationReason, LocalizedText] = {
    CancellationReason.SEASONAL_BREAK: PAUSE_HINT,
    CancellationReason.NOT_ENOUGH_USE: PAUSE_HINT,
    CancellationReason.TOO_EXPENSIVE: PRICE_HINT,
    CancellationReason.ANSWER_QUALITY: QUALITY_HINT,
    CancellationReason.MISSING_FEATURE: QUALITY_HINT,
}
