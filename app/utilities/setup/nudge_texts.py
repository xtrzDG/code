"""
The activation nudges' texts in English, Russian and Georgian (`{name}` is
the business's name), the footer that says where to turn them off, and the
cabinet page each one opens.
"""

from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.nudges import NudgeTopic
from app.schemas.dto.localization import LocalizedText
from app.utilities.knowledge.localized_texts import build_localized_text

NUDGE_TITLES: dict[NudgeTopic, LocalizedText] = {
    NudgeTopic.FINISH_SETUP: build_localized_text(
        en="{name}: your assistant is almost ready",
        ru="{name}: помощник почти готов",
        ka="{name}: ასისტენტი თითქმის მზადაა",
    ),
    NudgeTopic.DONE_FOR_YOU: build_localized_text(
        en="{name}: shall we set it up for you?",
        ru="{name}: настроить помощника за вас?",
        ka="{name}: მოვარგოთ ასისტენტი თქვენ ნაცვლად?",
    ),
    NudgeTopic.CONNECT_CHANNEL: build_localized_text(
        en="{name}: where do your customers write?",
        ru="{name}: где пишут ваши клиенты?",
        ka="{name}: სად გწერენ თქვენი კლიენტები?",
    ),
    NudgeTopic.SHARE_LINK: build_localized_text(
        en="{name}: let customers find your assistant",
        ru="{name}: покажите помощника клиентам",
        ka="{name}: აჩვენეთ ასისტენტი კლიენტებს",
    ),
    NudgeTopic.PRINT_QR: build_localized_text(
        en="{name}: put the QR code where customers wait",
        ru="{name}: поставьте QR-код туда, где ждут клиенты",
        ka="{name}: განათავსეთ QR-კოდი იქ, სადაც კლიენტები ელოდებიან",
    ),
}

NUDGE_DETAILS: dict[NudgeTopic, LocalizedText] = {
    NudgeTopic.FINISH_SETUP: build_localized_text(
        en="Pick up where you left off: the rest takes about ten minutes, and "
        "the free trial starts only when the assistant goes live.",
        ru="Продолжите с того места, где остановились: осталось около десяти "
        "минут, а пробный период начнётся только после запуска.",
        ka="გააგრძელეთ იქიდან, სადაც შეჩერდით: დარჩა დაახლოებით ათი წუთი, "
        "საცდელი პერიოდი კი მხოლოდ გაშვების შემდეგ დაიწყება.",
    ),
    NudgeTopic.DONE_FOR_YOU: build_localized_text(
        en="Finish the setup yourself in a few minutes, or let our team do it: "
        "choose “Done for you” in Settings, Plan and billing.",
        ru="Завершите настройку сами за несколько минут или доверьте её нашей "
        "команде: выберите «Настроим за вас» в «Настройки → Тариф и оплата».",
        ka="დაასრულეთ მორგება თავად რამდენიმე წუთში ან მიანდეთ ჩვენს გუნდს: "
        "აირჩიეთ „ჩვენ მოვარგებთ“ — „პარამეტრები → ტარიფი და გადახდა“.",
    ),
    NudgeTopic.CONNECT_CHANNEL: build_localized_text(
        en="Your assistant answers in one channel so far. Connect WhatsApp, "
        "Telegram or Instagram: most customers write there.",
        ru="Пока помощник отвечает в одном канале. Подключите WhatsApp, "
        "Telegram или Instagram — большинство клиентов пишут там.",
        ka="ჯერჯერობით ასისტენტი ერთ არხში პასუხობს. დააკავშირეთ WhatsApp, "
        "Telegram ან Instagram — კლიენტების უმეტესობა იქ წერს.",
    ),
    NudgeTopic.SHARE_LINK: build_localized_text(
        en="Your assistant is live, and no customer has written yet. Share the "
        "chat link in your profile, on Google Maps or with regular customers.",
        ru="Помощник работает, но клиенты ещё не писали. Поделитесь ссылкой на "
        "чат в профиле, на Google Картах или с постоянными клиентами.",
        ka="ასისტენტი მუშაობს, მაგრამ კლიენტებს ჯერ არ მოუწერიათ. გააზიარეთ "
        "ჩატის ბმული პროფილში, Google Maps-ზე ან მუდმივ კლიენტებთან.",
    ),
    NudgeTopic.PRINT_QR: build_localized_text(
        en="Print the QR card for the counter, the tables or the door: "
        "customers scan it and write to your assistant at any hour.",
        ru="Распечатайте карточку с QR-кодом для стойки, столиков или двери: "
        "клиенты отсканируют её и напишут помощнику в любое время.",
        ka="ამობეჭდეთ QR-ბარათი დახლისთვის, მაგიდებისთვის ან კარისთვის: "
        "კლიენტები დაასკანერებენ და ასისტენტს ნებისმიერ დროს მისწერენ.",
    ),
}

NUDGE_FOOTER: LocalizedText = build_localized_text(
    en="You can turn these reminders off in Settings, Notifications.",
    ru="Отключить эти напоминания можно в «Настройки → Уведомления».",
    ka="ამ შეხსენებების გამორთვა შეგიძლიათ: „პარამეტრები → შეტყობინებები“.",
)

# The cabinet page each nudge's signed link opens.
NUDGE_TARGETS: dict[NudgeTopic, StaffLinkTarget] = {
    NudgeTopic.FINISH_SETUP: StaffLinkTarget.SETUP,
    NudgeTopic.DONE_FOR_YOU: StaffLinkTarget.BILLING,
    NudgeTopic.CONNECT_CHANNEL: StaffLinkTarget.CHANNELS,
    NudgeTopic.SHARE_LINK: StaffLinkTarget.SHARE,
    NudgeTopic.PRINT_QR: StaffLinkTarget.SHARE,
}
