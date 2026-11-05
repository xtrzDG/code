"""
The payment line the platform adds under the assistant's reply when it
asks a deposit, in the customer's language: the amount, the owner's
payment link on a line of its own, until when the place (or the link)
holds, and the reference to pay under. The model never writes it, so it
can change neither the amount nor the link.

Placeholders: {amount} the money in the customer's language, {link} the
link, {until} the end of the hold in the business's time, {reference}.
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

DEPOSIT_BOOKING_LINE: LocalizedText = build_localized_text(
    en="To confirm your booking, please pay a deposit of {amount}: {link}\n"
    "We are holding your place until {until}. Payment reference: {reference}.",
    ru="Чтобы подтвердить бронь, внесите, пожалуйста, депозит {amount}: {link}\n"
    "Мы держим для вас место до {until}. Назначение платежа: {reference}.",
    ka="ჯავშნის დასადასტურებლად, გთხოვთ, გადაიხადოთ დეპოზიტი {amount}: {link}\n"
    "ადგილს თქვენთვის {until}-მდე ვინახავთ. გადახდის კოდი: {reference}.",
    uk="Щоб підтвердити бронювання, будь ласка, внесіть депозит {amount}: {link}\n"
    "Ми тримаємо для вас місце до {until}. Призначення платежу: {reference}.",
    hy="Ամրագրումը հաստատելու համար խնդրում ենք վճարել {amount} կանխավճար՝ {link}\n"
    "Տեղը Ձեզ համար պահում ենք մինչև {until}։ Վճարման կոդ՝ {reference}։",
    az="Rezervasiyanı təsdiqləmək üçün zəhmət olmasa {amount} depozit ödəyin: "
    "{link}\nYerinizi {until}-dək saxlayırıq. Ödəniş kodu: {reference}.",
    kk="Брондауды растау үшін {amount} депозит төлеуіңізді сұраймыз: {link}\n"
    "Орныңызды {until} дейін сақтаймыз. Төлем коды: {reference}.",
    tr="Rezervasyonunuzu onaylamak için lütfen {amount} tutarında kapora ödeyin: "
    "{link}\nYerinizi şu zamana kadar tutuyoruz: {until}. Ödeme referansı: "
    "{reference}.",
    he="כדי לאשר את ההזמנה, נא לשלם פיקדון של {amount}: {link}\n"
    "אנחנו שומרים עבורכם את המקום עד {until}. אסמכתה לתשלום: {reference}.",
    ar="لتأكيد حجزكم، يرجى دفع عربون بقيمة {amount}: {link}\n"
    "نحتفظ لكم بالمكان حتى {until}. مرجع الدفع: {reference}.",
    de="Um Ihre Buchung zu bestätigen, zahlen Sie bitte eine Anzahlung von "
    "{amount}: {link}\nWir halten Ihren Platz bis {until} frei. "
    "Zahlungsreferenz: {reference}.",
    fr="Pour confirmer votre réservation, merci de régler un acompte de "
    "{amount} : {link}\nNous vous gardons la place jusqu'à {until}. "
    "Référence de paiement : {reference}.",
    es="Para confirmar su reserva, abone por favor un depósito de {amount}: "
    "{link}\nLe guardamos el lugar hasta {until}. Referencia de pago: "
    "{reference}.",
    it="Per confermare la prenotazione, la preghiamo di versare un acconto di "
    "{amount}: {link}\nLe teniamo il posto fino a {until}. Riferimento di "
    "pagamento: {reference}.",
    pt="Para confirmar a sua reserva, pague por favor um sinal de {amount}: "
    "{link}\nGuardamos o seu lugar até {until}. Referência de pagamento: "
    "{reference}.",
    pl="Aby potwierdzić rezerwację, prosimy o wpłatę zaliczki w wysokości "
    "{amount}: {link}\nTrzymamy dla Państwa miejsce do {until}. Tytuł "
    "płatności: {reference}.",
)

DEPOSIT_BANQUET_LINE: LocalizedText = build_localized_text(
    en="To secure your banquet request, please pay a deposit of {amount}: "
    "{link}\nThe link is valid until {until}. Payment reference: {reference}.",
    ru="Чтобы закрепить заявку на банкет, внесите, пожалуйста, депозит "
    "{amount}: {link}\nСсылка действует до {until}. Назначение платежа: "
    "{reference}.",
    ka="ბანკეტის მოთხოვნის დასამაგრებლად, გთხოვთ, გადაიხადოთ დეპოზიტი "
    "{amount}: {link}\nბმული მოქმედებს {until}-მდე. გადახდის კოდი: {reference}.",
    uk="Щоб закріпити заявку на банкет, будь ласка, внесіть депозит {amount}: "
    "{link}\nПосилання діє до {until}. Призначення платежу: {reference}.",
    hy="Բանկետի հայտն ամրագրելու համար խնդրում ենք վճարել {amount} "
    "կանխավճար՝ {link}\nՀղումը գործում է մինչև {until}։ Վճարման կոդ՝ "
    "{reference}։",
    az="Banket sorğunuzu təsdiqləmək üçün zəhmət olmasa {amount} depozit "
    "ödəyin: {link}\nKeçid {until}-dək etibarlıdır. Ödəniş kodu: {reference}.",
    kk="Банкетке өтінімді бекіту үшін {amount} депозит төлеуіңізді сұраймыз: "
    "{link}\nСілтеме {until} дейін жарамды. Төлем коды: {reference}.",
    tr="Ziyafet talebinizi kesinleştirmek için lütfen {amount} tutarında kapora "
    "ödeyin: {link}\nBağlantı şu zamana kadar geçerlidir: {until}. Ödeme "
    "referansı: {reference}.",
    he="כדי להבטיח את בקשת האירוע, נא לשלם פיקדון של {amount}: {link}\n"
    "הקישור בתוקף עד {until}. אסמכתה לתשלום: {reference}.",
    ar="لتثبيت طلب المأدبة، يرجى دفع عربون بقيمة {amount}: {link}\n"
    "الرابط صالح حتى {until}. مرجع الدفع: {reference}.",
    de="Um Ihre Bankettanfrage zu sichern, zahlen Sie bitte eine Anzahlung von "
    "{amount}: {link}\nDer Link ist bis {until} gültig. Zahlungsreferenz: "
    "{reference}.",
    fr="Pour confirmer votre demande de banquet, merci de régler un acompte de "
    "{amount} : {link}\nLe lien est valable jusqu'à {until}. Référence de "
    "paiement : {reference}.",
    es="Para asegurar su solicitud de banquete, abone por favor un depósito de "
    "{amount}: {link}\nEl enlace es válido hasta {until}. Referencia de pago: "
    "{reference}.",
    it="Per confermare la richiesta di banchetto, la preghiamo di versare un "
    "acconto di {amount}: {link}\nIl link è valido fino a {until}. "
    "Riferimento di pagamento: {reference}.",
    pt="Para garantir o seu pedido de banquete, pague por favor um sinal de "
    "{amount}: {link}\nO link é válido até {until}. Referência de pagamento: "
    "{reference}.",
    pl="Aby potwierdzić zapytanie o bankiet, prosimy o wpłatę zaliczki w "
    "wysokości {amount}: {link}\nLink jest ważny do {until}. Tytuł płatności: "
    "{reference}.",
)
