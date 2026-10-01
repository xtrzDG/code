/*!
 * Assistant Workshop — website chat widget.
 *
 * Embed (the cabinet gives this snippet; GET /v1/businesses/{id}/channels/web/snippet):
 *   <script src="https://<api>/widget.js" data-tenant="<business id>" async></script>
 *
 * Optional attributes of the script tag (they win over the cabinet's choices):
 *   data-color="#4f46e5"   accent colour (hex; default: the cabinet's colour)
 *   data-position="left"   launcher in the bottom-left corner (default: the
 *                          cabinet's corner, else right)
 *   data-language="ka"     interface language (default: the visitor's browser
 *                          language among the business languages)
 *   data-open="true"       open the chat panel on the first page of a visit
 *                          (once the visitor opens or closes it, that choice
 *                          is kept on the next pages)
 *   data-preview="true"    show the widget even while the chat is switched off
 *   data-api-base="https://<api>"   API origin (default: the script's origin)
 *
 * No dependencies and no cookies. The visitor is identified by a random
 * session key kept in localStorage; the widget renders inside a shadow root,
 * so the host page's styles and the widget's styles never mix.
 *
 * The widget polls GET .../messages for answers it has not shown: while a
 * handoff to staff is open, while the panel is open within 24 hours of the
 * visitor's last exchange (staff can write to any website chat), and after
 * a page was left while an answer was being written. Every few seconds at
 * first, slower while nothing new arrives, and not at all while the page is
 * hidden. The visitor key travels in a request header, never in the URL.
 * Tabs of one site share one history: each tab adopts what the others saved.
 * window.AssistantWorkshopChat.open() / .close() / .toggle() control it.
 */
(function () {
  "use strict";

  // Kept in sync with the API by tests/channels/test_widget_script.py.
  var BUSINESS_ATTRIBUTE = "data-tenant";
  var CONFIG_PATH = "/v1/widget/{business_id}/config";
  var MESSAGES_PATH = "/v1/widget/{business_id}/messages";
  var SCRIPT_FILE_NAME = "/widget.js";

  var MAX_MESSAGE_LENGTH = 4000;
  var MAX_STORED_MESSAGES = 60;
  var REQUEST_TIMEOUT_MS = 90000;
  var SESSION_KEY_PATTERN = /^[A-Za-z0-9_-]{16,128}$/;
  var SESSION_KEY_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-";
  var COLOR_PATTERN = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;
  var DEFAULT_ACCENT = "#4f46e5";
  var STORAGE_PREFIX = "aw-chat:";
  var RTL_LANGUAGES = ["ar", "he", "fa", "ur", "yi", "ps", "sd", "ug", "ckb", "dv"];
  var URL_PATTERN = /\bhttps?:\/\/[^\s<>"']+/g;
  // Hebrew, Arabic, Syriac, Thaana, NKo and their presentation forms.
  var RTL_CHARACTER_PATTERN = /[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFC]/;
  var SESSION_KEY_HEADER = "X-Widget-Session-Key";
  var POSITIONS = ["left", "right"];
  // Polling for staff replies: fast after activity, slower while idle.
  var POLL_FIRST_DELAY_MS = 4000;
  var POLL_BACKOFF_FACTOR = 1.6;
  var POLL_MAX_DELAY_OPEN_MS = 30000;
  var POLL_MAX_DELAY_CLOSED_MS = 60000;
  var POLL_MORE_DELAY_MS = 500;
  // A handoff or an exchange in the last 24 hours keeps an open panel
  // polling: staff can write to any website chat.
  var HANDOFF_MEMORY_MS = 24 * 60 * 60 * 1000;
  var SVG_NS = "http://www.w3.org/2000/svg";
  // Fallback when the browser blocks localStorage / sessionStorage.
  var memoryStorage = {};

  // Interface texts. {business} is the business name. Missing languages and
  // keys fall back to the base language and then to English.
  var TEXTS = {
    en: {
      open: "Open chat",
      close: "Close chat",
      subtitle: "AI assistant",
      greeting: "Hello! I am the AI assistant of {business}. How can I help you?",
      placeholder: "Type a message…",
      send: "Send",
      typing: "The assistant is typing…",
      failed: "Message not sent.",
      retry: "Retry",
      unavailable: "The chat is unavailable right now. Please try again later.",
      rateLimited: "Too many messages. Please wait a moment and try again.",
      tooLong: "The message is too long.",
      handedOff: "Your request has been passed to our team. They will contact you soon.",
      language: "Language",
      preview: "Preview: this chat is switched off. Turn it on in the cabinet (Channels).",
      newReply: "New reply",
      staff: "Our team"
    },
    ru: {
      open: "Открыть чат",
      close: "Закрыть чат",
      subtitle: "AI-ассистент",
      greeting: "Здравствуйте! Я AI-ассистент «{business}». Чем могу помочь?",
      placeholder: "Напишите сообщение…",
      send: "Отправить",
      typing: "Ассистент печатает…",
      failed: "Сообщение не отправлено.",
      retry: "Повторить",
      unavailable: "Чат сейчас недоступен. Попробуйте позже.",
      rateLimited: "Слишком много сообщений. Подождите немного и попробуйте снова.",
      tooLong: "Сообщение слишком длинное.",
      handedOff: "Ваш запрос передан сотрудникам. С вами скоро свяжутся.",
      language: "Язык",
      preview: "Предпросмотр: чат выключен. Включите его в кабинете (Каналы).",
      newReply: "Новый ответ",
      staff: "Наша команда"
    },
    ka: {
      open: "ჩატის გახსნა",
      close: "ჩატის დახურვა",
      subtitle: "AI-ასისტენტი",
      greeting: "გამარჯობა! მე ვარ {business}-ის AI-ასისტენტი. რით შემიძლია დაგეხმაროთ?",
      placeholder: "დაწერეთ შეტყობინება…",
      send: "გაგზავნა",
      typing: "ასისტენტი წერს…",
      failed: "შეტყობინება ვერ გაიგზავნა.",
      retry: "თავიდან ცდა",
      unavailable: "ჩატი ახლა მიუწვდომელია. სცადეთ მოგვიანებით.",
      rateLimited: "ძალიან ბევრი შეტყობინებაა. მოიცადეთ და სცადეთ თავიდან.",
      tooLong: "შეტყობინება ძალიან გრძელია.",
      handedOff: "თქვენი მოთხოვნა გადაეცა ჩვენს გუნდს. მალე დაგიკავშირდებიან.",
      language: "ენა",
      preview: "წინასწარი ხედი: ჩატი გამორთულია. ჩართეთ კაბინეტში (არხები).",
      newReply: "ახალი პასუხი",
      staff: "ჩვენი გუნდი"
    },
    uk: {
      open: "Відкрити чат",
      close: "Закрити чат",
      subtitle: "AI-асистент",
      greeting: "Вітаю! Я AI-асистент «{business}». Чим можу допомогти?",
      placeholder: "Напишіть повідомлення…",
      send: "Надіслати",
      typing: "Асистент друкує…",
      failed: "Повідомлення не надіслано.",
      retry: "Повторити",
      unavailable: "Чат зараз недоступний. Спробуйте пізніше.",
      rateLimited: "Забагато повідомлень. Зачекайте трохи та спробуйте знову.",
      tooLong: "Повідомлення задовге.",
      handedOff: "Ваш запит передано працівникам. З вами незабаром зв'яжуться.",
      language: "Мова",
      preview: "Попередній перегляд: чат вимкнено. Увімкніть його в кабінеті (Канали).",
      newReply: "Нова відповідь",
      staff: "Наша команда"
    },
    tr: {
      open: "Sohbeti aç",
      close: "Sohbeti kapat",
      subtitle: "Yapay zekâ asistanı",
      greeting: "Merhaba! Ben {business} işletmesinin yapay zekâ asistanıyım. Size nasıl yardımcı olabilirim?",
      placeholder: "Bir mesaj yazın…",
      send: "Gönder",
      typing: "Asistan yazıyor…",
      failed: "Mesaj gönderilemedi.",
      retry: "Tekrar dene",
      unavailable: "Sohbet şu anda kullanılamıyor. Lütfen daha sonra tekrar deneyin.",
      rateLimited: "Çok fazla mesaj. Lütfen biraz bekleyip tekrar deneyin.",
      tooLong: "Mesaj çok uzun.",
      handedOff: "Talebiniz ekibimize iletildi. Kısa süre içinde sizinle iletişime geçecekler.",
      language: "Dil",
      preview: "Önizleme: bu sohbet kapalı. Panelden (Kanallar) açın.",
      newReply: "Yeni yanıt",
      staff: "Ekibimiz"
    },
    he: {
      open: "פתיחת הצ'אט",
      close: "סגירת הצ'אט",
      subtitle: "עוזר AI",
      greeting: "שלום! אני עוזר ה-AI של {business}. איך אפשר לעזור?",
      placeholder: "כתבו הודעה…",
      send: "שליחה",
      typing: "העוזר מקליד…",
      failed: "ההודעה לא נשלחה.",
      retry: "ניסיון חוזר",
      unavailable: "הצ'אט אינו זמין כרגע. נסו שוב מאוחר יותר.",
      rateLimited: "יותר מדי הודעות. המתינו רגע ונסו שוב.",
      tooLong: "ההודעה ארוכה מדי.",
      handedOff: "הפנייה שלכם הועברה לצוות שלנו. ניצור איתכם קשר בקרוב.",
      language: "שפה",
      preview: "תצוגה מקדימה: הצ'אט כבוי. הפעילו אותו בלוח הניהול (ערוצים).",
      newReply: "תשובה חדשה",
      staff: "הצוות שלנו"
    },
    ar: {
      open: "فتح المحادثة",
      close: "إغلاق المحادثة",
      subtitle: "مساعد الذكاء الاصطناعي",
      greeting: "مرحبًا! أنا مساعد الذكاء الاصطناعي لدى {business}. كيف يمكنني مساعدتك؟",
      placeholder: "اكتب رسالة…",
      send: "إرسال",
      typing: "المساعد يكتب…",
      failed: "لم يتم إرسال الرسالة.",
      retry: "إعادة المحاولة",
      unavailable: "المحادثة غير متاحة الآن. يرجى المحاولة لاحقًا.",
      rateLimited: "رسائل كثيرة جدًا. يرجى الانتظار قليلًا ثم المحاولة مرة أخرى.",
      tooLong: "الرسالة طويلة جدًا.",
      handedOff: "تم تحويل طلبك إلى فريقنا. سيتواصلون معك قريبًا.",
      language: "اللغة",
      preview: "معاينة: هذه المحادثة متوقفة. فعّلها في لوحة التحكم (القنوات).",
      newReply: "رد جديد",
      staff: "فريقنا"
    },
    de: {
      open: "Chat öffnen",
      close: "Chat schließen",
      subtitle: "KI-Assistent",
      greeting: "Hallo! Ich bin der KI-Assistent von {business}. Wie kann ich helfen?",
      placeholder: "Nachricht schreiben…",
      send: "Senden",
      typing: "Der Assistent schreibt…",
      failed: "Nachricht nicht gesendet.",
      retry: "Erneut versuchen",
      unavailable: "Der Chat ist gerade nicht verfügbar. Bitte versuchen Sie es später erneut.",
      rateLimited: "Zu viele Nachrichten. Bitte warten Sie einen Moment.",
      tooLong: "Die Nachricht ist zu lang.",
      handedOff: "Ihre Anfrage wurde an unser Team weitergeleitet. Wir melden uns bald.",
      language: "Sprache",
      preview: "Vorschau: Dieser Chat ist ausgeschaltet. Schalten Sie ihn im Kundenbereich ein (Kanäle).",
      newReply: "Neue Antwort",
      staff: "Unser Team"
    },
    fr: {
      open: "Ouvrir le chat",
      close: "Fermer le chat",
      subtitle: "Assistant IA",
      greeting: "Bonjour ! Je suis l'assistant IA de {business}. Comment puis-je vous aider ?",
      placeholder: "Écrivez un message…",
      send: "Envoyer",
      typing: "L'assistant écrit…",
      failed: "Message non envoyé.",
      retry: "Réessayer",
      unavailable: "Le chat est indisponible pour le moment. Veuillez réessayer plus tard.",
      rateLimited: "Trop de messages. Patientez un instant puis réessayez.",
      tooLong: "Le message est trop long.",
      handedOff: "Votre demande a été transmise à notre équipe. Elle vous contactera bientôt.",
      language: "Langue",
      preview: "Aperçu : ce chat est désactivé. Activez-le dans l’espace client (Canaux).",
      newReply: "Nouvelle réponse",
      staff: "Notre équipe"
    },
    es: {
      open: "Abrir el chat",
      close: "Cerrar el chat",
      subtitle: "Asistente de IA",
      greeting: "¡Hola! Soy el asistente de IA de {business}. ¿En qué puedo ayudarle?",
      placeholder: "Escriba un mensaje…",
      send: "Enviar",
      typing: "El asistente está escribiendo…",
      failed: "Mensaje no enviado.",
      retry: "Reintentar",
      unavailable: "El chat no está disponible ahora. Inténtelo más tarde.",
      rateLimited: "Demasiados mensajes. Espere un momento e inténtelo de nuevo.",
      tooLong: "El mensaje es demasiado largo.",
      handedOff: "Su solicitud se ha enviado a nuestro equipo. Le contactarán pronto.",
      language: "Idioma",
      preview: "Vista previa: este chat está desactivado. Actívalo en el panel (Canales).",
      newReply: "Nueva respuesta",
      staff: "Nuestro equipo"
    },
    it: {
      open: "Apri la chat",
      close: "Chiudi la chat",
      subtitle: "Assistente IA",
      greeting: "Buongiorno! Sono l'assistente IA di {business}. Come posso aiutarla?",
      placeholder: "Scriva un messaggio…",
      send: "Invia",
      typing: "L'assistente sta scrivendo…",
      failed: "Messaggio non inviato.",
      retry: "Riprova",
      unavailable: "La chat non è disponibile al momento. Riprovi più tardi.",
      rateLimited: "Troppi messaggi. Attenda un momento e riprovi.",
      tooLong: "Il messaggio è troppo lungo.",
      handedOff: "La sua richiesta è stata inoltrata al nostro team. La contatteranno presto.",
      language: "Lingua",
      preview: "Anteprima: questa chat è disattivata. Attivala nel pannello (Canali).",
      newReply: "Nuova risposta",
      staff: "Il nostro team"
    },
    pt: {
      open: "Abrir o chat",
      close: "Fechar o chat",
      subtitle: "Assistente de IA",
      greeting: "Olá! Sou o assistente de IA de {business}. Como posso ajudar?",
      placeholder: "Escreva uma mensagem…",
      send: "Enviar",
      typing: "O assistente está escrevendo…",
      failed: "Mensagem não enviada.",
      retry: "Tentar novamente",
      unavailable: "O chat está indisponível no momento. Tente novamente mais tarde.",
      rateLimited: "Mensagens demais. Aguarde um momento e tente novamente.",
      tooLong: "A mensagem é longa demais.",
      handedOff: "Seu pedido foi encaminhado à nossa equipe. Eles entrarão em contato em breve.",
      language: "Idioma",
      preview: "Pré-visualização: este chat está desativado. Ative-o no painel (Canais).",
      newReply: "Nova resposta",
      staff: "Nossa equipe"
    },
    pl: {
      open: "Otwórz czat",
      close: "Zamknij czat",
      subtitle: "Asystent AI",
      greeting: "Dzień dobry! Jestem asystentem AI w {business}. W czym mogę pomóc?",
      placeholder: "Napisz wiadomość…",
      send: "Wyślij",
      typing: "Asystent pisze…",
      failed: "Wiadomość nie została wysłana.",
      retry: "Spróbuj ponownie",
      unavailable: "Czat jest teraz niedostępny. Spróbuj ponownie później.",
      rateLimited: "Zbyt wiele wiadomości. Odczekaj chwilę i spróbuj ponownie.",
      tooLong: "Wiadomość jest za długa.",
      handedOff: "Twoja prośba została przekazana naszemu zespołowi. Wkrótce się z Tobą skontaktujemy.",
      language: "Język",
      preview: "Podgląd: ten czat jest wyłączony. Włącz go w panelu (Kanały).",
      newReply: "Nowa odpowiedź",
      staff: "Nasz zespół"
    },
    zh: {
      open: "打开聊天",
      close: "关闭聊天",
      subtitle: "AI助手",
      greeting: "您好！我是{business}的AI助手。有什么可以帮您？",
      placeholder: "输入消息…",
      send: "发送",
      typing: "助手正在输入…",
      failed: "消息未发送。",
      retry: "重试",
      unavailable: "聊天暂时不可用，请稍后再试。",
      rateLimited: "消息过多，请稍候再试。",
      tooLong: "消息太长。",
      handedOff: "您的请求已转交给我们的团队，他们会尽快与您联系。",
      language: "语言",
      preview: "预览：此聊天已关闭。请在管理后台（渠道）中开启。",
      newReply: "新回复",
      staff: "我们的团队"
    },
    ja: {
      open: "チャットを開く",
      close: "チャットを閉じる",
      subtitle: "AIアシスタント",
      greeting: "こんにちは！{business}のAIアシスタントです。ご用件をどうぞ。",
      placeholder: "メッセージを入力…",
      send: "送信",
      typing: "アシスタントが入力中…",
      failed: "メッセージを送信できませんでした。",
      retry: "再試行",
      unavailable: "現在チャットはご利用いただけません。しばらくしてからお試しください。",
      rateLimited: "メッセージが多すぎます。少し待ってからお試しください。",
      tooLong: "メッセージが長すぎます。",
      handedOff: "お問い合わせを担当者に引き継ぎました。まもなくご連絡します。",
      language: "言語",
      preview: "プレビュー：このチャットはオフです。管理画面（チャネル）でオンにしてください。",
      newReply: "新しい返信",
      staff: "スタッフ"
    },
    hy: {
      open: "Բացել զրույցը",
      close: "Փակել զրույցը",
      subtitle: "AI օգնական",
      greeting: "Բարև ձեզ։ Ես {business}-ի AI օգնականն եմ։ Ինչո՞վ կարող եմ օգնել։",
      placeholder: "Գրեք հաղորդագրություն…",
      send: "Ուղարկել",
      typing: "Օգնականը գրում է…",
      failed: "Հաղորդագրությունը չուղարկվեց։",
      retry: "Կրկնել",
      unavailable: "Զրույցը հիմա հասանելի չէ։ Փորձեք ավելի ուշ։",
      rateLimited: "Չափազանց շատ հաղորդագրություններ։ Մի փոքր սպասեք և նորից փորձեք։",
      tooLong: "Հաղորդագրությունը չափազանց երկար է։",
      handedOff: "Ձեր հարցումը փոխանցվել է մեր թիմին։ Նրանք շուտով կկապվեն ձեզ հետ։",
      language: "Լեզու",
      preview: "Նախադիտում. զրույցն անջատված է։ Միացրեք այն կաբինետում (Ալիքներ)։",
      newReply: "Նոր պատասխան",
      staff: "Մեր թիմը"
    },
    kk: {
      open: "Чатты ашу",
      close: "Чатты жабу",
      subtitle: "AI көмекші",
      greeting: "Сәлеметсіз бе! Мен {business} AI көмекшісімін. Қалай көмектесе аламын?",
      placeholder: "Хабарлама жазыңыз…",
      send: "Жіберу",
      typing: "Көмекші жазып жатыр…",
      failed: "Хабарлама жіберілмеді.",
      retry: "Қайталау",
      unavailable: "Чат қазір қолжетімсіз. Кейінірек қайталап көріңіз.",
      rateLimited: "Хабарламалар тым көп. Біраз күтіп, қайталап көріңіз.",
      tooLong: "Хабарлама тым ұзын.",
      handedOff: "Сұрауыңыз біздің командаға жіберілді. Олар сізбен жақын арада байланысады.",
      language: "Тіл",
      preview: "Алдын ала қарау: чат өшірулі. Оны кабинетте қосыңыз (Арналар).",
      newReply: "Жаңа жауап",
      staff: "Біздің команда"
    },
    az: {
      open: "Söhbəti aç",
      close: "Söhbəti bağla",
      subtitle: "AI köməkçi",
      greeting: "Salam! Mən {business} AI köməkçisiyəm. Sizə necə kömək edə bilərəm?",
      placeholder: "Mesaj yazın…",
      send: "Göndər",
      typing: "Köməkçi yazır…",
      failed: "Mesaj göndərilmədi.",
      retry: "Yenidən cəhd et",
      unavailable: "Söhbət hazırda əlçatan deyil. Bir az sonra yenidən cəhd edin.",
      rateLimited: "Həddindən çox mesaj. Bir az gözləyin və yenidən cəhd edin.",
      tooLong: "Mesaj çox uzundur.",
      handedOff: "Sorğunuz komandamıza ötürüldü. Tezliklə sizinlə əlaqə saxlayacaqlar.",
      language: "Dil",
      preview: "Önizləmə: söhbət söndürülüb. Onu kabinetdə (Kanallar) aktiv edin.",
      newReply: "Yeni cavab",
      staff: "Komandamız"
    },
    lt: {
      open: "Atidaryti pokalbį",
      close: "Uždaryti pokalbį",
      subtitle: "DI asistentas",
      greeting: "Sveiki! Esu „{business}“ DI asistentas. Kuo galiu padėti?",
      placeholder: "Parašykite žinutę…",
      send: "Siųsti",
      typing: "Asistentas rašo…",
      failed: "Žinutė neišsiųsta.",
      retry: "Bandyti dar kartą",
      unavailable: "Pokalbis šiuo metu nepasiekiamas. Bandykite vėliau.",
      rateLimited: "Per daug žinučių. Šiek tiek palaukite ir bandykite dar kartą.",
      tooLong: "Žinutė per ilga.",
      handedOff: "Jūsų užklausa perduota mūsų komandai. Netrukus su jumis susisieks.",
      language: "Kalba",
      preview: "Peržiūra: pokalbis išjungtas. Įjunkite jį kabinete (Kanalai).",
      newReply: "Naujas atsakymas",
      staff: "Mūsų komanda"
    },
    lv: {
      open: "Atvērt tērzēšanu",
      close: "Aizvērt tērzēšanu",
      subtitle: "MI asistents",
      greeting: "Sveiki! Esmu “{business}” MI asistents. Kā varu palīdzēt?",
      placeholder: "Rakstiet ziņu…",
      send: "Sūtīt",
      typing: "Asistents raksta…",
      failed: "Ziņa netika nosūtīta.",
      retry: "Mēģināt vēlreiz",
      unavailable: "Tērzēšana pašlaik nav pieejama. Mēģiniet vēlāk.",
      rateLimited: "Pārāk daudz ziņu. Mazliet uzgaidiet un mēģiniet vēlreiz.",
      tooLong: "Ziņa ir pārāk gara.",
      handedOff: "Jūsu pieprasījums ir nodots mūsu komandai. Drīzumā ar jums sazināsies.",
      language: "Valoda",
      preview: "Priekšskatījums: tērzēšana ir izslēgta. Ieslēdziet to kabinetā (Kanāli).",
      newReply: "Jauna atbilde",
      staff: "Mūsu komanda"
    },
    et: {
      open: "Ava vestlus",
      close: "Sulge vestlus",
      subtitle: "AI-assistent",
      greeting: "Tere! Olen ettevõtte {business} AI-assistent. Kuidas saan aidata?",
      placeholder: "Kirjutage sõnum…",
      send: "Saada",
      typing: "Assistent kirjutab…",
      failed: "Sõnumit ei saadetud.",
      retry: "Proovi uuesti",
      unavailable: "Vestlus pole praegu saadaval. Proovige hiljem uuesti.",
      rateLimited: "Liiga palju sõnumeid. Oodake veidi ja proovige uuesti.",
      tooLong: "Sõnum on liiga pikk.",
      handedOff: "Teie päring edastati meie meeskonnale. Nad võtavad teiega peagi ühendust.",
      language: "Keel",
      preview: "Eelvaade: vestlus on välja lülitatud. Lülitage see sisse kabinetis (Kanalid).",
      newReply: "Uus vastus",
      staff: "Meie meeskond"
    },
    fa: {
      open: "باز کردن گفتگو",
      close: "بستن گفتگو",
      subtitle: "دستیار هوش مصنوعی",
      greeting: "سلام! من دستیار هوش مصنوعی {business} هستم. چطور می‌توانم کمک کنم؟",
      placeholder: "پیام خود را بنویسید…",
      send: "ارسال",
      typing: "دستیار در حال نوشتن است…",
      failed: "پیام ارسال نشد.",
      retry: "تلاش دوباره",
      unavailable: "گفتگو در حال حاضر در دسترس نیست. لطفاً بعداً دوباره تلاش کنید.",
      rateLimited: "پیام‌ها بیش از حد زیاد است. لطفاً کمی صبر کنید و دوباره تلاش کنید.",
      tooLong: "پیام بیش از حد طولانی است.",
      handedOff: "درخواست شما به تیم ما ارسال شد. به‌زودی با شما تماس می‌گیرند.",
      language: "زبان",
      preview: "پیش‌نمایش: گفتگو خاموش است. آن را در کابینت (کانال‌ها) روشن کنید.",
      newReply: "پاسخ جدید",
      staff: "تیم ما"
    },
    ur: {
      open: "چیٹ کھولیں",
      close: "چیٹ بند کریں",
      subtitle: "AI معاون",
      greeting: "السلام علیکم! میں {business} کا AI معاون ہوں۔ میں آپ کی کیا مدد کر سکتا ہوں؟",
      placeholder: "پیغام لکھیں…",
      send: "بھیجیں",
      typing: "معاون لکھ رہا ہے…",
      failed: "پیغام نہیں بھیجا گیا۔",
      retry: "دوبارہ کوشش کریں",
      unavailable: "چیٹ اس وقت دستیاب نہیں ہے۔ براہ کرم بعد میں کوشش کریں۔",
      rateLimited: "بہت زیادہ پیغامات۔ تھوڑا انتظار کریں اور دوبارہ کوشش کریں۔",
      tooLong: "پیغام بہت لمبا ہے۔",
      handedOff: "آپ کی درخواست ہماری ٹیم کو بھیج دی گئی ہے۔ وہ جلد آپ سے رابطہ کریں گے۔",
      language: "زبان",
      preview: "پیش نظارہ: چیٹ بند ہے۔ اسے کیبنٹ (چینلز) میں آن کریں۔",
      newReply: "نیا جواب",
      staff: "ہماری ٹیم"
    },
    fi: {
      open: "Avaa chat",
      close: "Sulje chat",
      subtitle: "Tekoälyavustaja",
      greeting: "Hei! Olen yrityksen {business} tekoälyavustaja. Miten voin auttaa?",
      placeholder: "Kirjoita viesti…",
      send: "Lähetä",
      typing: "Avustaja kirjoittaa…",
      failed: "Viestiä ei lähetetty.",
      retry: "Yritä uudelleen",
      unavailable: "Chat ei ole juuri nyt käytettävissä. Yritä myöhemmin uudelleen.",
      rateLimited: "Liian monta viestiä. Odota hetki ja yritä uudelleen.",
      tooLong: "Viesti on liian pitkä.",
      handedOff: "Pyyntösi on välitetty tiimillemme. He ottavat sinuun pian yhteyttä.",
      language: "Kieli",
      preview: "Esikatselu: chat on pois päältä. Ota se käyttöön hallintapaneelissa (Kanavat).",
      newReply: "Uusi vastaus",
      staff: "Tiimimme"
    },
    hi: {
      open: "चैट खोलें",
      close: "चैट बंद करें",
      subtitle: "AI सहायक",
      greeting: "नमस्ते! मैं {business} का AI सहायक हूँ। मैं आपकी क्या मदद कर सकता हूँ?",
      placeholder: "संदेश लिखें…",
      send: "भेजें",
      typing: "सहायक लिख रहा है…",
      failed: "संदेश नहीं भेजा गया।",
      retry: "फिर से कोशिश करें",
      unavailable: "चैट अभी उपलब्ध नहीं है। कृपया बाद में कोशिश करें।",
      rateLimited: "बहुत अधिक संदेश। कृपया थोड़ा रुकें और फिर से कोशिश करें।",
      tooLong: "संदेश बहुत लंबा है।",
      handedOff: "आपका अनुरोध हमारी टीम को भेज दिया गया है। वे जल्द ही आपसे संपर्क करेंगे।",
      language: "भाषा",
      preview: "पूर्वावलोकन: यह चैट बंद है। इसे कैबिनेट (चैनल) में चालू करें।",
      newReply: "नया जवाब",
      staff: "हमारी टीम"
    },
    ko: {
      open: "채팅 열기",
      close: "채팅 닫기",
      subtitle: "AI 어시스턴트",
      greeting: "안녕하세요! {business}의 AI 어시스턴트입니다. 무엇을 도와드릴까요?",
      placeholder: "메시지를 입력하세요…",
      send: "보내기",
      typing: "어시스턴트가 입력 중…",
      failed: "메시지를 보내지 못했습니다.",
      retry: "다시 시도",
      unavailable: "지금은 채팅을 이용할 수 없습니다. 나중에 다시 시도해 주세요.",
      rateLimited: "메시지가 너무 많습니다. 잠시 후 다시 시도해 주세요.",
      tooLong: "메시지가 너무 깁니다.",
      handedOff: "요청이 담당 팀에 전달되었습니다. 곧 연락드리겠습니다.",
      language: "언어",
      preview: "미리보기: 채팅이 꺼져 있습니다. 관리 화면(채널)에서 켜 주세요.",
      newReply: "새 답변",
      staff: "담당 팀"
    },
    nb: {
      open: "Åpne chat",
      close: "Lukk chat",
      subtitle: "KI-assistent",
      greeting: "Hei! Jeg er KI-assistenten til {business}. Hvordan kan jeg hjelpe?",
      placeholder: "Skriv en melding…",
      send: "Send",
      typing: "Assistenten skriver…",
      failed: "Meldingen ble ikke sendt.",
      retry: "Prøv igjen",
      unavailable: "Chatten er ikke tilgjengelig akkurat nå. Prøv igjen senere.",
      rateLimited: "For mange meldinger. Vent litt og prøv igjen.",
      tooLong: "Meldingen er for lang.",
      handedOff: "Forespørselen din er sendt videre til teamet vårt. De tar snart kontakt.",
      language: "Språk",
      preview: "Forhåndsvisning: chatten er slått av. Slå den på i kontrollpanelet (Kanaler).",
      newReply: "Nytt svar",
      staff: "Teamet vårt"
    },
    uz: {
      open: "Chatni ochish",
      close: "Chatni yopish",
      subtitle: "AI yordamchi",
      greeting: "Assalomu alaykum! Men {business} AI yordamchisiman. Qanday yordam bera olaman?",
      placeholder: "Xabar yozing…",
      send: "Yuborish",
      typing: "Yordamchi yozmoqda…",
      failed: "Xabar yuborilmadi.",
      retry: "Qayta urinish",
      unavailable: "Chat hozir mavjud emas. Keyinroq qayta urinib ko‘ring.",
      rateLimited: "Xabarlar juda ko‘p. Biroz kuting va qayta urinib ko‘ring.",
      tooLong: "Xabar juda uzun.",
      handedOff: "So‘rovingiz jamoamizga yuborildi. Tez orada siz bilan bog‘lanishadi.",
      language: "Til",
      preview: "Oldindan ko‘rish: chat o‘chirilgan. Uni kabinetda (Kanallar) yoqing.",
      newReply: "Yangi javob",
      staff: "Jamoamiz"
    },
    vi: {
      open: "Mở trò chuyện",
      close: "Đóng trò chuyện",
      subtitle: "Trợ lý AI",
      greeting: "Xin chào! Tôi là trợ lý AI của {business}. Tôi có thể giúp gì cho bạn?",
      placeholder: "Nhập tin nhắn…",
      send: "Gửi",
      typing: "Trợ lý đang soạn tin…",
      failed: "Không gửi được tin nhắn.",
      retry: "Thử lại",
      unavailable: "Hiện không thể trò chuyện. Vui lòng thử lại sau.",
      rateLimited: "Quá nhiều tin nhắn. Vui lòng đợi một chút rồi thử lại.",
      tooLong: "Tin nhắn quá dài.",
      handedOff: "Yêu cầu của bạn đã được chuyển cho đội ngũ của chúng tôi. Họ sẽ sớm liên hệ với bạn.",
      language: "Ngôn ngữ",
      preview: "Xem trước: trò chuyện đang tắt. Hãy bật trong bảng quản lý (Kênh).",
      newReply: "Phản hồi mới",
      staff: "Đội ngũ của chúng tôi"
    }
  };

  var CSS = [
    ":host{all:initial;}",
    ".aw{--aw-accent:" + DEFAULT_ACCENT + ";--aw-on-accent:#fff;--aw-bg:#fff;--aw-fg:#111827;",
    "--aw-muted:#6b7280;--aw-bubble:#f3f4f6;--aw-line:#e5e7eb;--aw-danger:#b91c1c;",
    "--aw-danger-bg:#fef2f2;--aw-shadow:0 12px 40px rgba(17,24,39,.22);",
    "font-family:system-ui,-apple-system,'Segoe UI',Roboto,'Noto Sans','Noto Sans Georgian',",
    "'Noto Sans Hebrew','Noto Sans Arabic',sans-serif;font-size:15px;line-height:1.45;",
    "color:var(--aw-fg);-webkit-font-smoothing:antialiased;}",
    "@media (prefers-color-scheme:dark){.aw{--aw-bg:#111827;--aw-fg:#f9fafb;--aw-muted:#9ca3af;",
    "--aw-bubble:#1f2937;--aw-line:#374151;--aw-danger:#fca5a5;--aw-danger-bg:#3b1414;",
    "--aw-shadow:0 12px 40px rgba(0,0,0,.6);}}",
    ".aw *,.aw *::before,.aw *::after{box-sizing:border-box;}",
    ".aw button,.aw textarea,.aw select{font:inherit;}",
    ".aw select{color:inherit;}",
    ".aw-launcher{position:fixed;bottom:20px;right:20px;width:56px;height:56px;border:0;",
    "border-radius:50%;background:var(--aw-accent);color:var(--aw-on-accent);cursor:pointer;",
    "box-shadow:var(--aw-shadow);display:flex;align-items:center;justify-content:center;",
    "z-index:2147483000;padding:0;transition:transform .15s ease;}",
    ".aw-launcher:hover{transform:scale(1.05);}",
    ".aw-left .aw-launcher{right:auto;left:20px;}",
    ".aw-launcher svg{width:26px;height:26px;fill:none;stroke:currentColor;stroke-width:2;",
    "stroke-linecap:round;stroke-linejoin:round;}",
    ".aw-badge{position:absolute;top:4px;right:4px;width:12px;height:12px;border-radius:50%;",
    "background:#ef4444;border:2px solid var(--aw-bg);display:none;}",
    ".aw-unread .aw-badge{display:block;}",
    ".aw-panel{position:fixed;bottom:88px;right:20px;width:380px;max-width:calc(100vw - 40px);",
    "height:min(620px,calc(100vh - 120px));background:var(--aw-bg);border-radius:16px;",
    "box-shadow:var(--aw-shadow);display:flex;flex-direction:column;overflow:hidden;",
    "z-index:2147483000;border:1px solid var(--aw-line);}",
    ".aw-left .aw-panel{right:auto;left:20px;}",
    ".aw-panel[hidden]{display:none;}",
    ".aw-header{background:var(--aw-accent);color:var(--aw-on-accent);padding:14px 12px;",
    "padding-inline-start:16px;",
    "display:flex;align-items:center;gap:8px;flex:none;}",
    ".aw-heading{flex:1;min-width:0;}",
    ".aw-title{margin:0;font-size:16px;font-weight:600;line-height:1.3;overflow:hidden;",
    "text-overflow:ellipsis;white-space:nowrap;}",
    ".aw-subtitle{margin:0;font-size:12.5px;opacity:.85;}",
    ".aw-language{background:transparent;border:1px solid currentColor;border-radius:8px;",
    "padding:4px 6px;font-size:13px;max-width:120px;cursor:pointer;}",
    ".aw-language option{color:#111827;background:#fff;}",
    ".aw-icon-button{border:0;background:transparent;color:inherit;width:36px;height:36px;",
    "border-radius:8px;cursor:pointer;display:flex;align-items:center;justify-content:center;",
    "padding:0;flex:none;}",
    ".aw-icon-button:hover{background:rgba(255,255,255,.16);}",
    ".aw-icon-button svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:2;",
    "stroke-linecap:round;stroke-linejoin:round;}",
    ".aw-banner{margin:0;padding:8px 16px;font-size:13px;background:#fef3c7;color:#78350f;flex:none;}",
    ".aw-log{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:8px;",
    "overscroll-behavior:contain;}",
    ".aw-message{max-width:85%;padding:9px 13px;border-radius:16px;white-space:pre-wrap;",
    "overflow-wrap:anywhere;text-align:start;}",
    ".aw-assistant{align-self:flex-start;background:var(--aw-bubble);border-end-start-radius:4px;}",
    ".aw-staff{align-self:flex-start;background:var(--aw-bubble);border-end-start-radius:4px;",
    "border-inline-start:3px solid var(--aw-accent);}",
    ".aw-author{display:block;font-size:12px;font-weight:600;color:var(--aw-muted);margin-bottom:2px;}",
    ".aw-visitor{align-self:flex-end;background:var(--aw-accent);color:var(--aw-on-accent);",
    "border-end-end-radius:4px;}",
    ".aw-visitor a{color:inherit;}",
    ".aw-message a{text-decoration:underline;overflow-wrap:anywhere;}",
    // Links keep the bubble's text colour (and the underline): the accent can
    // be unreadable on the bubble, in dark mode above all.
    ".aw-assistant a,.aw-staff a{color:inherit;}",
    ".aw-pending{opacity:.7;}",
    ".aw-notice{align-self:center;max-width:92%;text-align:center;font-size:13px;color:var(--aw-muted);",
    "padding:4px 8px;}",
    ".aw-error{align-self:flex-end;display:flex;align-items:center;gap:8px;font-size:13px;",
    "color:var(--aw-danger);background:var(--aw-danger-bg);padding:6px 10px;border-radius:10px;",
    "max-width:92%;}",
    ".aw-error-text{flex:1;}",
    ".aw-error-detail{display:block;margin-top:2px;opacity:.8;font-size:12px;}",
    ".aw-retry{border:1px solid currentColor;background:transparent;color:inherit;border-radius:8px;",
    "padding:3px 10px;cursor:pointer;font-size:13px;}",
    ".aw-typing{align-self:flex-start;background:var(--aw-bubble);border-radius:16px;",
    "padding:12px 14px;display:flex;gap:4px;}",
    ".aw-typing span{width:7px;height:7px;border-radius:50%;background:var(--aw-muted);",
    "animation:aw-blink 1.2s infinite ease-in-out;}",
    ".aw-typing span:nth-child(2){animation-delay:.2s;}",
    ".aw-typing span:nth-child(3){animation-delay:.4s;}",
    "@keyframes aw-blink{0%,80%,100%{opacity:.25;}40%{opacity:1;}}",
    ".aw-composer{display:flex;align-items:flex-end;gap:8px;padding:10px 12px;",
    "border-top:1px solid var(--aw-line);flex:none;background:var(--aw-bg);}",
    ".aw-input{flex:1;resize:none;border:1px solid var(--aw-line);border-radius:12px;",
    "padding:9px 12px;max-height:132px;min-height:42px;background:var(--aw-bg);line-height:1.4;",
    "color:var(--aw-fg);",
    "font-size:16px;}",
    ".aw-input::placeholder{color:var(--aw-muted);}",
    ".aw-send{border:0;border-radius:12px;background:var(--aw-accent);color:var(--aw-on-accent);",
    "width:42px;height:42px;cursor:pointer;display:flex;align-items:center;justify-content:center;",
    "padding:0;flex:none;}",
    ".aw-send:disabled{opacity:.45;cursor:default;}",
    ".aw-send svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:2;",
    "stroke-linecap:round;stroke-linejoin:round;}",
    "[dir=rtl] .aw-send svg{transform:scaleX(-1);}",
    ".aw-sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;",
    "clip:rect(0,0,0,0);white-space:nowrap;border:0;}",
    ".aw button:focus-visible,.aw select:focus-visible,.aw textarea:focus-visible,",
    ".aw a:focus-visible{outline:2px solid var(--aw-accent);outline-offset:2px;}",
    ".aw-header button:focus-visible,.aw-header select:focus-visible,",
    ".aw-launcher:focus-visible{outline-color:var(--aw-on-accent);outline-offset:-4px;}",
    ".aw-input:focus-visible{outline-offset:0;}",
    "@media (max-width:480px){.aw-panel,.aw-left .aw-panel{inset:0;width:100%;max-width:none;",
    "height:100%;border-radius:0;border:0;}.aw-open .aw-launcher{display:none;}}",
    "@media (prefers-reduced-motion:reduce){.aw-launcher{transition:none;}",
    ".aw-typing span{animation:none;opacity:.6;}}"
  ].join("");

  var script = findOwnScript();
  if (!script) {
    return;
  }

  var businessId = (
    script.getAttribute(BUSINESS_ATTRIBUTE) ||
    script.getAttribute("data-business-id") ||
    ""
  ).trim();
  if (!businessId) {
    warn("the script tag needs a " + BUSINESS_ATTRIBUTE + " attribute.");
    return;
  }

  var loaded = (window.__assistantWorkshopChat = window.__assistantWorkshopChat || {});
  if (loaded[businessId]) {
    return;
  }
  loaded[businessId] = true;

  var apiBase = resolveApiBase(script);
  var configUrl = apiBase + CONFIG_PATH.replace("{business_id}", encodeURIComponent(businessId));
  var messagesUrl =
    apiBase + MESSAGES_PATH.replace("{business_id}", encodeURIComponent(businessId));
  var storagePrefix = STORAGE_PREFIX + businessId + ":";

  start();

  function start() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", start, { once: true });
      return;
    }
    requestJson(configUrl, null).then(
      function (result) {
        var config = result.body;
        var isPreview = script.getAttribute("data-preview") === "true";
        if (!result.ok || !config || typeof config !== "object") {
          warn("the chat configuration could not be loaded (HTTP " + result.status + ").");
          return;
        }
        if (!config.is_enabled && !isPreview) {
          info("the chat is switched off for this business.");
          return;
        }
        mount(config, isPreview);
      },
      function () {
        warn("the chat configuration could not be loaded.");
      }
    );
  }

  function mount(config, isPreview) {
    var showPreviewBanner = isPreview && !config.is_enabled;
    var host = document.createElement("div");
    host.setAttribute("data-assistant-workshop-chat", "");
    if (!host.attachShadow) {
      warn("this browser does not support the chat widget.");
      return;
    }
    var root = host.attachShadow({ mode: "open" });
    applyStyles(root);

    var state = {
      config: config,
      language: chooseLanguage(config),
      sessionKey: loadSessionKey(),
      history: loadHistory(),
      isOpen: false,
      isSending: false,
      pendingItem: null,
      handoffNoticeShown: false,
      // Polling for staff replies (see the header comment).
      cursor: storageGet(localStorageOrNull(), storagePrefix + "cursor"),
      isHandedOff: storageGet(localStorageOrNull(), storagePrefix + "handoff") === "1",
      handoffAt: Number(storageGet(localStorageOrNull(), storagePrefix + "handoff-at")) || 0,
      // The visitor's last exchange (an answer or new messages), any tab.
      activityAt: Number(storageGet(localStorageOrNull(), storagePrefix + "activity-at")) || 0,
      // The history as this tab last read or wrote it (other tabs change it).
      storedHistory: storageGet(localStorageOrNull(), storagePrefix + "history"),
      pollTimer: null,
      pollDelay: POLL_FIRST_DELAY_MS,
      isPolling: false,
      pollStopped: false
    };
    state.handoffNoticeShown = state.history.some(function (item) {
      return item.role === "notice";
    });

    var accent = chooseAccent(script.getAttribute("data-color"), config.accent_color);
    var wrapper = el("div", "aw");
    if (accent) {
      wrapper.style.setProperty("--aw-accent", accent);
      wrapper.style.setProperty("--aw-on-accent", readableTextColor(accent));
    }
    if (choosePosition(script.getAttribute("data-position"), config.position) === "left") {
      wrapper.className += " aw-left";
    }

    var panelId = "aw-panel-" + Math.random().toString(36).slice(2);
    var launcher = el("button", "aw-launcher");
    launcher.type = "button";
    launcher.setAttribute("aria-controls", panelId);
    launcher.setAttribute("aria-expanded", "false");
    launcher.appendChild(chatIcon());
    launcher.appendChild(el("span", "aw-badge"));

    var panel = el("div", "aw-panel");
    panel.id = panelId;
    panel.hidden = true;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "false");

    var header = el("div", "aw-header");
    var heading = el("div", "aw-heading");
    var title = el("h2", "aw-title");
    title.textContent = config.business_name || "";
    title.setAttribute("dir", "auto");
    var subtitle = el("p", "aw-subtitle");
    heading.appendChild(title);
    heading.appendChild(subtitle);
    header.appendChild(heading);

    var languageSelect = null;
    var languages = Array.isArray(config.languages) ? config.languages : [];
    if (languages.length > 1) {
      languageSelect = el("select", "aw-language");
      languages.forEach(function (language) {
        var option = document.createElement("option");
        option.value = language.tag;
        option.textContent = language.native_name || language.tag;
        option.setAttribute("dir", language.direction === "rtl" ? "rtl" : "ltr");
        languageSelect.appendChild(option);
      });
      languageSelect.value = state.language;
      languageSelect.addEventListener("change", function () {
        state.language = languageSelect.value;
        storageSet(localStorageOrNull(), storagePrefix + "language", state.language);
        applyLanguage();
      });
      header.appendChild(languageSelect);
    }

    var closeButton = el("button", "aw-icon-button");
    closeButton.type = "button";
    closeButton.appendChild(closeIcon());
    closeButton.addEventListener("click", function () {
      setOpen(false);
    });
    header.appendChild(closeButton);
    panel.appendChild(header);

    var banner = null;
    if (showPreviewBanner) {
      banner = el("p", "aw-banner");
      banner.setAttribute("role", "note");
      panel.appendChild(banner);
    }

    // The conversation is re-rendered as a whole, so it is not a live region:
    // replies and errors are announced through the status element below.
    var log = el("div", "aw-log");
    log.tabIndex = 0;
    panel.appendChild(log);

    // Outside the panel: a hidden (display:none) panel would silence it.
    var status = el("p", "aw-sr");
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");

    var composer = el("form", "aw-composer");
    composer.setAttribute("novalidate", "");
    var inputLabel = el("label", "aw-sr");
    var input = el("textarea", "aw-input");
    input.id = panelId + "-input";
    inputLabel.htmlFor = input.id;
    input.rows = 1;
    input.maxLength = MAX_MESSAGE_LENGTH;
    input.setAttribute("dir", "auto");
    input.setAttribute("autocomplete", "off");
    input.setAttribute("enterkeyhint", "send");
    var sendButton = el("button", "aw-send");
    sendButton.type = "submit";
    sendButton.disabled = true;
    sendButton.appendChild(sendIcon());
    composer.appendChild(inputLabel);
    composer.appendChild(input);
    composer.appendChild(sendButton);
    panel.appendChild(composer);

    wrapper.appendChild(panel);
    wrapper.appendChild(launcher);
    wrapper.appendChild(status);
    root.appendChild(wrapper);
    document.body.appendChild(host);

    var typingRow = null;

    launcher.addEventListener("click", function () {
      setOpen(!state.isOpen);
    });
    wrapper.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && state.isOpen) {
        event.stopPropagation();
        setOpen(false);
      }
    });
    input.addEventListener("input", function () {
      autoSize();
      updateSendButton();
    });
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        submit();
      }
    });
    composer.addEventListener("submit", function (event) {
      event.preventDefault();
      submit();
    });

    applyLanguage();
    exposeApi();
    // data-open only sets the first view of the tab session: once the visitor
    // has opened or closed the chat, their choice is kept on every page (a
    // full-screen panel on a phone must not come back on each page).
    var savedOpen = storageGet(sessionStorageOrNull(), storagePrefix + "open");
    if (savedOpen === "1" || (savedOpen === null && script.getAttribute("data-open") === "true")) {
      setOpen(true, true);
    }
    window.addEventListener("storage", function (event) {
      if (event.key === storagePrefix + "history" || event.key === storagePrefix + "cursor") {
        adoptStoredState();
      }
    });
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") {
        stopPolling();
      } else {
        schedulePoll(0);
      }
    });
    schedulePoll(0);

    function applyLanguage() {
      var direction = languageDirection(config, state.language);
      wrapper.setAttribute("dir", direction);
      wrapper.setAttribute("lang", state.language);
      updateLauncherLabel();
      panel.setAttribute("aria-label", config.business_name || text("subtitle"));
      log.setAttribute("aria-label", config.business_name || text("subtitle"));
      subtitle.textContent = text("subtitle");
      closeButton.setAttribute("aria-label", text("close"));
      closeButton.title = text("close");
      if (languageSelect) {
        languageSelect.setAttribute("aria-label", text("language"));
      }
      if (banner) {
        banner.textContent = text("preview");
      }
      input.placeholder = text("placeholder");
      inputLabel.textContent = text("placeholder");
      sendButton.setAttribute("aria-label", text("send"));
      sendButton.title = text("send");
      renderLog();
    }

    function setOpen(isOpen, keepFocus) {
      state.isOpen = isOpen;
      panel.hidden = !isOpen;
      launcher.setAttribute("aria-expanded", isOpen ? "true" : "false");
      if (isOpen) {
        wrapper.classList.remove("aw-unread");
      }
      updateLauncherLabel();
      launcher.replaceChild(isOpen ? closeIcon() : chatIcon(), launcher.firstChild);
      wrapper.classList.toggle("aw-open", isOpen);
      storageSet(sessionStorageOrNull(), storagePrefix + "open", isOpen ? "1" : "0");
      if (isOpen) {
        scrollToEnd();
        if (!keepFocus) {
          input.focus();
        }
        state.pollDelay = POLL_FIRST_DELAY_MS;
        schedulePoll(0);
      } else if (!keepFocus) {
        launcher.focus();
      }
    }

    // The launcher's name also tells a screen reader about an unread reply.
    function updateLauncherLabel() {
      var label = text(state.isOpen ? "close" : "open");
      if (!state.isOpen && wrapper.classList.contains("aw-unread")) {
        label += " (" + text("newReply") + ")";
      }
      launcher.setAttribute("aria-label", label);
      launcher.title = label;
    }

    // A reply arrived: read it out when the panel is open, else mark the
    // launcher unread and say that a reply came.
    function noteReply(replyText) {
      if (state.isOpen) {
        announce(replyText);
        return;
      }
      wrapper.classList.add("aw-unread");
      updateLauncherLabel();
      announce(text("newReply"));
    }

    function exposeApi() {
      window.AssistantWorkshopChat = {
        open: function () {
          setOpen(true);
        },
        close: function () {
          setOpen(false);
        },
        toggle: function () {
          setOpen(!state.isOpen);
        }
      };
    }

    function submit() {
      var messageText = input.value.trim();
      if (!messageText || state.isSending) {
        return;
      }
      if (messageText.length > MAX_MESSAGE_LENGTH) {
        announce(text("tooLong"));
        return;
      }
      input.value = "";
      autoSize();
      adoptStoredState();
      var item = { role: "visitor", text: messageText, failed: false };
      state.history.push(item);
      send(item);
    }

    function send(item) {
      stopPolling();
      state.isSending = true;
      state.pendingItem = item;
      item.failed = false;
      item.error = "";
      // Stored before sending: if the visitor leaves while the answer is
      // being written, the next page shows the question and fetches it.
      item.pending = true;
      item.sentAt = Date.now();
      saveHistory();
      updateSendButton();
      renderLog();
      showTyping(true);
      requestJson(messagesUrl, {
        session_key: state.sessionKey,
        text: item.text
      }).then(
        function (result) {
          showTyping(false);
          state.isSending = false;
          state.pendingItem = null;
          if (result.ok && result.body) {
            receiveReply(result.body);
          } else {
            markFailed(item, errorTextFor(result.status), previewDetail(result));
          }
          updateSendButton();
          state.pollDelay = POLL_FIRST_DELAY_MS;
          if (result.ok) {
            // Catch up once: the answer again (skipped by id) and any staff
            // message written while the assistant was answering.
            poll(true);
          } else {
            schedulePoll(POLL_FIRST_DELAY_MS);
          }
        },
        function () {
          showTyping(false);
          state.isSending = false;
          state.pendingItem = null;
          markFailed(item, text("failed"), "", true);
          updateSendButton();
          schedulePoll(POLL_FIRST_DELAY_MS);
        }
      );
    }

    function receiveReply(reply) {
      clearPending();
      if (typeof reply.text === "string" && reply.text) {
        state.history.push({
          role: "assistant",
          id: typeof reply.message_id === "string" ? reply.message_id : undefined,
          text: reply.text,
          direction: reply.direction === "rtl" ? "rtl" : "ltr"
        });
        noteReply(reply.text);
      } else if (reply.is_handed_off && !state.handoffNoticeShown) {
        state.handoffNoticeShown = true;
        state.history.push({ role: "notice", key: "handedOff" });
        announce(text("handedOff"));
      }
      // The position only moves forward by polling (right after this reply),
      // so staff messages written meanwhile are never skipped.
      if (!state.cursor && typeof reply.cursor === "string" && reply.cursor) {
        saveCursor(reply.cursor);
      }
      setHandedOff(reply.is_handed_off === true);
      markActivity();
      saveHistory();
      renderLog();
    }

    // --- answers the widget has not shown yet -----------------------------

    function shouldPoll() {
      if (state.pollStopped || document.visibilityState === "hidden") {
        return false;
      }
      if (state.isHandedOff) {
        return true;
      }
      if (awaitingAnswer() && !state.isSending) {
        return true;
      }
      var lastAt = Math.max(state.handoffAt, state.activityAt);
      return state.isOpen && lastAt > 0 && Date.now() - lastAt < HANDOFF_MEMORY_MS;
    }

    // The visitor's last message was sent (maybe from a page since left) and
    // its answer has not been shown yet.
    function awaitingAnswer() {
      for (var index = state.history.length - 1; index >= 0; index -= 1) {
        var item = state.history[index];
        if (item.role === "visitor") {
          return isAwaiting(item);
        }
      }
      return false;
    }

    function isAwaiting(item) {
      return item.pending === true && Date.now() - (item.sentAt || 0) < REQUEST_TIMEOUT_MS;
    }

    function clearPending() {
      state.history.forEach(function (item) {
        if (item.role === "visitor") {
          item.pending = false;
        }
      });
    }

    function markActivity() {
      state.activityAt = Date.now();
      storageSet(localStorageOrNull(), storagePrefix + "activity-at", String(state.activityAt));
    }

    // The history and position another tab saved; this tab's unsent and
    // failed messages stay at the end.
    function adoptStoredState() {
      if (state.isSending) {
        // Adopted after the answer: the message being sent is in the history.
        return;
      }
      var raw = storageGet(localStorageOrNull(), storagePrefix + "history");
      if (raw !== state.storedHistory) {
        var unsaved = state.history.filter(function (item) {
          return item.failed;
        });
        state.history = loadHistory().concat(unsaved);
        state.storedHistory = raw;
        state.handoffNoticeShown = state.history.some(function (item) {
          return item.role === "notice";
        });
        renderLog();
      }
      var cursor = storageGet(localStorageOrNull(), storagePrefix + "cursor");
      if (cursor) {
        state.cursor = cursor;
      }
      state.activityAt = Math.max(
        state.activityAt,
        Number(storageGet(localStorageOrNull(), storagePrefix + "activity-at")) || 0
      );
    }

    function schedulePoll(delay) {
      stopPolling();
      if (!shouldPoll() || state.isSending) {
        return;
      }
      state.pollTimer = window.setTimeout(function () {
        poll(false);
      }, delay);
    }

    function stopPolling() {
      if (state.pollTimer !== null) {
        window.clearTimeout(state.pollTimer);
        state.pollTimer = null;
      }
    }

    function nextDelay() {
      var limit = state.isOpen ? POLL_MAX_DELAY_OPEN_MS : POLL_MAX_DELAY_CLOSED_MS;
      state.pollDelay = Math.min(Math.round(state.pollDelay * POLL_BACKOFF_FACTOR), limit);
      return state.pollDelay;
    }

    function poll(isCatchUp) {
      state.pollTimer = null;
      if (state.isPolling || state.isSending || state.pollStopped) {
        return;
      }
      if (isCatchUp !== true && !shouldPoll()) {
        return;
      }
      // Start from the shared position, so another tab's answers are not
      // appended out of order.
      adoptStoredState();
      state.isPolling = true;
      var url = messagesUrl;
      if (state.cursor) {
        url += "?after=" + encodeURIComponent(state.cursor);
      }
      requestJson(url, null, state.sessionKey).then(
        function (result) {
          state.isPolling = false;
          if (result.status === 404) {
            // The chat was switched off: stop asking.
            state.pollStopped = true;
            return;
          }
          if (!result.ok || !result.body || !Array.isArray(result.body.items)) {
            schedulePoll(nextDelay());
            return;
          }
          var added = receiveMessages(result.body);
          if (result.body.has_more === true) {
            schedulePoll(POLL_MORE_DELAY_MS);
          } else if (added > 0) {
            state.pollDelay = POLL_FIRST_DELAY_MS;
            schedulePoll(POLL_FIRST_DELAY_MS);
          } else {
            schedulePoll(nextDelay());
          }
        },
        function () {
          state.isPolling = false;
          schedulePoll(nextDelay());
        }
      );
    }

    function receiveMessages(page) {
      var known = {};
      state.history.forEach(function (item) {
        if (item.id) {
          known[item.id] = true;
        }
      });
      var added = 0;
      var lastText = "";
      page.items.forEach(function (message) {
        if (!message || typeof message.id !== "string" || typeof message.text !== "string") {
          return;
        }
        if (known[message.id] || !message.text) {
          return;
        }
        known[message.id] = true;
        state.history.push({
          role: message.author === "staff" ? "staff" : "assistant",
          id: message.id,
          text: message.text,
          direction: message.direction === "rtl" ? "rtl" : "ltr"
        });
        lastText = message.text;
        added += 1;
      });
      if (typeof page.cursor === "string" && page.cursor) {
        saveCursor(page.cursor);
      }
      setHandedOff(page.is_handed_off === true);
      if (added > 0) {
        clearPending();
        markActivity();
        saveHistory();
        renderLog();
        noteReply(lastText);
      }
      return added;
    }

    function saveCursor(cursor) {
      state.cursor = cursor;
      storageSet(localStorageOrNull(), storagePrefix + "cursor", cursor);
    }

    function setHandedOff(isHandedOff) {
      state.isHandedOff = isHandedOff;
      storageSet(localStorageOrNull(), storagePrefix + "handoff", isHandedOff ? "1" : "0");
      if (isHandedOff) {
        state.handoffAt = Date.now();
        storageSet(localStorageOrNull(), storagePrefix + "handoff-at", String(state.handoffAt));
      }
    }

    // `mayHaveArrived`: the request broke off (network, or the visitor left
    // the page): the API may have the message, so the stored copy stays and
    // the next page looks for its answer. A refused message (an HTTP error)
    // is kept on this page only, for Retry.
    function markFailed(item, message, detail, mayHaveArrived) {
      item.pending = false;
      item.failed = true;
      item.error = message;
      item.detail = detail;
      if (!mayHaveArrived) {
        saveHistory();
      }
      announce(message);
      renderLog();
    }

    function errorTextFor(statusCode) {
      // 404: unknown business or chat switched off; 409: assistant not live.
      if (statusCode === 404 || statusCode === 409) {
        return text("unavailable");
      }
      if (statusCode === 429) {
        return text("rateLimited");
      }
      if (statusCode === 413) {
        return text("tooLong");
      }
      return text("failed");
    }

    // Owners previewing the widget (data-preview) also see the API's reason.
    function previewDetail(result) {
      var message = result.body && typeof result.body.message === "string" ? result.body.message : "";
      return isPreview ? message : "";
    }

    function renderLog() {
      var wasAtEnd = log.scrollHeight - log.scrollTop - log.clientHeight < 40;
      while (log.firstChild) {
        log.removeChild(log.firstChild);
      }
      var greeting = configGreeting(config, state.language);
      log.appendChild(
        greeting
          ? messageRow("assistant", greeting.text, greeting.direction)
          : messageRow("assistant", text("greeting").split("{business}").join(config.business_name || ""))
      );
      state.history.forEach(function (item) {
        if (item.role === "notice") {
          var notice = el("p", "aw-notice");
          notice.textContent = text(item.key || "handedOff");
          log.appendChild(notice);
          return;
        }
        var row = messageRow(item.role, item.text, item.direction, item.role === "staff" ? text("staff") : "");
        if (item === state.pendingItem || (item.role === "visitor" && isAwaiting(item))) {
          row.className += " aw-pending";
        }
        log.appendChild(row);
        if (item.failed) {
          log.appendChild(errorRow(item));
        }
      });
      if (typingRow) {
        log.appendChild(typingRow);
      }
      if (wasAtEnd || state.isSending) {
        scrollToEnd();
      }
    }

    function errorRow(item) {
      var row = el("div", "aw-error");
      row.setAttribute("role", "alert");
      var message = el("span", "aw-error-text");
      message.textContent = item.error || text("failed");
      if (item.detail) {
        var detail = el("span", "aw-error-detail");
        detail.setAttribute("dir", "auto");
        detail.textContent = item.detail;
        message.appendChild(detail);
      }
      var retry = el("button", "aw-retry");
      retry.type = "button";
      retry.textContent = text("retry");
      retry.disabled = state.isSending;
      retry.addEventListener("click", function () {
        if (!state.isSending) {
          send(item);
          input.focus();
        }
      });
      row.appendChild(message);
      row.appendChild(retry);
      return row;
    }

    function showTyping(isTyping) {
      if (isTyping) {
        typingRow = el("div", "aw-typing");
        typingRow.title = text("typing");
        typingRow.appendChild(el("span", ""));
        typingRow.appendChild(el("span", ""));
        typingRow.appendChild(el("span", ""));
        announce(text("typing"));
        log.appendChild(typingRow);
        scrollToEnd();
      } else if (typingRow) {
        if (typingRow.parentNode) {
          typingRow.parentNode.removeChild(typingRow);
        }
        typingRow = null;
      }
    }

    function updateSendButton() {
      sendButton.disabled = state.isSending || input.value.trim() === "";
    }

    function autoSize() {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight + 2, 132) + "px";
    }

    function scrollToEnd() {
      log.scrollTop = log.scrollHeight;
    }

    function announce(message) {
      status.textContent = "";
      window.setTimeout(function () {
        status.textContent = message;
      }, 50);
    }

    function saveHistory() {
      if (state.history.length > MAX_STORED_MESSAGES * 2) {
        state.history.splice(0, state.history.length - MAX_STORED_MESSAGES * 2);
      }
      var stored = state.history
        .filter(function (item) {
          return !item.failed;
        })
        .slice(-MAX_STORED_MESSAGES)
        .map(function (item) {
          return {
            role: item.role,
            id: item.id,
            text: item.text,
            direction: item.direction,
            key: item.key,
            pending: item.pending === true ? true : undefined,
            sentAt: item.pending === true ? item.sentAt : undefined
          };
        });
      // Remembered so this tab does not take its own write for another tab's.
      state.storedHistory = JSON.stringify(stored);
      storageSet(localStorageOrNull(), storagePrefix + "history", state.storedHistory);
    }

    function text(key) {
      return translate(state.language, key);
    }
  }

  // --- language ----------------------------------------------------------

  function chooseLanguage(config) {
    var languages = Array.isArray(config.languages) ? config.languages : [];
    var tags = languages.map(function (language) {
      return String(language.tag);
    });
    var candidates = [];
    var forced = script.getAttribute("data-language");
    if (forced) {
      candidates.push(forced);
    }
    var saved = storageGet(localStorageOrNull(), storagePrefix + "language");
    if (saved) {
      candidates.push(saved);
    }
    var browserLanguages = navigator.languages && navigator.languages.length
      ? navigator.languages
      : [navigator.language || ""];
    candidates = candidates.concat(Array.prototype.slice.call(browserLanguages));
    for (var index = 0; index < candidates.length; index += 1) {
      var match = matchLanguage(String(candidates[index] || ""), tags);
      if (match) {
        return match;
      }
    }
    if (config.default_language && tags.indexOf(config.default_language) !== -1) {
      return config.default_language;
    }
    return tags.length ? tags[0] : config.default_language || "en";
  }

  function matchLanguage(candidate, tags) {
    if (!candidate) {
      return null;
    }
    var lower = candidate.toLowerCase();
    var index;
    for (index = 0; index < tags.length; index += 1) {
      if (tags[index].toLowerCase() === lower) {
        return tags[index];
      }
    }
    var base = baseLanguage(lower);
    for (index = 0; index < tags.length; index += 1) {
      if (baseLanguage(tags[index].toLowerCase()) === base) {
        return tags[index];
      }
    }
    return null;
  }

  function baseLanguage(tag) {
    return String(tag).split(/[-_]/)[0].toLowerCase();
  }

  function languageDirection(config, tag) {
    var languages = Array.isArray(config.languages) ? config.languages : [];
    for (var index = 0; index < languages.length; index += 1) {
      if (languages[index].tag === tag) {
        return languages[index].direction === "rtl" ? "rtl" : "ltr";
      }
    }
    return RTL_LANGUAGES.indexOf(baseLanguage(tag)) !== -1 ? "rtl" : "ltr";
  }

  // The business's greeting for the language (exact tag, then base language).
  function configGreeting(config, tag) {
    var greetings = Array.isArray(config.greetings) ? config.greetings : [];
    var base = null;
    for (var index = 0; index < greetings.length; index += 1) {
      var greeting = greetings[index];
      if (!greeting || typeof greeting.text !== "string" || !greeting.text) {
        continue;
      }
      if (String(greeting.language).toLowerCase() === String(tag).toLowerCase()) {
        return { text: greeting.text, direction: greeting.direction };
      }
      if (!base && baseLanguage(greeting.language) === baseLanguage(tag)) {
        base = { text: greeting.text, direction: greeting.direction };
      }
    }
    return base;
  }

  // The script tag's data-color wins over the colour chosen in the cabinet.
  function chooseAccent(attribute, configured) {
    var candidates = [String(attribute || "").trim(), String(configured || "").trim()];
    for (var index = 0; index < candidates.length; index += 1) {
      if (COLOR_PATTERN.test(candidates[index])) {
        return candidates[index];
      }
    }
    return "";
  }

  function choosePosition(attribute, configured) {
    var fromTag = String(attribute || "").trim().toLowerCase();
    if (POSITIONS.indexOf(fromTag) !== -1) {
      return fromTag;
    }
    var fromConfig = String(configured || "").trim().toLowerCase();
    return POSITIONS.indexOf(fromConfig) !== -1 ? fromConfig : "right";
  }

  function translate(tag, key) {
    var exact = TEXTS[String(tag).toLowerCase()];
    var base = TEXTS[baseLanguage(tag)];
    if (exact && exact[key]) {
      return exact[key];
    }
    if (base && base[key]) {
      return base[key];
    }
    return TEXTS.en[key] || key;
  }

  // --- network -----------------------------------------------------------

  function requestJson(url, body, sessionKey) {
    var controller = typeof AbortController === "function" ? new AbortController() : null;
    var timer = controller
      ? window.setTimeout(function () {
          controller.abort();
        }, REQUEST_TIMEOUT_MS)
      : null;
    var options = {
      method: body ? "POST" : "GET",
      credentials: "omit",
      mode: "cors",
      cache: "no-store",
      referrerPolicy: "strict-origin-when-cross-origin"
    };
    if (body) {
      // text/plain keeps this a simple request (no CORS preflight); the API
      // reads the body as JSON whatever its content type.
      options.headers = { "Content-Type": "text/plain;charset=UTF-8" };
      options.body = JSON.stringify(body);
    } else if (sessionKey) {
      // In a header, so access logs and proxies never record the key.
      options.headers = {};
      options.headers[SESSION_KEY_HEADER] = sessionKey;
    }
    if (controller) {
      options.signal = controller.signal;
    }
    return window.fetch(url, options).then(
      function (response) {
        if (timer) {
          window.clearTimeout(timer);
        }
        return response.text().then(function (raw) {
          var parsed = null;
          try {
            parsed = raw ? JSON.parse(raw) : null;
          } catch (error) {
            parsed = null;
          }
          return { ok: response.ok, status: response.status, body: parsed };
        });
      },
      function (error) {
        if (timer) {
          window.clearTimeout(timer);
        }
        throw error;
      }
    );
  }

  // --- visitor identity and history (localStorage, never cookies) ---------

  function loadSessionKey() {
    var storage = localStorageOrNull();
    var key = storageGet(storage, storagePrefix + "session");
    if (key && SESSION_KEY_PATTERN.test(key)) {
      return key;
    }
    key = "v1_" + randomString(32);
    storageSet(storage, storagePrefix + "session", key);
    return key;
  }

  function loadHistory() {
    var raw = storageGet(localStorageOrNull(), storagePrefix + "history");
    if (!raw) {
      return [];
    }
    try {
      var parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        return [];
      }
      return parsed
        .filter(function (item) {
          return (
            item &&
            (item.role === "notice" ||
              ((item.role === "visitor" || item.role === "assistant" || item.role === "staff") &&
                typeof item.text === "string"))
          );
        })
        .slice(-MAX_STORED_MESSAGES)
        .map(function (item) {
          return {
            role: item.role,
            id: typeof item.id === "string" ? item.id : undefined,
            text: item.text,
            direction: item.direction === "rtl" ? "rtl" : "ltr",
            key: item.key,
            pending: item.pending === true,
            sentAt: typeof item.sentAt === "number" ? item.sentAt : 0,
            failed: false
          };
        });
    } catch (error) {
      return [];
    }
  }

  function randomString(length) {
    var values = new Uint8Array(length);
    var cryptoSource = window.crypto || window.msCrypto;
    if (cryptoSource && cryptoSource.getRandomValues) {
      cryptoSource.getRandomValues(values);
    } else {
      for (var fill = 0; fill < length; fill += 1) {
        values[fill] = Math.floor(Math.random() * 256);
      }
    }
    var result = "";
    for (var index = 0; index < length; index += 1) {
      result += SESSION_KEY_ALPHABET.charAt(values[index] % SESSION_KEY_ALPHABET.length);
    }
    return result;
  }

  function localStorageOrNull() {
    try {
      return window.localStorage;
    } catch (error) {
      return null;
    }
  }

  function sessionStorageOrNull() {
    try {
      return window.sessionStorage;
    } catch (error) {
      return null;
    }
  }

  function storageGet(storage, key) {
    try {
      if (storage) {
        return storage.getItem(key);
      }
    } catch (error) {
      // Storage blocked (privacy mode): keep the value in memory.
    }
    return Object.prototype.hasOwnProperty.call(memoryStorage, key) ? memoryStorage[key] : null;
  }

  function storageSet(storage, key, value) {
    memoryStorage[key] = value;
    try {
      if (storage) {
        storage.setItem(key, value);
      }
    } catch (error) {
      // Quota or privacy mode: the in-memory copy is enough for this page.
    }
  }

  // --- DOM helpers -------------------------------------------------------

  function findOwnScript() {
    if (document.currentScript && document.currentScript.tagName === "SCRIPT") {
      return document.currentScript;
    }
    var scripts = document.getElementsByTagName("script");
    for (var index = scripts.length - 1; index >= 0; index -= 1) {
      var candidate = scripts[index];
      var source = candidate.getAttribute("src") || "";
      if (
        candidate.hasAttribute(BUSINESS_ATTRIBUTE) &&
        source.split("?")[0].slice(-SCRIPT_FILE_NAME.length) === SCRIPT_FILE_NAME
      ) {
        return candidate;
      }
    }
    return null;
  }

  function resolveApiBase(scriptTag) {
    var configured = scriptTag.getAttribute("data-api-base");
    var base = configured;
    if (!base) {
      try {
        var source = new URL(scriptTag.src, window.location.href);
        var path = source.pathname;
        var prefix = path.slice(0, path.length - SCRIPT_FILE_NAME.length);
        base = source.origin + (path.slice(-SCRIPT_FILE_NAME.length) === SCRIPT_FILE_NAME ? prefix : "");
      } catch (error) {
        base = "";
      }
    }
    return String(base).replace(/\/+$/, "");
  }

  function applyStyles(root) {
    // Constructable stylesheets also work on pages whose Content-Security-
    // Policy forbids inline <style> elements.
    try {
      if (root.adoptedStyleSheets !== undefined && typeof CSSStyleSheet === "function") {
        var sheet = new CSSStyleSheet();
        sheet.replaceSync(CSS);
        root.adoptedStyleSheets = [sheet];
        return;
      }
    } catch (error) {
      // Fall back to a <style> element below.
    }
    var style = document.createElement("style");
    style.textContent = CSS;
    root.appendChild(style);
  }

  function messageRow(role, messageText, direction, authorLabel) {
    var row = el("div", "aw-message aw-" + role);
    if (authorLabel) {
      // The label is in the interface language; the message keeps its own
      // direction below it.
      var author = el("span", "aw-author");
      author.textContent = authorLabel;
      row.appendChild(author);
    }
    var body = el("div", "");
    // Each message finds its own direction (a Hebrew reply in an English
    // interface, a phone number in an Arabic one). A business message the
    // API marks right-to-left stays right-to-left even when it opens with a
    // Latin name ("Pizza Roma مفتوح ..."), as long as it has right-to-left
    // letters; "ltr" is never forced (the API also sends it for unknown
    // languages).
    var isRightToLeft =
      role !== "visitor" && direction === "rtl" && RTL_CHARACTER_PATTERN.test(messageText);
    body.setAttribute("dir", isRightToLeft ? "rtl" : "auto");
    if (direction === "rtl" || direction === "ltr") {
      body.setAttribute("data-language-direction", direction);
    }
    appendLinkedText(body, messageText);
    row.appendChild(body);
    return row;
  }

  function appendLinkedText(parent, messageText) {
    var lastIndex = 0;
    var match;
    URL_PATTERN.lastIndex = 0;
    while ((match = URL_PATTERN.exec(messageText)) !== null) {
      var url = match[0].replace(/[.,;:!?)\]]+$/, "");
      if (match.index > lastIndex) {
        parent.appendChild(document.createTextNode(messageText.slice(lastIndex, match.index)));
      }
      var link = document.createElement("a");
      link.href = url;
      link.textContent = url;
      link.target = "_blank";
      link.rel = "noopener noreferrer nofollow";
      parent.appendChild(link);
      lastIndex = match.index + url.length;
      URL_PATTERN.lastIndex = lastIndex;
    }
    if (lastIndex < messageText.length) {
      parent.appendChild(document.createTextNode(messageText.slice(lastIndex)));
    }
  }

  function el(tagName, className) {
    var element = document.createElement(tagName);
    if (className) {
      element.className = className;
    }
    return element;
  }

  function svgIcon(paths) {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    paths.forEach(function (definition) {
      var path = document.createElementNS(SVG_NS, "path");
      path.setAttribute("d", definition);
      svg.appendChild(path);
    });
    return svg;
  }

  function chatIcon() {
    return svgIcon(["M21 12a8 8 0 0 1-11.8 7.04L4 20l1.05-4.2A8 8 0 1 1 21 12z"]);
  }

  function closeIcon() {
    return svgIcon(["M6 6l12 12", "M18 6L6 18"]);
  }

  function sendIcon() {
    return svgIcon(["M4 12l16-8-6 16-2.5-6.5L4 12z", "M11.5 13.5L20 4"]);
  }

  function readableTextColor(hexColor) {
    var hex = hexColor.slice(1);
    if (hex.length === 3) {
      hex = hex.charAt(0) + hex.charAt(0) + hex.charAt(1) + hex.charAt(1) + hex.charAt(2) + hex.charAt(2);
    }
    var channels = [0, 2, 4].map(function (offset) {
      var value = parseInt(hex.slice(offset, offset + 2), 16) / 255;
      return value <= 0.03928 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4);
    });
    var luminance = 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
    // The higher WCAG contrast: with white 1.05/(L+0.05), with #111827
    // (L about 0.0093) (L+0.05)/0.0593.
    return 1.05 / (luminance + 0.05) >= (luminance + 0.05) / 0.0593 ? "#ffffff" : "#111827";
  }

  function warn(message) {
    if (window.console && window.console.warn) {
      window.console.warn("[Assistant Workshop chat] " + message);
    }
  }

  function info(message) {
    if (window.console && window.console.info) {
      window.console.info("[Assistant Workshop chat] " + message);
    }
  }
})();
