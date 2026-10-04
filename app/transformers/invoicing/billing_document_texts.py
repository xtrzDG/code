"""
Texts of the invoice and receipt PDFs in English, Russian and Georgian
(other languages read English). Placeholders in braces are filled by the
layout. The VAT notes want an accountant's sign-off before VAT
registration (docs/LAUNCH.md).
"""

from app.schemas.constants.billing import InvoiceStatus
from app.schemas.constants.invoicing import TaxTreatment
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

INVOICE_TITLE = build_localized_text(en="Invoice", ru="Счёт", ka="ინვოისი")
RECEIPT_TITLE = build_localized_text(
    en="Payment receipt", ru="Квитанция об оплате", ka="გადახდის ქვითარი"
)
NUMBER = build_localized_text(en="No. {number}", ru="№ {number}", ka="№ {number}")
ISSUE_DATE = build_localized_text(
    en="Issue date", ru="Дата выставления", ka="გამოწერის თარიღი"
)
PAYMENT_DATE = build_localized_text(
    en="Payment date", ru="Дата оплаты", ka="გადახდის თარიღი"
)
SELLER = build_localized_text(en="Seller", ru="Исполнитель", ka="გამყიდველი")
BUYER = build_localized_text(en="Buyer", ru="Заказчик", ka="მყიდველი")
TAX_ID = build_localized_text(
    en="Tax number", ru="Налоговый номер", ka="საიდენტიფიკაციო ნომერი"
)
EMAIL = build_localized_text(en="E-mail", ru="Эл. почта", ka="ელ. ფოსტა")
DESCRIPTION = build_localized_text(en="Description", ru="Наименование", ka="დასახელება")
PERIOD = build_localized_text(en="Period", ru="Период", ka="პერიოდი")
AMOUNT = build_localized_text(en="Amount", ru="Сумма", ka="თანხა")
SUBTOTAL = build_localized_text(
    en="Subtotal excl. VAT", ru="Итого без НДС", ka="ჯამი დღგ-ის გარეშე"
)
VAT = build_localized_text(en="VAT {rate}", ru="НДС {rate}", ka="დღგ {rate}")
TOTAL_DUE = build_localized_text(
    en="Total due", ru="Итого к оплате", ka="სულ გადასახდელი"
)
TOTAL_PAID = build_localized_text(
    en="Total paid", ru="Итого оплачено", ka="სულ გადახდილი"
)
AMOUNT_RECEIVED = build_localized_text(
    en="Amount received", ru="Получено", ka="მიღებული თანხა"
)
RECEIPT_NUMBER = build_localized_text(
    en="For invoice No. {number}",
    ru="По счёту № {number}",
    ka="ინვოისი № {number}",
)
PAYMENT_METHOD = build_localized_text(
    en="Payment method", ru="Способ оплаты", ka="გადახდის საშუალება"
)
CARD_WITH_BRAND = build_localized_text(
    en="{brand} card ending in {digits}",
    ru="Карта {brand}, последние цифры {digits}",
    ka="ბარათი {brand}, ბოლო ციფრები {digits}",
)
CARD_WITHOUT_BRAND = build_localized_text(
    en="Card ending in {digits}",
    ru="Карта, последние цифры {digits}",
    ka="ბარათი, ბოლო ციფრები {digits}",
)
CARD_UNKNOWN = build_localized_text(
    en="Online card payment",
    ru="Оплата картой онлайн",
    ka="ონლაინ გადახდა ბარათით",
)
PAY_ONLINE = build_localized_text(
    en="Pay online in the cabinet: Settings → Plan and billing.",
    ru="Оплатите онлайн в кабинете: Настройки → Тариф и оплата.",
    ka="გადაიხადეთ ონლაინ კაბინეტში: პარამეტრები → ტარიფი და გადახდა.",
)
RECEIPT_THANKS = build_localized_text(
    en="Thank you. This receipt confirms the payment above.",
    ru="Спасибо! Квитанция подтверждает оплату, указанную выше.",
    ka="გმადლობთ. ეს ქვითარი ადასტურებს ზემოთ მითითებულ გადახდას.",
)
GENERATED_BY = build_localized_text(
    en="Generated electronically by {seller}.",
    ru="Документ сформирован электронно: {seller}.",
    ka="დოკუმენტი შექმნილია ელექტრონულად: {seller}.",
)

RECEIPT_EMAIL_SUBJECT = build_localized_text(
    en="Payment receipt for invoice {number}",
    ru="Квитанция об оплате по счёту № {number}",
    ka="გადახდის ქვითარი, ინვოისი № {number}",
)
RECEIPT_EMAIL_BODY = build_localized_text(
    en="{business}: we received {amount} on {date}. The invoice and the "
    "payment receipt are attached as PDF files for your accountant.",
    ru="{business}: оплата {amount} получена {date}. Счёт и квитанция об "
    "оплате приложены в PDF — их можно передать бухгалтеру.",
    ka="{business}: {amount} მიღებულია {date}. ინვოისი და გადახდის ქვითარი "
    "თან ერთვის PDF ფაილებად — შეგიძლიათ გადასცეთ ბუღალტერს.",
)
RECEIPT_EMAIL_HINT = build_localized_text(
    en="You can download them again in the cabinet: Settings → Plan and billing.",
    ru="Скачать их снова можно в кабинете: Настройки → Тариф и оплата.",
    ka="მათი ხელახლა ჩამოტვირთვა შეგიძლიათ კაბინეტში: პარამეტრები → ტარიფი და გადახდა.",
)

STATUS_NAMES: dict[InvoiceStatus, LocalizedText] = {
    InvoiceStatus.ISSUED: build_localized_text(
        en="Awaiting payment", ru="Ожидает оплаты", ka="ელოდება გადახდას"
    ),
    InvoiceStatus.PAID: build_localized_text(en="Paid", ru="Оплачен", ka="გადახდილია"),
    InvoiceStatus.FAILED: build_localized_text(
        en="Payment failed", ru="Оплата не прошла", ka="გადახდა ვერ შესრულდა"
    ),
    InvoiceStatus.VOID: build_localized_text(
        en="Cancelled", ru="Аннулирован", ka="გაუქმებულია"
    ),
}

TAX_NOTES: dict[TaxTreatment, LocalizedText] = {
    TaxTreatment.NOT_REGISTERED: build_localized_text(
        en="VAT is not charged: the seller is not registered for VAT.",
        ru="Без НДС: исполнитель не зарегистрирован плательщиком НДС.",
        ka="დღგ არ ერიცხება: გამყიდველი არ არის რეგისტრირებული დღგ-ის გადამხდელად.",
    ),
    TaxTreatment.STANDARD: build_localized_text(
        en="VAT is charged at {rate}.",
        ru="НДС начислен по ставке {rate}.",
        ka="დღგ დარიცხულია {rate} განაკვეთით.",
    ),
    TaxTreatment.REVERSE_CHARGE: build_localized_text(
        en="Reverse charge: VAT is to be accounted for by the recipient.",
        ru="Обратное начисление: НДС исчисляет и уплачивает получатель услуги.",
        ka="უკუდაბეგვრა: დღგ-ის გადახდის ვალდებულება ეკისრება მომსახურების მიმღებს.",
    ),
    TaxTreatment.OUTSIDE_SCOPE: build_localized_text(
        en="Not subject to VAT in {country}: the place of supply is outside "
        "the seller's country.",
        ru="Не облагается НДС страны исполнителя ({country}): место оказания "
        "услуг за её пределами.",
        ka="არ იბეგრება გამყიდველის ქვეყნის ({country}) დღგ-ით: მომსახურების "
        "გაწევის ადგილი მის ფარგლებს გარეთაა.",
    ),
}
