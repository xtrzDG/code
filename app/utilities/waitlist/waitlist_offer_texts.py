"""
The offer of a freed place to a waiting customer, in their language.

WAITLIST_OFFER_TEXT is also the body of the WhatsApp utility template for
a closed 24-hour window (WHATSAPP_WAITLIST_TEMPLATE): its parameters are
{{1}} the business, {{2}} the date, {{3}} the time and {{4}} the minutes
the place is held (`template_body` shows it that way).
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

TEMPLATE_FIELDS: tuple[str, ...] = ("{business}", "{date}", "{time}", "{minutes}")

WAITLIST_OFFER_TEXT: LocalizedText = build_localized_text(
    en=(
        "{business}: good news, a place has opened up for you on {date} at "
        "{time}. We are holding it for you for {minutes} minutes. Reply YES "
        "to take it or NO to let it go."
    ),
    ru=(
        "{business}: хорошая новость — для вас освободилось место на {date} в "
        "{time}. Мы держим его для вас {minutes} мин. Ответьте ДА, чтобы "
        "занять его, или НЕТ, чтобы отказаться."
    ),
    ka=(
        "{business}: კარგი ამბავი — თქვენთვის გათავისუფლდა ადგილი {date}, "
        "{time}-ზე. ადგილს თქვენთვის {minutes} წუთით ვინახავთ. უპასუხეთ "
        "„კი“, თუ გსურთ, ან „არა“, თუ უარს ამბობთ."
    ),
    uk=(
        "{business}: гарна новина — для вас звільнилося місце на {date} о "
        "{time}. Ми тримаємо його для вас {minutes} хв. Відповідайте ТАК, щоб "
        "його зайняти, або НІ, щоб відмовитися."
    ),
    hy=(
        "{business}: լավ նորություն՝ Ձեզ համար ազատվել է տեղ {date}, ժամը "
        "{time}-ին։ Այն պահում ենք Ձեզ համար {minutes} րոպե։ Պատասխանեք ԱՅՈ՝ "
        "զբաղեցնելու համար, կամ ՈՉ՝ հրաժարվելու համար։"
    ),
    az=(
        "{business}: xoş xəbər — sizin üçün {date}, saat {time} üçün yer "
        "boşaldı. Onu sizin üçün {minutes} dəqiqə saxlayırıq. Götürmək üçün "
        "BƏLİ, imtina etmək üçün XEYR yazın."
    ),
    kk=(
        "{business}: жақсы жаңалық — сізге {date}, сағат {time} уақытына орын "
        "босады. Біз оны сізге {minutes} минут сақтаймыз. Алу үшін ИӘ, бас "
        "тарту үшін ЖОҚ деп жауап беріңіз."
    ),
    tr=(
        "{business}: iyi haber, {date} saat {time} için sizin için bir yer "
        "açıldı. Bu yeri {minutes} dakika boyunca sizin için tutuyoruz. Almak "
        "için EVET, vazgeçmek için HAYIR yazın."
    ),
    he=(
        "{business}: חדשות טובות, התפנה עבורכם מקום ב-{date} בשעה {time}. "
        "אנחנו שומרים אותו עבורכם {minutes} דקות. השיבו כן כדי לקחת אותו או "
        "לא כדי לוותר."
    ),
    ar=(
        "{business}: خبر سار، توفر لكم مكان يوم {date} الساعة {time}. نحجزه "
        "لكم لمدة {minutes} دقيقة. ردّوا بـ نعم لحجزه أو لا للتنازل عنه."
    ),
    de=(
        "{business}: Gute Nachricht, für Sie ist ein Platz am {date} um {time} "
        "frei geworden. Wir halten ihn {minutes} Minuten für Sie frei. "
        "Antworten Sie JA, um ihn zu nehmen, oder NEIN, um ihn freizugeben."
    ),
    fr=(
        "{business} : bonne nouvelle, une place s'est libérée pour vous le "
        "{date} à {time}. Nous vous la réservons pendant {minutes} minutes. "
        "Répondez OUI pour la prendre ou NON pour la laisser."
    ),
    es=(
        "{business}: buenas noticias, se ha liberado un lugar para usted el "
        "{date} a las {time}. Se lo guardamos durante {minutes} minutos. "
        "Responda SÍ para tomarlo o NO para dejarlo."
    ),
    it=(
        "{business}: buone notizie, si è liberato un posto per lei il {date} "
        "alle {time}. Lo teniamo per lei per {minutes} minuti. Risponda SÌ per "
        "prenderlo o NO per lasciarlo."
    ),
    pt=(
        "{business}: boas notícias, abriu-se uma vaga para você em {date} às "
        "{time}. Vamos guardá-la por {minutes} minutos. Responda SIM para "
        "ficar com ela ou NÃO para liberá-la."
    ),
    pl=(
        "{business}: dobra wiadomość, zwolniło się dla Ciebie miejsce {date} o "
        "{time}. Trzymamy je dla Ciebie przez {minutes} minut. Odpowiedz TAK, "
        "aby je zająć, lub NIE, aby z niego zrezygnować."
    ),
)
