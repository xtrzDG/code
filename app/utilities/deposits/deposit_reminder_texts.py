"""
The reminder of a waiting deposit, sent once through the outbox in the
customer's language while the place (or the link) still holds.

Placeholders: {business}, {date} and {time} of the booking, {until} the end
of the hold, {amount} and {link}.
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

DEPOSIT_BOOKING_REMINDER: LocalizedText = build_localized_text(
    en="{business}: a reminder — your booking on {date} at {time} is held "
    "until {until}. To keep it, please pay the deposit of {amount}: {link}",
    ru="{business}: напоминаем — ваша бронь на {date} в {time} удерживается до "
    "{until}. Чтобы сохранить её, внесите депозит {amount}: {link}",
    ka="{business}: შეგახსენებთ — თქვენი ჯავშანი {date}, {time}-ზე {until}-მდე "
    "ინახება. მის შესანარჩუნებლად გადაიხადეთ დეპოზიტი {amount}: {link}",
    uk="{business}: нагадуємо — ваше бронювання на {date} о {time} утримується "
    "до {until}. Щоб зберегти його, внесіть депозит {amount}: {link}",
    hy="{business}: հիշեցում — Ձեր ամրագրումը {date}, ժամը {time}-ին պահվում "
    "է մինչև {until}։ Այն պահպանելու համար վճարեք {amount} կանխավճարը՝ {link}",
    az="{business}: xatırlatma — {date}, saat {time} üçün rezervasiyanız "
    "{until}-dək saxlanılır. Onu saxlamaq üçün {amount} depoziti ödəyin: {link}",
    kk="{business}: еске саламыз — {date}, сағат {time} брондауыңыз {until} "
    "дейін сақталады. Оны сақтап қалу үшін {amount} депозитті төлеңіз: {link}",
    tr="{business}: hatırlatma — {date} saat {time} için rezervasyonunuz şu "
    "zamana kadar tutuluyor: {until}. Korumak için lütfen {amount} tutarındaki "
    "kaporayı ödeyin: {link}",
    he="{business}: תזכורת — ההזמנה שלכם ל-{date} בשעה {time} שמורה עד "
    "{until}. כדי לשמור עליה, נא לשלם את הפיקדון של {amount}: {link}",
    ar="{business}: تذكير — حجزكم يوم {date} الساعة {time} محجوز حتى {until}. "
    "للاحتفاظ به، يرجى دفع العربون بقيمة {amount}: {link}",
    de="{business}: Zur Erinnerung — Ihre Buchung am {date} um {time} ist bis "
    "{until} reserviert. Um sie zu behalten, zahlen Sie bitte die Anzahlung "
    "von {amount}: {link}",
    fr="{business} : petit rappel — votre réservation du {date} à {time} est "
    "retenue jusqu'à {until}. Pour la garder, merci de régler l'acompte de "
    "{amount} : {link}",
    es="{business}: le recordamos que su reserva del {date} a las {time} está "
    "retenida hasta {until}. Para mantenerla, abone el depósito de {amount}: "
    "{link}",
    it="{business}: le ricordiamo che la sua prenotazione del {date} alle "
    "{time} è trattenuta fino a {until}. Per mantenerla, versi l'acconto di "
    "{amount}: {link}",
    pt="{business}: lembrete — a sua reserva de {date} às {time} está guardada "
    "até {until}. Para a manter, pague o sinal de {amount}: {link}",
    pl="{business}: przypominamy — Państwa rezerwacja na {date} o {time} jest "
    "utrzymywana do {until}. Aby ją zachować, prosimy o wpłatę zaliczki "
    "{amount}: {link}",
)

DEPOSIT_BANQUET_REMINDER: LocalizedText = build_localized_text(
    en="{business}: a reminder — the deposit of {amount} for your banquet "
    "request is still waiting: {link}\nThe link is valid until {until}.",
    ru="{business}: напоминаем — депозит {amount} по вашей заявке на банкет ещё "
    "не внесён: {link}\nСсылка действует до {until}.",
    ka="{business}: შეგახსენებთ — თქვენი ბანკეტის მოთხოვნის დეპოზიტი {amount} "
    "ჯერ არ არის გადახდილი: {link}\nბმული მოქმედებს {until}-მდე.",
    uk="{business}: нагадуємо — депозит {amount} за вашою заявкою на банкет ще "
    "не внесено: {link}\nПосилання діє до {until}.",
    hy="{business}: հիշեցում — Ձեր բանկետի հայտի {amount} կանխավճարը դեռ "
    "վճարված չէ՝ {link}\nՀղումը գործում է մինչև {until}։",
    az="{business}: xatırlatma — banket sorğunuz üçün {amount} depozit hələ "
    "ödənilməyib: {link}\nKeçid {until}-dək etibarlıdır.",
    kk="{business}: еске саламыз — банкетке өтініміңіз бойынша {amount} депозит "
    "әлі төленбеген: {link}\nСілтеме {until} дейін жарамды.",
    tr="{business}: hatırlatma — ziyafet talebiniz için {amount} tutarındaki "
    "kapora henüz ödenmedi: {link}\nBağlantı şu zamana kadar geçerlidir: "
    "{until}.",
    he="{business}: תזכורת — הפיקדון של {amount} עבור בקשת האירוע שלכם עדיין "
    "לא שולם: {link}\nהקישור בתוקף עד {until}.",
    ar="{business}: تذكير — لم يُدفع بعد عربون طلب المأدبة بقيمة {amount}: "
    "{link}\nالرابط صالح حتى {until}.",
    de="{business}: Zur Erinnerung — die Anzahlung von {amount} für Ihre "
    "Bankettanfrage steht noch aus: {link}\nDer Link ist bis {until} gültig.",
    fr="{business} : petit rappel — l'acompte de {amount} pour votre demande "
    "de banquet n'est pas encore réglé : {link}\nLe lien est valable jusqu'à "
    "{until}.",
    es="{business}: le recordamos que el depósito de {amount} de su solicitud "
    "de banquete sigue pendiente: {link}\nEl enlace es válido hasta {until}.",
    it="{business}: le ricordiamo che l'acconto di {amount} per la sua "
    "richiesta di banchetto è ancora in sospeso: {link}\nIl link è valido "
    "fino a {until}.",
    pt="{business}: lembrete — o sinal de {amount} do seu pedido de banquete "
    "ainda está por pagar: {link}\nO link é válido até {until}.",
    pl="{business}: przypominamy — zaliczka {amount} za zapytanie o bankiet "
    "nie została jeszcze wpłacona: {link}\nLink jest ważny do {until}.",
)

DEPOSIT_BOOKING_RELEASED: LocalizedText = build_localized_text(
    en="{business}: we could not keep your booking on {date} at {time} because "
    "the deposit was not paid in time. Write to us if you would still like to "
    "come.",
    ru="{business}: мы не смогли сохранить вашу бронь на {date} в {time}, "
    "потому что депозит не был внесён вовремя. Напишите нам, если всё ещё "
    "хотите прийти.",
    ka="{business}: თქვენი ჯავშანი {date}, {time}-ზე ვერ შევინარჩუნეთ, რადგან "
    "დეპოზიტი დროულად არ იქნა გადახდილი. მოგვწერეთ, თუ კვლავ გსურთ მოსვლა.",
    uk="{business}: ми не змогли зберегти ваше бронювання на {date} о {time}, "
    "бо депозит не було внесено вчасно. Напишіть нам, якщо все ще бажаєте "
    "прийти.",
    hy="{business}: չկարողացանք պահպանել Ձեր ամրագրումը {date}, ժամը "
    "{time}-ին, քանի որ կանխավճարը ժամանակին չի վճարվել։ Գրեք մեզ, եթե դեռ "
    "ցանկանում եք գալ։",
    az="{business}: depozit vaxtında ödənilmədiyi üçün {date}, saat {time} "
    "üçün rezervasiyanızı saxlaya bilmədik. Hələ də gəlmək istəyirsinizsə, "
    "bizə yazın.",
    kk="{business}: депозит уақытында төленбегендіктен, {date}, сағат {time} "
    "брондауыңызды сақтай алмадық. Әлі де келгіңіз келсе, бізге жазыңыз.",
    tr="{business}: kapora zamanında ödenmediği için {date} saat {time} "
    "rezervasyonunuzu tutamadık. Hâlâ gelmek isterseniz bize yazın.",
    he="{business}: לא יכולנו לשמור את ההזמנה שלכם ל-{date} בשעה {time}, כי "
    "הפיקדון לא שולם בזמן. כתבו לנו אם תרצו עדיין להגיע.",
    ar="{business}: لم نتمكن من الاحتفاظ بحجزكم يوم {date} الساعة {time} لأن "
    "العربون لم يُدفع في الوقت المحدد. راسلونا إن كنتم لا تزالون ترغبون في "
    "الحضور.",
    de="{business}: Wir konnten Ihre Buchung am {date} um {time} nicht halten, "
    "weil die Anzahlung nicht rechtzeitig einging. Schreiben Sie uns, wenn Sie "
    "trotzdem kommen möchten.",
    fr="{business} : nous n'avons pas pu garder votre réservation du {date} à "
    "{time}, car l'acompte n'a pas été réglé à temps. Écrivez-nous si vous "
    "souhaitez toujours venir.",
    es="{business}: no pudimos mantener su reserva del {date} a las {time} "
    "porque el depósito no se abonó a tiempo. Escríbanos si todavía desea "
    "venir.",
    it="{business}: non abbiamo potuto mantenere la sua prenotazione del {date} "
    "alle {time} perché l'acconto non è stato versato in tempo. Ci scriva se "
    "desidera ancora venire.",
    pt="{business}: não conseguimos manter a sua reserva de {date} às {time} "
    "porque o sinal não foi pago a tempo. Escreva-nos se ainda quiser vir.",
    pl="{business}: nie mogliśmy utrzymać Państwa rezerwacji na {date} o "
    "{time}, ponieważ zaliczka nie została wpłacona na czas. Prosimy o "
    "wiadomość, jeśli nadal chcą Państwo przyjść.",
)
