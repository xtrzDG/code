"""The platform's short answers to a customer's yes or no to an offered place."""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

# "No": the place goes to the next customer.
OFFER_DECLINED_TEXT: LocalizedText = build_localized_text(
    en="Got it, we have let the place go. Thank you for letting us know!",
    ru="Поняли, место отпускаем. Спасибо, что сообщили!",
    ka="გასაგებია, ადგილს ვათავისუფლებთ. გმადლობთ, რომ შეგვატყობინეთ!",
    uk="Зрозуміли, місце відпускаємо. Дякуємо, що повідомили!",
    hy="Հասկացանք, տեղն ազատում ենք։ Շնորհակալություն, որ տեղեկացրիք։",
    az="Aydındır, yeri boşaldırıq. Bildirdiyiniz üçün təşəkkür edirik!",
    kk="Түсіндік, орынды босатамыз. Хабарлағаныңызға рахмет!",
    tr="Anlaşıldı, yeri bırakıyoruz. Haber verdiğiniz için teşekkürler!",
    he="הבנו, אנחנו משחררים את המקום. תודה שעדכנתם!",
    ar="فهمنا، سنترك المكان لغيركم. شكرًا لإبلاغنا!",
    de="Verstanden, wir geben den Platz frei. Danke für Ihre Nachricht!",
    fr="C'est noté, nous libérons la place. Merci de nous avoir prévenus !",
    es="Entendido, liberamos el lugar. ¡Gracias por avisarnos!",
    it="Capito, liberiamo il posto. Grazie per avercelo detto!",
    pt="Entendido, vamos liberar a vaga. Obrigado por avisar!",
    pl="Rozumiemy, zwalniamy miejsce. Dziękujemy za informację!",
)
# A "yes" too late: someone else has the place now; the customer waits on.
OFFER_GONE_TEXT: LocalizedText = build_localized_text(
    en=(
        "Sorry, that place is no longer available. You are still on our "
        "waitlist, and we will write to you if another one opens up."
    ),
    ru=(
        "К сожалению, это место уже недоступно. Вы остаётесь в листе "
        "ожидания — мы напишем, если освободится другое."
    ),
    ka=(
        "სამწუხაროდ, ეს ადგილი უკვე აღარ არის ხელმისაწვდომი. თქვენ რჩებით "
        "მოლოდინის სიაში და მოგწერთ, თუ სხვა ადგილი გათავისუფლდება."
    ),
    uk=(
        "На жаль, це місце вже недоступне. Ви залишаєтеся в списку "
        "очікування — ми напишемо, якщо звільниться інше."
    ),
    hy=(
        "Ցավոք, այդ տեղն այլևս հասանելի չէ։ Դուք մնում եք սպասման ցուցակում, "
        "և մենք կգրենք, եթե մեկ այլ տեղ ազատվի։"
    ),
    az=(
        "Təəssüf ki, bu yer artıq mövcud deyil. Siz gözləmə siyahısında "
        "qalırsınız, başqa yer boşalsa, sizə yazacağıq."
    ),
    kk=(
        "Өкінішке қарай, бұл орын енді бос емес. Сіз күту тізімінде "
        "қаласыз, басқа орын босаса, жазамыз."
    ),
    tr=(
        "Üzgünüz, bu yer artık müsait değil. Bekleme listemizde kalmaya devam "
        "ediyorsunuz; başka bir yer açılırsa size yazacağız."
    ),
    he=(
        "מצטערים, המקום הזה כבר לא פנוי. אתם עדיין ברשימת ההמתנה, ונכתוב "
        "לכם אם יתפנה מקום אחר."
    ),
    ar=(
        "عذرًا، هذا المكان لم يعد متاحًا. ما زلتم على قائمة الانتظار، "
        "وسنراسلكم إن توفر مكان آخر."
    ),
    de=(
        "Leider ist dieser Platz nicht mehr frei. Sie bleiben auf unserer "
        "Warteliste, und wir schreiben Ihnen, wenn ein anderer frei wird."
    ),
    fr=(
        "Désolés, cette place n'est plus disponible. Vous restez sur notre "
        "liste d'attente et nous vous écrirons si une autre se libère."
    ),
    es=(
        "Lo sentimos, ese lugar ya no está disponible. Sigue en nuestra lista "
        "de espera y le escribiremos si se libera otro."
    ),
    it=(
        "Ci dispiace, quel posto non è più disponibile. Resta nella nostra "
        "lista d'attesa e le scriveremo se se ne libera un altro."
    ),
    pt=(
        "Desculpe, essa vaga já não está disponível. Você continua na nossa "
        "lista de espera e escreveremos se abrir outra."
    ),
    pl=(
        "Niestety, to miejsce nie jest już dostępne. Nadal jesteś na naszej "
        "liście oczekujących i napiszemy, jeśli zwolni się inne."
    ),
)
