"""
Lines of a guest's written booking confirmation, in the customer languages
of the platform's other customer texts (English is the last fallback).
Placeholders are filled with `str.format`; a line without its value is
left out.
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

CONFIRMED_HEADLINE: LocalizedText = build_localized_text(
    en="{business}: your booking is confirmed.",
    ru="{business}: ваша бронь подтверждена.",
    ka="{business}: თქვენი ჯავშანი დადასტურებულია.",
    uk="{business}: ваше бронювання підтверджено.",
    hy="{business}․ ձեր ամրագրումը հաստատված է։",
    he="{business}: ההזמנה שלך אושרה.",
    ar="{business}: تم تأكيد حجزك.",
    tr="{business}: rezervasyonunuz onaylandı.",
    pl="{business}: Twoja rezerwacja jest potwierdzona.",
    de="{business}: Ihre Buchung ist bestätigt.",
    es="{business}: tu reserva está confirmada.",
    fr="{business} : votre réservation est confirmée.",
    it="{business}: la tua prenotazione è confermata.",
    pt="{business}: sua reserva está confirmada.",
    kk="{business}: брондауыңыз расталды.",
)

MOVED_HEADLINE: LocalizedText = build_localized_text(
    en="{business}: your booking has been moved.",
    ru="{business}: ваша бронь перенесена.",
    ka="{business}: თქვენი ჯავშანი გადატანილია.",
    uk="{business}: ваше бронювання перенесено.",
    hy="{business}․ ձեր ամրագրումը տեղափոխված է։",
    he="{business}: ההזמנה שלך הועברה.",
    ar="{business}: تم تغيير موعد حجزك.",
    tr="{business}: rezervasyonunuzun zamanı değiştirildi.",
    pl="{business}: Twoja rezerwacja została przeniesiona.",
    de="{business}: Ihre Buchung wurde verschoben.",
    es="{business}: tu reserva se ha cambiado.",
    fr="{business} : votre réservation a été déplacée.",
    it="{business}: la tua prenotazione è stata spostata.",
    pt="{business}: sua reserva foi remarcada.",
    kk="{business}: брондауыңыз ауыстырылды.",
)

WHEN_LINE: LocalizedText = build_localized_text(
    en="When: {when}",
    ru="Когда: {when}",
    ka="როდის: {when}",
    uk="Коли: {when}",
    hy="Երբ՝ {when}",
    he="מתי: {when}",
    ar="الموعد: {when}",
    tr="Ne zaman: {when}",
    pl="Kiedy: {when}",
    de="Wann: {when}",
    es="Cuándo: {when}",
    fr="Quand : {when}",
    it="Quando: {when}",
    pt="Quando: {when}",
    kk="Қашан: {when}",
)

ARRIVAL_LINE: LocalizedText = build_localized_text(
    en="Arrival: {when}",
    ru="Заезд: {when}",
    ka="ჩამოსვლა: {when}",
    uk="Заїзд: {when}",
    hy="Ժամանում՝ {when}",
    he="הגעה: {when}",
    ar="الوصول: {when}",
    tr="Giriş: {when}",
    pl="Przyjazd: {when}",
    de="Anreise: {when}",
    es="Llegada: {when}",
    fr="Arrivée : {when}",
    it="Arrivo: {when}",
    pt="Chegada: {when}",
    kk="Келу: {when}",
)

DEPARTURE_LINE: LocalizedText = build_localized_text(
    en="Departure: {when}",
    ru="Выезд: {when}",
    ka="გამგზავრება: {when}",
    uk="Виїзд: {when}",
    hy="Մեկնում՝ {when}",
    he="עזיבה: {when}",
    ar="المغادرة: {when}",
    tr="Çıkış: {when}",
    pl="Wyjazd: {when}",
    de="Abreise: {when}",
    es="Salida: {when}",
    fr="Départ : {when}",
    it="Partenza: {when}",
    pt="Saída: {when}",
    kk="Кету: {when}",
)

GUESTS_LINE: LocalizedText = build_localized_text(
    en="Guests: {party_size}",
    ru="Гостей: {party_size}",
    ka="სტუმრები: {party_size}",
    uk="Гостей: {party_size}",
    hy="Հյուրեր՝ {party_size}",
    he="מספר אורחים: {party_size}",
    ar="عدد الضيوف: {party_size}",
    tr="Kişi sayısı: {party_size}",
    pl="Liczba gości: {party_size}",
    de="Personen: {party_size}",
    es="Personas: {party_size}",
    fr="Personnes : {party_size}",
    it="Persone: {party_size}",
    pt="Pessoas: {party_size}",
    kk="Қонақтар саны: {party_size}",
)

SERVICE_LINE: LocalizedText = build_localized_text(
    en="Service: {service}",
    ru="Услуга: {service}",
    ka="მომსახურება: {service}",
    uk="Послуга: {service}",
    hy="Ծառայություն՝ {service}",
    he="שירות: {service}",
    ar="الخدمة: {service}",
    tr="Hizmet: {service}",
    pl="Usługa: {service}",
    de="Leistung: {service}",
    es="Servicio: {service}",
    fr="Prestation : {service}",
    it="Servizio: {service}",
    pt="Serviço: {service}",
    kk="Қызмет: {service}",
)

ADDRESS_LINE: LocalizedText = build_localized_text(
    en="Address: {address}",
    ru="Адрес: {address}",
    ka="მისამართი: {address}",
    uk="Адреса: {address}",
    hy="Հասցե՝ {address}",
    he="כתובת: {address}",
    ar="العنوان: {address}",
    tr="Adres: {address}",
    pl="Adres: {address}",
    de="Adresse: {address}",
    es="Dirección: {address}",
    fr="Adresse : {address}",
    it="Indirizzo: {address}",
    pt="Endereço: {address}",
    kk="Мекенжай: {address}",
)

MAP_LINE: LocalizedText = build_localized_text(
    en="Map: {url}",
    ru="Карта: {url}",
    ka="რუკა: {url}",
    uk="Мапа: {url}",
    hy="Քարտեզ՝ {url}",
    he="מפה: {url}",
    ar="الخريطة: {url}",
    tr="Harita: {url}",
    pl="Mapa: {url}",
    de="Karte: {url}",
    es="Mapa: {url}",
    fr="Plan : {url}",
    it="Mappa: {url}",
    pt="Mapa: {url}",
    kk="Карта: {url}",
)

MANAGE_LINE: LocalizedText = build_localized_text(
    en="Change or cancel: {url}",
    ru="Изменить или отменить: {url}",
    ka="შეცვლა ან გაუქმება: {url}",
    uk="Змінити або скасувати: {url}",
    hy="Փոխել կամ չեղարկել՝ {url}",
    he="לשינוי או ביטול: {url}",
    ar="للتعديل أو الإلغاء: {url}",
    tr="Değiştirmek veya iptal etmek için: {url}",
    pl="Zmień lub odwołaj: {url}",
    de="Ändern oder stornieren: {url}",
    es="Cambiar o cancelar: {url}",
    fr="Modifier ou annuler : {url}",
    it="Modifica o annulla: {url}",
    pt="Alterar ou cancelar: {url}",
    kk="Өзгерту немесе бас тарту: {url}",
)
