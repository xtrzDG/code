"""
Words that make a sentence of a reply a policy or availability claim, per
language: "free", "included", "allowed", "we accept", "pets", "parking",
"refund", "available", "in stock". A word ending in "*" is a stem (any
word starting with it), others match whole words; phrases match as
written. The list is short on purpose: the verifier model is asked only
when one of these words appears, so it stays a cheap check.
"""

from collections.abc import Mapping

from app.schemas.constants.reply_safety import ClaimTopic

CLAIM_MARKERS: Mapping[str, Mapping[ClaimTopic, tuple[str, ...]]] = {
    "en": {
        ClaimTopic.POLICY: (
            "free", "free of charge", "complimentary", "included", "includes",
            "allowed", "permitted", "we accept", "we take", "pets", "pet-friendly",
            "dogs", "parking", "wifi", "wi-fi", "refund*", "cancellation*",
            "deposit", "prepayment", "wheelchair", "smoking", "discount*",
            "guarantee*", "delivery", "we deliver", "halal", "kosher",
        ),
        ClaimTopic.AVAILABILITY: (
            "available", "availability", "in stock", "vacancy", "vacancies",
            "fully booked", "sold out",
        ),
    },
    "ru": {
        ClaimTopic.POLICY: (
            "бесплатн*", "включен*", "входит в стоимость", "разреш*", "принимаем",
            "животн*", "собак*", "парковк*", "wi-fi", "вай-фай", "возврат*",
            "отмен*", "депозит*", "предоплат*", "инвалидн*", "курить", "скидк*",
            "доставк*", "доставляем", "гаранти*",
        ),
        ClaimTopic.AVAILABILITY: (
            "в наличии", "доступн*", "свобод*", "мест нет", "все занято",
        ),
    },
    "uk": {
        ClaimTopic.POLICY: (
            "безкоштовн*", "включен*", "входить у вартість", "дозвол*",
            "приймаємо", "тварин*", "собак*", "парковк*", "паркуванн*",
            "повернен*", "скасуванн*", "депозит*", "передоплат*", "знижк*",
            "доставк*", "гаранті*",
        ),
        ClaimTopic.AVAILABILITY: ("в наявності", "доступн*", "вільн*"),
    },
    "ka": {
        ClaimTopic.POLICY: (
            "უფასო*", "შედის", "ნებადართული*", "ვიღებთ", "ცხოველ*", "ძაღლ*",
            "პარკინგ*", "ავტოსადგომ*", "wifi", "ვაი-ფაი", "დაბრუნებ*", "გაუქმებ*",
            "დეპოზიტ*", "წინასწარ გადახდ*", "ფასდაკლებ*", "მიწოდებ*", "გარანტი*",
        ),
        ClaimTopic.AVAILABILITY: ("ხელმისაწვდომ*", "თავისუფალ*", "მარაგშია"),
    },
    "tr": {
        ClaimTopic.POLICY: (
            "ücretsiz*", "bedava", "dahil*", "izin*", "kabul ediyoruz", "evcil*",
            "köpek*", "otopark*", "park yeri", "wifi", "iade*", "iptal*",
            "depozito*", "kapora*", "indirim*", "teslimat*", "paket servis",
            "sigara", "garanti*",
        ),
        ClaimTopic.AVAILABILITY: ("mevcut*", "müsait*", "stokta", "boş yer"),
    },
    "he": {
        ClaimTopic.POLICY: (
            "חינם", "בחינם", "ללא תשלום", "כלול*", "מותר*", "מקבלים", "חיות", "כלבים",
            "חניה", "חנייה", "וויפי", "החזר*", "ביטול*", "פיקדון", "מקדמה",
            "הנחה", "משלוח*", "אחריות",
        ),
        ClaimTopic.AVAILABILITY: ("זמין*", "פנוי*", "במלאי", "אזל"),
    },
    "ar": {
        ClaimTopic.POLICY: (
            "مجان*", "بالمجان", "مشمول*", "يشمل", "مسموح*", "نقبل", "حيوانات",
            "كلاب", "موقف*", "مواقف*", "واي فاي", "استرداد*", "استرجاع*",
            "الغاء*", "إلغاء*", "عربون", "خصم*", "توصيل*", "ضمان*",
        ),
        ClaimTopic.AVAILABILITY: ("متاح*", "متوفر*", "شاغر*", "نفدت*"),
    },
    "de": {
        ClaimTopic.POLICY: (
            "kostenlos*", "gratis", "inklusive", "inbegriffen", "erlaubt",
            "akzeptieren", "haustier*", "hunde", "parkplatz*", "parken", "wlan",
            "wifi", "erstattung*", "stornierung*", "storno*", "kaution",
            "anzahlung", "rabatt*", "lieferung*", "liefern", "barrierefrei*",
            "rollstuhl*", "garantie*",
        ),
        ClaimTopic.AVAILABILITY: (
            "verfügbar*", "auf lager", "ausgebucht", "ausverkauft",
        ),
    },
    "fr": {
        ClaimTopic.POLICY: (
            "gratuit*", "offert*", "inclus*", "compris", "autorisé*", "acceptons",
            "animaux", "chiens", "parking", "stationnement", "wifi",
            "rembours*", "annulation*", "acompte", "caution", "réduction*",
            "remise", "livraison*", "livrons", "accessible*", "garanti*",
        ),
        ClaimTopic.AVAILABILITY: (
            "disponible*", "disponibilité*", "en stock", "complet", "épuisé*",
        ),
    },
    "es": {
        ClaimTopic.POLICY: (
            "gratis", "gratuit*", "incluido*", "incluida*", "incluye", "permitid*",
            "permitimos", "aceptamos", "mascotas", "perros", "aparcamiento",
            "estacionamiento", "parking", "wifi", "reembols*", "cancelación*",
            "cancelacion*", "depósito", "deposito", "descuento*", "a domicilio",
            "entrega*", "accesible*", "garantía*",
        ),
        ClaimTopic.AVAILABILITY: (
            "disponible*", "disponibilidad", "en stock", "agotad*", "completo",
        ),
    },
}  # fmt: skip
