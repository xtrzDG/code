"""Texts the channels module sends to staff and customers.

Each text is a LocalizedText (English always present, Russian for every
staff-facing text) resolved with the requested -> base language -> English
fallback. Placeholders are filled with `str.format`.
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

# Reply of the platform bot after "/start <code>" linked the chat.
PLATFORM_BOT_LINKED_TEXT: LocalizedText = build_localized_text(
    en=(
        "You are connected to {business}. New bookings, requests and handoffs "
        "will arrive in this chat."
    ),
    ru=(
        "Вы подключены к «{business}». Новые брони, заявки и передачи от "
        "ассистента будут приходить в этот чат."
    ),
    ka=(
        "კავშირი დამყარდა: {business}. ახალი ჯავშნები, მოთხოვნები და "
        "ასისტენტისგან გადმოცემული საუბრები ამ ჩატში მოვა."
    ),
    uk=(
        "Вас підключено до «{business}». Нові бронювання, заявки та передачі "
        "від асистента надходитимуть у цей чат."
    ),
    hy=(
        "Դուք միացված եք՝ {business}։ Նոր ամրագրումները, հայտերը և ասիստենտի "
        "փոխանցած զրույցները կստանաք այս չաթում։"
    ),
    he=(
        "התחברת אל {business}. הזמנות חדשות, פניות ושיחות שהועברו לצוות "
        "יגיעו לצ'אט הזה."
    ),
    ar=(
        "تم ربطك بـ {business}. ستصلك الحجوزات والطلبات الجديدة والمحادثات "
        "المحوّلة إليك في هذه الدردشة."
    ),
    tr=(
        "{business} ile bağlantınız kuruldu. Yeni rezervasyonlar, talepler ve "
        "size aktarılan görüşmeler bu sohbete gelecek."
    ),
    pl=(
        "Połączono z {business}. Nowe rezerwacje, zgłoszenia i przekazane "
        "rozmowy będą trafiać do tego czatu."
    ),
    de=(
        "Sie sind mit {business} verbunden. Neue Buchungen, Anfragen und "
        "Übergaben kommen in diesen Chat."
    ),
    es=(
        "Te has conectado a {business}. Las nuevas reservas, solicitudes y "
        "conversaciones derivadas llegarán a este chat."
    ),
    fr=(
        "Vous êtes connecté à {business}. Les nouvelles réservations, demandes "
        "et conversations transférées arriveront dans ce chat."
    ),
    it=(
        "Sei collegato a {business}. Nuove prenotazioni, richieste e "
        "conversazioni passate allo staff arriveranno in questa chat."
    ),
    pt=(
        "Você está conectado a {business}. Novas reservas, pedidos e conversas "
        "encaminhadas chegarão neste chat."
    ),
    kk=(
        "Сіз {business} жүйесіне қосылдыңыз. Жаңа брондаулар, өтінімдер және "
        "ассистент жіберген сөйлесулер осы чатқа келеді."
    ),
)

# Reply to an unknown, used or expired link code.
PLATFORM_BOT_REJECTED_CODE_TEXT: LocalizedText = build_localized_text(
    en=(
        "This code is invalid or has expired. Ask the owner for a new link in "
        "the cabinet."
    ),
    ru=(
        "Код недействителен или устарел. Попросите владельца создать новую "
        "ссылку в кабинете."
    ),
    ka=(
        "კოდი არასწორია ან ვადაგასულია. სთხოვეთ მფლობელს კაბინეტში ახალი ბმულის შექმნა."
    ),
    uk=(
        "Код недійсний або застарів. Попросіть власника створити нове "
        "посилання в кабінеті."
    ),
    hy=(
        "Կոդը անվավեր է կամ ժամկետանց։ Խնդրեք սեփականատիրոջը կաբինետում "
        "ստեղծել նոր հղում։"
    ),
    he="הקוד אינו תקף או שפג תוקפו. בקשו מהבעלים ליצור קישור חדש באזור האישי.",
    ar=(
        "هذا الرمز غير صالح أو منتهي الصلاحية. اطلب من المالك إنشاء رابط جديد "
        "في لوحة التحكم."
    ),
    tr=(
        "Bu kod geçersiz veya süresi dolmuş. İşletme sahibinden panelde yeni "
        "bir bağlantı oluşturmasını isteyin."
    ),
    pl=(
        "Ten kod jest nieprawidłowy lub wygasł. "
        "Poproś właściciela o nowy link w panelu."
    ),
    de=(
        "Dieser Code ist ungültig oder abgelaufen. Bitten Sie den Inhaber, im "
        "Kundenbereich einen neuen Link zu erstellen."
    ),
    es=(
        "Este código no es válido o ha caducado. Pide "
        "al propietario un nuevo enlace desde el panel."
    ),
    fr=(
        "Ce code est invalide ou a expiré. Demandez au propriétaire de créer un "
        "nouveau lien dans son espace."
    ),
    it=(
        "Questo codice non è valido o è scaduto. Chiedi al titolare di creare "
        "un nuovo link nel pannello."
    ),
    pt=(
        "Este código é inválido ou expirou. Peça "
        "ao proprietário um novo link no painel."
    ),
    kk=(
        "Код жарамсыз немесе мерзімі өткен. Иесінен "
        "кабинетте жаңа сілтеме жасауын сұраңыз."
    ),
)

# Reply when the business already has the maximum number of staff contacts.
PLATFORM_BOT_CONTACT_LIMIT_TEXT: LocalizedText = build_localized_text(
    en=(
        "{business} already has the maximum number of staff contacts. Ask the "
        "owner to remove one first."
    ),
    ru=(
        "У «{business}» уже максимальное число контактов сотрудников. "
        "Попросите владельца сначала удалить один из них."
    ),
    uk=(
        "У «{business}» вже максимальна кількість контактів працівників. "
        "Попросіть власника спочатку видалити один із них."
    ),
)

# Reply to "/start" without a code or to any other message.
PLATFORM_BOT_INSTRUCTIONS_TEXT: LocalizedText = build_localized_text(
    en=(
        "Hello! This bot sends notifications to the staff of businesses that "
        "use an AI assistant. To connect, open the link the owner created for "
        "you in the cabinet."
    ),
    ru=(
        "Здравствуйте! Этот бот присылает уведомления сотрудникам заведений с "
        "AI-ассистентом. Чтобы подключиться, откройте ссылку, которую владелец "
        "создал для вас в кабинете."
    ),
    ka=(
        "გამარჯობა! ეს ბოტი აგზავნის შეტყობინებებს იმ ბიზნესების "
        "თანამშრომლებთან, რომლებიც AI-ასისტენტს იყენებენ. დასაკავშირებლად "
        "გახსენით ბმული, რომელიც მფლობელმა კაბინეტში შეგიქმნათ."
    ),
    uk=(
        "Вітаємо! Цей бот надсилає сповіщення працівникам закладів з "
        "AI-асистентом. Щоб підключитися, відкрийте посилання, яке власник "
        "створив для вас у кабінеті."
    ),
    hy=(
        "Բարև։ Այս բոտը ծանուցումներ է ուղարկում AI ասիստենտ օգտագործող "
        "բիզնեսների աշխատակիցներին։ Միանալու համար բացեք այն հղումը, որը "
        "սեփականատերը ստեղծել է ձեզ համար կաբինետում։"
    ),
    he=(
        "שלום! הבוט הזה שולח התראות לצוות של עסקים שמשתמשים בעוזר AI. כדי "
        "להתחבר, פתחו את הקישור שהבעלים יצר עבורכם באזור האישי."
    ),
    ar=(
        "مرحبًا! يرسل هذا البوت إشعارات إلى موظفي الأعمال التي تستخدم مساعدًا "
        "بالذكاء الاصطناعي. للاتصال، افتح الرابط الذي أنشأه لك المالك في لوحة "
        "التحكم."
    ),
    tr=(
        "Merhaba! Bu bot, yapay zekâ asistanı kullanan işletmelerin "
        "çalışanlarına bildirim gönderir. Bağlanmak için işletme sahibinin "
        "panelde sizin için oluşturduğu bağlantıyı açın."
    ),
    pl=(
        "Dzień dobry! Ten bot wysyła powiadomienia pracownikom firm "
        "korzystających z asystenta AI. Aby się połączyć, otwórz link, który "
        "właściciel utworzył dla Ciebie w panelu."
    ),
    de=(
        "Hallo! Dieser Bot sendet Benachrichtigungen an Mitarbeitende von "
        "Betrieben mit einem KI-Assistenten. Um sich zu verbinden, öffnen Sie "
        "den Link, den der Inhaber im Kundenbereich für Sie erstellt hat."
    ),
    es=(
        "¡Hola! Este bot envía avisos al personal de negocios que usan un "
        "asistente de IA. Para conectarte, abre el enlace que el propietario "
        "creó para ti en el panel."
    ),
    fr=(
        "Bonjour ! Ce bot envoie des notifications au personnel des "
        "établissements qui utilisent un assistant IA. Pour vous connecter, "
        "ouvrez le lien que le propriétaire a créé pour vous dans son espace."
    ),
    it=(
        "Ciao! Questo bot invia notifiche al personale delle attività che usano "
        "un assistente AI. Per collegarti, apri il link che il titolare ha "
        "creato per te nel pannello."
    ),
    pt=(
        "Olá! Este bot envia notificações à equipe de empresas que usam um "
        "assistente de IA. Para se conectar, abra o link que o proprietário "
        "criou para você no painel."
    ),
    kk=(
        "Сәлеметсіз бе! Бұл бот AI-ассистентті қолданатын бизнес "
        "қызметкерлеріне хабарламалар жібереді. Қосылу үшін иесі кабинетте "
        "сізге арнап жасаған сілтемені ашыңыз."
    ),
)

# Message to a caller after the voice agent booked during the call.
CALL_BOOKING_CONFIRMATION_TEXT: LocalizedText = build_localized_text(
    en="{business}: your booking for {when} is confirmed. Thank you for calling!",
    ru="{business}: ваша бронь на {when} подтверждена. Спасибо за звонок!",
    ka="{business}: თქვენი ჯავშანი დადასტურებულია — {when}. გმადლობთ ზარისთვის!",
    uk="{business}: ваше бронювання на {when} підтверджено. Дякуємо за дзвінок!",
    hy=(
        "{business}․ ձեր ամրագրումը հաստատված է՝ {when}։ Շնորհակալություն զանգի համար։"
    ),
    he="{business}: ההזמנה שלך ל-{when} אושרה. תודה על השיחה!",
    ar="{business}: تم تأكيد حجزك في {when}. شكرًا لاتصالك!",
    tr=(
        "{business}: {when} için rezervasyonunuz "
        "onaylandı. Aradığınız için teşekkürler!"
    ),
    pl=(
        "{business}: Twoja rezerwacja na {when} jest "
        "potwierdzona. Dziękujemy za telefon!"
    ),
    de="{business}: Ihre Buchung für {when} ist bestätigt. Danke für Ihren Anruf!",
    es="{business}: tu reserva para el {when} está confirmada. ¡Gracias por llamar!",
    fr=(
        "{business} : votre réservation pour le {when} "
        "est confirmée. Merci de votre appel !"
    ),
    it=(
        "{business}: la tua prenotazione per il {when} "
        "è confermata. Grazie per la chiamata!"
    ),
    pt="{business}: sua reserva para {when} está confirmada. Obrigado pela ligação!",
    kk="{business}: {when} уақытына брондауыңыз расталды. Қоңырау шалғаныңызға рақмет!",
)

# Appended to the confirmation when more than one person is expected.
CALL_BOOKING_PARTY_TEXT: LocalizedText = build_localized_text(
    en="Guests: {party_size}.",
    ru="Гостей: {party_size}.",
    ka="სტუმრები: {party_size}.",
    uk="Гостей: {party_size}.",
    hy="Հյուրեր՝ {party_size}։",
    he="מספר אורחים: {party_size}.",
    ar="عدد الضيوف: {party_size}.",
    tr="Kişi sayısı: {party_size}.",
    pl="Liczba gości: {party_size}.",
    de="Personen: {party_size}.",
    es="Personas: {party_size}.",
    fr="Personnes : {party_size}.",
    it="Persone: {party_size}.",
    pt="Pessoas: {party_size}.",
    kk="Қонақтар саны: {party_size}.",
)
