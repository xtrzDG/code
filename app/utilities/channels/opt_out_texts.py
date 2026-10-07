"""
What a customer hears after STOP or START, in their language: whether
messages they did not ask for (reminders, feedback requests) still come,
and how to change it. Writing to the business keeps working either way.
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

OPTED_OUT_TEXT: LocalizedText = build_localized_text(
    en=(
        "Done: {business} will no longer send you messages you did not ask "
        "for, such as reminders and feedback requests. You can still write to "
        "us at any time. To get them again, reply START."
    ),
    ru=(
        "Готово: {business} больше не будет присылать вам сообщения, которые "
        "вы не запрашивали, — напоминания и просьбы об отзыве. Писать нам "
        "можно в любое время. Чтобы снова их получать, ответьте СТАРТ."
    ),
    ka=(
        "მზადაა: {business} აღარ გამოგიგზავნით შეტყობინებებს, რომლებიც არ "
        "მოგითხოვიათ — შეხსენებებსა და შეფასების თხოვნებს. მოგვწერეთ ნებისმიერ "
        "დროს. ხელახლა მისაღებად უპასუხეთ: სტარტი."
    ),
    uk=(
        "Готово: {business} більше не надсилатиме вам повідомлень, яких ви не "
        "просили, — нагадувань і прохань про відгук. Писати нам можна будь-коли. "
        "Щоб знову їх отримувати, надішліть СТАРТ."
    ),
    hy=(
        "Պատրաստ է․ {business}-ն այլևս Ձեզ չի ուղարկի հաղորդագրություններ, "
        "որոնք չեք խնդրել (հիշեցումներ, կարծիքի խնդրանքներ)։ Կարող եք գրել "
        "մեզ ցանկացած ժամանակ։ Կրկին ստանալու համար պատասխանեք ՍՏԱՐՏ։"
    ),
    az=(
        "Hazırdır: {business} artıq sizə istəmədiyiniz mesajlar (xatırlatmalar, "
        "rəy sorğuları) göndərməyəcək. Bizə istənilən vaxt yaza bilərsiniz. "
        "Yenidən almaq üçün START yazın."
    ),
    kk=(
        "Дайын: {business} енді сізге сұрамаған хабарламаларды (еске "
        "салғыштар, пікір сұраулары) жібермейді. Бізге кез келген уақытта "
        "жаза аласыз. Қайта алу үшін СТАРТ деп жазыңыз."
    ),
    tr=(
        "Tamam: {business} artık size istemediğiniz mesajlar (hatırlatmalar, "
        "geri bildirim istekleri) göndermeyecek. Bize her zaman yazabilirsiniz. "
        "Yeniden almak için BAŞLA yazın."
    ),
    he=(
        "בוצע: {business} לא ישלחו לך יותר הודעות שלא ביקשת, כמו תזכורות "
        "ובקשות למשוב. אפשר לכתוב לנו בכל עת. כדי לקבל אותן שוב, השיבו התחל."
    ),
    ar=(
        "تم: لن يرسل لك {business} بعد الآن رسائل لم تطلبها، مثل التذكيرات "
        "وطلبات التقييم. يمكنك مراسلتنا في أي وقت. لاستلامها مجددًا، أرسل ابدأ."
    ),
    de=(
        "Erledigt: {business} schickt Ihnen keine Nachrichten mehr, um die Sie "
        "nicht gebeten haben, etwa Erinnerungen und Bewertungsanfragen. Sie "
        "können uns jederzeit schreiben. Mit START erhalten Sie sie wieder."
    ),
    fr=(
        "C'est fait : {business} ne vous enverra plus de messages que vous "
        "n'avez pas demandés (rappels, demandes d'avis). Vous pouvez toujours "
        "nous écrire. Pour les recevoir à nouveau, répondez START."
    ),
    es=(
        "Listo: {business} ya no te enviará mensajes que no hayas pedido, como "
        "recordatorios o solicitudes de opinión. Puedes escribirnos cuando "
        "quieras. Para volver a recibirlos, responde START."
    ),
    it=(
        "Fatto: {business} non ti invierà più messaggi che non hai chiesto, "
        "come promemoria e richieste di recensione. Puoi scriverci quando vuoi. "
        "Per riceverli di nuovo, rispondi START."
    ),
    pt=(
        "Pronto: {business} não enviará mais mensagens que você não pediu, "
        "como lembretes e pedidos de avaliação. Você pode nos escrever quando "
        "quiser. Para recebê-las de novo, responda START."
    ),
    pl=(
        "Gotowe: {business} nie będzie już wysyłać wiadomości, o które nie "
        "prosiłeś, takich jak przypomnienia i prośby o opinię. Możesz pisać do "
        "nas w każdej chwili. Aby znów je otrzymywać, odpisz START."
    ),
)

OPTED_IN_TEXT: LocalizedText = build_localized_text(
    en=(
        "Welcome back! {business} will send you reminders and other updates "
        "again. Reply STOP at any time to stop them."
    ),
    ru=(
        "С возвращением! {business} снова будет присылать вам напоминания и "
        "другие сообщения. Чтобы остановить их, ответьте СТОП."
    ),
    ka=(
        "კეთილი იყოს თქვენი დაბრუნება! {business} კვლავ გამოგიგზავნით "
        "შეხსენებებს და სხვა შეტყობინებებს. შესაწყვეტად უპასუხეთ: სტოპ."
    ),
    uk=(
        "З поверненням! {business} знову надсилатиме вам нагадування та інші "
        "повідомлення. Щоб зупинити їх, надішліть СТОП."
    ),
    hy=(
        "Բարի վերադարձ։ {business}-ն կրկին Ձեզ կուղարկի հիշեցումներ և այլ "
        "հաղորդագրություններ։ Դադարեցնելու համար պատասխանեք ՍՏՈՊ։"
    ),
    az=(
        "Yenidən xoş gəlmisiniz! {business} sizə yenə xatırlatmalar və digər "
        "mesajlar göndərəcək. Dayandırmaq üçün istənilən vaxt STOP yazın."
    ),
    kk=(
        "Қайта қош келдіңіз! {business} сізге қайтадан еске салғыштар мен "
        "басқа хабарламалар жібереді. Тоқтату үшін СТОП деп жазыңыз."
    ),
    tr=(
        "Tekrar hoş geldiniz! {business} size yeniden hatırlatmalar ve diğer "
        "mesajları gönderecek. Durdurmak için istediğiniz zaman DUR yazın."
    ),
    he="ברוכים השבים! {business} ישלחו לך שוב תזכורות ועדכונים. להפסקה, השיבו עצור.",
    ar=(
        "أهلًا بعودتك! سيرسل لك {business} التذكيرات والرسائل الأخرى مجددًا. "
        "لإيقافها في أي وقت، أرسل توقف."
    ),
    de=(
        "Willkommen zurück! {business} schickt Ihnen wieder Erinnerungen und "
        "andere Nachrichten. Mit STOPP bestellen Sie sie jederzeit ab."
    ),
    fr=(
        "Bon retour ! {business} vous enverra de nouveau des rappels et "
        "d'autres messages. Répondez STOP à tout moment pour les arrêter."
    ),
    es=(
        "¡Bienvenido de nuevo! {business} volverá a enviarte recordatorios y "
        "otros mensajes. Responde STOP cuando quieras para dejar de recibirlos."
    ),
    it=(
        "Bentornato! {business} ti invierà di nuovo promemoria e altri "
        "messaggi. Rispondi STOP in qualsiasi momento per interromperli."
    ),
    pt=(
        "Bem-vindo de volta! {business} voltará a enviar lembretes e outras "
        "mensagens. Responda PARAR a qualquer momento para interrompê-las."
    ),
    pl=(
        "Witamy ponownie! {business} znów będzie wysyłać przypomnienia i inne "
        "wiadomości. Odpisz STOP w dowolnej chwili, aby je zatrzymać."
    ),
)
