"""
What a customer hears after rating their visit, in their language: thanks
(and, for a rating of 3 or below, that a colleague will be in touch), then
the same invitation to the business's Google review page whatever the
rating (no review gating: Google forbids asking only happy customers).
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

LINK_FIELD: str = "{link}"

FEEDBACK_THANKS_TEXT: LocalizedText = build_localized_text(
    en="Thank you for your rating! We are glad you enjoyed your visit.",
    ru="Спасибо за оценку! Мы рады, что вам понравилось.",
    ka="გმადლობთ შეფასებისთვის! მოხარულები ვართ, რომ მოგეწონათ.",
    uk="Дякуємо за оцінку! Ми раді, що вам сподобалося.",
    hy="Շնորհակալություն գնահատականի համար։ Ուրախ ենք, որ Ձեզ դուր եկավ։",
    az="Qiymətləndirmə üçün təşəkkür edirik! Bəyəndiyinizə şadıq.",
    kk="Бағаңызға рахмет! Сізге ұнағанына қуаныштымыз.",
    tr="Puanınız için teşekkürler! Beğenmenize çok sevindik.",
    he="תודה על הדירוג! שמחים שנהניתם.",
    ar="شكرًا على تقييمك! يسعدنا أن الزيارة نالت إعجابك.",
    de="Danke für Ihre Bewertung! Schön, dass es Ihnen gefallen hat.",
    fr="Merci pour votre note ! Nous sommes ravis que votre visite vous ait plu.",
    es="¡Gracias por tu valoración! Nos alegra que te haya gustado.",
    it="Grazie per la tua valutazione! Siamo felici che ti sia piaciuto.",
    pt="Obrigado pela sua avaliação! Ficamos felizes por ter gostado.",
    pl="Dziękujemy za ocenę! Cieszymy się, że się podobało.",
)

FEEDBACK_SORRY_TEXT: LocalizedText = build_localized_text(
    en=(
        "Thank you for your honest rating. We are sorry your visit was not "
        "perfect: a colleague will get in touch with you."
    ),
    ru=(
        "Спасибо за честную оценку. Нам жаль, что визит прошёл не идеально: "
        "с вами свяжется наш сотрудник."
    ),
    ka=(
        "გმადლობთ გულწრფელი შეფასებისთვის. ვწუხვართ, რომ ვიზიტი იდეალური არ "
        "იყო: ჩვენი თანამშრომელი დაგიკავშირდებათ."
    ),
    uk=(
        "Дякуємо за чесну оцінку. Шкода, що візит пройшов не ідеально: з вами "
        "зв'яжеться наш співробітник."
    ),
    hy=(
        "Շնորհակալություն անկեղծ գնահատականի համար։ Ափսոսում ենք, որ այցը "
        "կատարյալ չէր․ մեր աշխատակիցը կկապվի Ձեզ հետ։"
    ),
    az=(
        "Səmimi qiymətləndirmə üçün təşəkkür edirik. Təəssüf ki, ziyarət "
        "mükəmməl keçmədi: əməkdaşımız sizinlə əlaqə saxlayacaq."
    ),
    kk=(
        "Шынайы бағаңызға рахмет. Сапарыңыз мінсіз өтпегеніне өкінеміз: "
        "қызметкеріміз сізбен хабарласады."
    ),
    tr=(
        "Dürüst puanınız için teşekkürler. Ziyaretinizin kusursuz geçmediği "
        "için üzgünüz: bir çalışma arkadaşımız sizinle iletişime geçecek."
    ),
    he="תודה על הדירוג הכן. מצטערים שהביקור לא היה מושלם: נציג שלנו ייצור איתך קשר.",
    ar=(
        "شكرًا على تقييمك الصادق. نأسف لأن زيارتك لم تكن مثالية: سيتواصل معك "
        "أحد زملائنا."
    ),
    de=(
        "Danke für Ihre ehrliche Bewertung. Es tut uns leid, dass nicht alles "
        "perfekt war: Jemand aus unserem Team meldet sich bei Ihnen."
    ),
    fr=(
        "Merci pour votre note sincère. Nous sommes désolés que votre visite "
        "n'ait pas été parfaite : un membre de l'équipe va vous contacter."
    ),
    es=(
        "Gracias por tu valoración sincera. Sentimos que la visita no fuera "
        "perfecta: alguien del equipo se pondrá en contacto contigo."
    ),
    it=(
        "Grazie per la tua valutazione sincera. Ci dispiace che la visita non "
        "sia stata perfetta: un collega ti contatterà."
    ),
    pt=(
        "Obrigado pela sua avaliação sincera. Lamentamos que a visita não "
        "tenha sido perfeita: alguém da equipe entrará em contato com você."
    ),
    pl=(
        "Dziękujemy za szczerą ocenę. Przykro nam, że wizyta nie była idealna: "
        "skontaktuje się z Tobą ktoś z naszego zespołu."
    ),
)

REVIEW_INVITE_TEXT: LocalizedText = build_localized_text(
    en="We would value your review on Google: {link}",
    ru="Будем благодарны за отзыв в Google: {link}",
    ka="მადლობელი ვიქნებით, თუ Google-ზე შეფასებას დაგვიტოვებთ: {link}",
    uk="Будемо вдячні за відгук у Google: {link}",
    hy="Շնորհակալ կլինենք Google-ում Ձեր կարծիքի համար՝ {link}",
    az="Google-da rəyinizi bildirsəniz, minnətdar olarıq: {link}",
    kk="Google-да пікір қалдырсаңыз, алғыс айтамыз: {link}",
    tr="Google'da yorumunuzu paylaşırsanız çok seviniriz: {link}",
    he="נשמח לביקורת שלך בגוגל: {link}",
    ar="نقدّر رأيك على Google: {link}",
    de="Wir freuen uns über Ihre Bewertung bei Google: {link}",
    fr="Votre avis sur Google nous serait précieux : {link}",
    es="Agradeceríamos tu reseña en Google: {link}",
    it="Ci farebbe piacere una tua recensione su Google: {link}",
    pt="Agradeceríamos a sua avaliação no Google: {link}",
    pl="Będziemy wdzięczni za opinię w Google: {link}",
)
