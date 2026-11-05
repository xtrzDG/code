"""
The refund terms a deposit's line and reminder end with, in the customer's
language, so the customer knows them before paying (Codice del consumo
art. 49): when a cancellation gets the deposit back, and that a later one
or a no-show keeps it. The terms follow the owner's refund cutoff, the
same one settling a cancelled booking applies (`deposit_settlement`).

Placeholders: {until} the last moment of a booking's free cancellation
(the time alone today, else date and time, in the business's time);
{hours} the cutoff before a banquet ("24 h", CLDR short units, which no
grammatical case changes).
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

# A booking whose free cancellation is still ahead.
DEPOSIT_REFUND_UNTIL: LocalizedText = build_localized_text(
    en="Cancel by {until} and the deposit is refunded; after that, or if you "
    "do not come, it is kept.",
    ru="При отмене до {until} депозит вернём; при более поздней отмене или "
    "неявке он не возвращается.",
    ka="თუ ჯავშანს {until}-მდე გააუქმებთ, დეპოზიტს დაგიბრუნებთ; მოგვიანებით "
    "გაუქმების ან გამოუცხადებლობის შემთხვევაში ის არ ბრუნდება.",
    uk="У разі скасування до {until} депозит повернемо; у разі пізнішого "
    "скасування або неявки він не повертається.",
    hy="Եթե չեղարկեք մինչև {until}, կանխավճարը կվերադարձնենք։ Ավելի ուշ "
    "չեղարկելու կամ չներկայանալու դեպքում այն չի վերադարձվում։",
    az="Rezervasiyanı {until}-dək ləğv etsəniz, depozit geri qaytarılır; daha "
    "gec ləğv etdikdə və ya gəlmədikdə geri qaytarılmır.",
    kk="{until} дейін бас тартсаңыз, депозит қайтарылады; кейінірек бас "
    "тартсаңыз немесе келмесеңіз, ол қайтарылмайды.",
    tr="Rezervasyonu şu zamana kadar iptal ederseniz kapora iade edilir: "
    "{until}. Daha geç iptal veya gelmeme durumunda iade edilmez.",
    he="ביטול עד {until} – הפיקדון יוחזר; ביטול מאוחר יותר או אי־הגעה – "
    "הפיקדון לא יוחזר.",
    ar="إذا ألغيتم الحجز حتى {until} يُعاد إليكم العربون؛ وإذا ألغيتم بعد ذلك "
    "أو لم تحضروا فلا يُعاد.",
    de="Bei einer Stornierung bis {until} erstatten wir die Anzahlung; bei "
    "späterer Stornierung oder Nichterscheinen wird sie einbehalten.",
    fr="En cas d'annulation jusqu'à {until}, l'acompte vous est remboursé ; "
    "au-delà, ou si vous ne venez pas, il est conservé.",
    es="Si cancela hasta {until}, le devolvemos el depósito; si cancela más "
    "tarde o no se presenta, no se devuelve.",
    it="Se annulla entro {until}, l'acconto le viene restituito; dopo, o se "
    "non si presenta, viene trattenuto.",
    pt="Se cancelar até {until}, o sinal é devolvido; se cancelar depois ou "
    "não comparecer, não é devolvido.",
    pl="W razie odwołania do {until} zwrócimy zaliczkę; przy późniejszym "
    "odwołaniu lub nieobecności zaliczka nie jest zwracana.",
)

# A booking asked or reminded of once its free cancellation has passed.
DEPOSIT_NOT_REFUNDABLE: LocalizedText = build_localized_text(
    en="Once paid, the deposit is not refunded if you cancel or do not come.",
    ru="Внесённый депозит не возвращается при отмене или неявке.",
    ka="გადახდილი დეპოზიტი გაუქმების ან გამოუცხადებლობის შემთხვევაში არ ბრუნდება.",
    uk="Внесений депозит не повертається у разі скасування або неявки.",
    hy="Վճարված կանխավճարը չեղարկելու կամ չներկայանալու դեպքում չի վերադարձվում։",
    az="Ödənilmiş depozit ləğv etdikdə və ya gəlmədikdə geri qaytarılmır.",
    kk="Төленген депозит бас тартқанда немесе келмегенде қайтарылмайды.",
    tr="Ödenen kapora, iptal veya gelmeme durumunda iade edilmez.",
    he="פיקדון ששולם לא יוחזר במקרה של ביטול או אי־הגעה.",
    ar="لا يُعاد العربون المدفوع في حال الإلغاء أو عدم الحضور.",
    de="Die gezahlte Anzahlung wird bei Stornierung oder Nichterscheinen nicht "
    "erstattet.",
    fr="Une fois réglé, l'acompte n'est pas remboursé en cas d'annulation ou "
    "d'absence.",
    es="Una vez abonado, el depósito no se devuelve si cancela o no se presenta.",
    it="Una volta versato, l'acconto non viene restituito in caso di "
    "annullamento o mancata presentazione.",
    pt="Depois de pago, o sinal não é devolvido em caso de cancelamento ou de "
    "não comparência.",
    pl="Wpłacona zaliczka nie jest zwracana w razie odwołania lub nieobecności.",
)

# A banquet request (its event has no start time yet): the cutoff in hours.
DEPOSIT_REFUND_BEFORE_EVENT: LocalizedText = build_localized_text(
    en="If you cancel at least {hours} before the event, the deposit is "
    "refunded; later, or if you do not come, it is kept.",
    ru="При отмене не позднее чем за {hours} до мероприятия депозит вернём; "
    "при более поздней отмене или неявке он не возвращается.",
    ka="თუ ღონისძიებამდე არანაკლებ {hours}-ით ადრე გააუქმებთ, დეპოზიტს "
    "დაგიბრუნებთ; მოგვიანებით გაუქმების ან გამოუცხადებლობის შემთხვევაში ის "
    "არ ბრუნდება.",
    uk="У разі скасування щонайменше за {hours} до заходу депозит повернемо; "
    "у разі пізнішого скасування або неявки він не повертається.",
    hy="Եթե չեղարկեք միջոցառումից առնվազն {hours} առաջ, կանխավճարը "
    "կվերադարձնենք։ Ավելի ուշ չեղարկելու կամ չներկայանալու դեպքում այն չի "
    "վերադարձվում։",
    az="Tədbirdən ən azı {hours} əvvəl ləğv etsəniz, depozit geri qaytarılır; "
    "daha gec ləğv etdikdə və ya gəlmədikdə geri qaytarılmır.",
    kk="Іс-шарадан кемінде {hours} бұрын бас тартсаңыз, депозит қайтарылады; "
    "кейінірек бас тартсаңыз немесе келмесеңіз, ол қайтарылмайды.",
    tr="Etkinlikten en az {hours} önce iptal ederseniz kapora iade edilir; "
    "daha geç iptal veya gelmeme durumunda iade edilmez.",
    he="ביטול לפחות {hours} לפני האירוע – הפיקדון יוחזר; ביטול מאוחר יותר או "
    "אי־הגעה – הפיקדון לא יוחזר.",
    ar="إذا ألغيتم قبل {hours} على الأقل من المناسبة يُعاد إليكم العربون؛ "
    "وإذا ألغيتم بعد ذلك أو لم تحضروا فلا يُعاد.",
    de="Bei einer Stornierung mindestens {hours} vor der Veranstaltung "
    "erstatten wir die Anzahlung; bei späterer Stornierung oder "
    "Nichterscheinen wird sie einbehalten.",
    fr="En cas d'annulation au moins {hours} avant l'événement, l'acompte vous "
    "est remboursé ; au-delà, ou si vous ne venez pas, il est conservé.",
    es="Si cancela al menos {hours} antes del evento, le devolvemos el "
    "depósito; si cancela más tarde o no se presenta, no se devuelve.",
    it="Se annulla almeno {hours} prima dell'evento, l'acconto le viene "
    "restituito; dopo, o se non si presenta, viene trattenuto.",
    pt="Se cancelar pelo menos {hours} antes do evento, o sinal é devolvido; "
    "se cancelar depois ou não comparecer, não é devolvido.",
    pl="W razie odwołania co najmniej {hours} przed wydarzeniem zwrócimy "
    "zaliczkę; przy późniejszym odwołaniu lub nieobecności zaliczka nie jest "
    "zwracana.",
)

# A banquet request when any cancellation before the event gets it back.
DEPOSIT_REFUND_ANY_TIME_BEFORE_EVENT: LocalizedText = build_localized_text(
    en="If you cancel before the event, the deposit is refunded; if you do "
    "not come, it is kept.",
    ru="При отмене до начала мероприятия депозит вернём; при неявке он не "
    "возвращается.",
    ka="თუ ღონისძიებამდე გააუქმებთ, დეპოზიტს დაგიბრუნებთ; "
    "გამოუცხადებლობის შემთხვევაში ის არ ბრუნდება.",
    uk="У разі скасування до початку заходу депозит повернемо; у разі неявки "
    "він не повертається.",
    hy="Եթե չեղարկեք մինչև միջոցառումը, կանխավճարը կվերադարձնենք։ "
    "Չներկայանալու դեպքում այն չի վերադարձվում։",
    az="Tədbirdən əvvəl ləğv etsəniz, depozit geri qaytarılır; gəlmədikdə "
    "geri qaytarılmır.",
    kk="Іс-шараға дейін бас тартсаңыз, депозит қайтарылады; келмесеңіз, ол "
    "қайтарылмайды.",
    tr="Etkinlikten önce iptal ederseniz kapora iade edilir; gelmemeniz "
    "durumunda iade edilmez.",
    he="ביטול לפני האירוע – הפיקדון יוחזר; אי־הגעה – הפיקדון לא יוחזר.",
    ar="إذا ألغيتم قبل المناسبة يُعاد إليكم العربون؛ وإذا لم تحضروا فلا يُعاد.",
    de="Bei einer Stornierung vor der Veranstaltung erstatten wir die "
    "Anzahlung; bei Nichterscheinen wird sie einbehalten.",
    fr="En cas d'annulation avant l'événement, l'acompte vous est remboursé ; "
    "si vous ne venez pas, il est conservé.",
    es="Si cancela antes del evento, le devolvemos el depósito; si no se "
    "presenta, no se devuelve.",
    it="Se annulla prima dell'evento, l'acconto le viene restituito; se non "
    "si presenta, viene trattenuto.",
    pt="Se cancelar antes do evento, o sinal é devolvido; se não comparecer, "
    "não é devolvido.",
    pl="W razie odwołania przed wydarzeniem zwrócimy zaliczkę; w razie "
    "nieobecności zaliczka nie jest zwracana.",
)
