/*!
 * Assistant Workshop — website chat widget.
 *
 * Embed (the cabinet gives this snippet; GET /v1/businesses/{id}/channels/web/snippet):
 *   <script src="https://<api>/widget.js" data-tenant="<business id>" async></script>
 *
 * Optional attributes of the script tag:
 *   data-color="#4f46e5"   accent colour (hex)
 *   data-position="left"   launcher in the bottom-left corner (default: right)
 *   data-language="ka"     interface language (default: the visitor's browser
 *                          language among the business languages)
 *   data-open="true"       open the chat panel on load
 *   data-preview="true"    show the widget even while the chat is switched off
 *   data-api-base="https://<api>"   API origin (default: the script's origin)
 *
 * No dependencies and no cookies. The visitor is identified by a random
 * session key kept in localStorage; the widget renders inside a shadow root,
 * so the host page's styles and the widget's styles never mix.
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
      newReply: "New reply"
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
      newReply: "Новый ответ"
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
      newReply: "ახალი პასუხი"
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
      newReply: "Нова відповідь"
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
      newReply: "Yeni yanıt"
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
      newReply: "תשובה חדשה"
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
      newReply: "رد جديد"
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
      newReply: "Neue Antwort"
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
      newReply: "Nouvelle réponse"
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
      newReply: "Nueva respuesta"
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
      newReply: "Nuova risposta"
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
      newReply: "Nova resposta"
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
      newReply: "Nowa odpowiedź"
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
      newReply: "新回复"
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
      newReply: "新しい返信"
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
    ".aw-visitor{align-self:flex-end;background:var(--aw-accent);color:var(--aw-on-accent);",
    "border-end-end-radius:4px;}",
    ".aw-visitor a{color:inherit;}",
    ".aw-message a{text-decoration:underline;overflow-wrap:anywhere;}",
    ".aw-assistant a{color:var(--aw-accent);}",
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
      handoffNoticeShown: false
    };
    state.handoffNoticeShown = state.history.some(function (item) {
      return item.role === "notice";
    });

    var accent = (script.getAttribute("data-color") || "").trim();
    var wrapper = el("div", "aw");
    if (COLOR_PATTERN.test(accent)) {
      wrapper.style.setProperty("--aw-accent", accent);
      wrapper.style.setProperty("--aw-on-accent", readableTextColor(accent));
    }
    if (script.getAttribute("data-position") === "left") {
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

    var status = el("p", "aw-sr");
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    panel.appendChild(status);

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
    if (
      script.getAttribute("data-open") === "true" ||
      storageGet(sessionStorageOrNull(), storagePrefix + "open") === "1"
    ) {
      setOpen(true, true);
    }

    function applyLanguage() {
      var direction = languageDirection(config, state.language);
      wrapper.setAttribute("dir", direction);
      wrapper.setAttribute("lang", state.language);
      launcher.setAttribute("aria-label", text(state.isOpen ? "close" : "open"));
      launcher.title = text(state.isOpen ? "close" : "open");
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
      launcher.setAttribute("aria-label", text(isOpen ? "close" : "open"));
      launcher.title = text(isOpen ? "close" : "open");
      launcher.replaceChild(isOpen ? closeIcon() : chatIcon(), launcher.firstChild);
      wrapper.classList.toggle("aw-open", isOpen);
      storageSet(sessionStorageOrNull(), storagePrefix + "open", isOpen ? "1" : "0");
      if (isOpen) {
        wrapper.classList.remove("aw-unread");
        scrollToEnd();
        if (!keepFocus) {
          input.focus();
        }
      } else if (!keepFocus) {
        launcher.focus();
      }
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
      var item = { role: "visitor", text: messageText, failed: false };
      state.history.push(item);
      send(item);
    }

    function send(item) {
      state.isSending = true;
      state.pendingItem = item;
      item.failed = false;
      item.error = "";
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
        },
        function () {
          showTyping(false);
          state.isSending = false;
          state.pendingItem = null;
          markFailed(item, text("failed"), "");
          updateSendButton();
        }
      );
    }

    function receiveReply(reply) {
      if (typeof reply.text === "string" && reply.text) {
        state.history.push({
          role: "assistant",
          text: reply.text,
          direction: reply.direction === "rtl" ? "rtl" : "ltr"
        });
        announce(reply.text);
        if (!state.isOpen) {
          wrapper.classList.add("aw-unread");
        }
      } else if (reply.is_handed_off && !state.handoffNoticeShown) {
        state.handoffNoticeShown = true;
        state.history.push({ role: "notice", key: "handedOff" });
        announce(text("handedOff"));
      }
      saveHistory();
      renderLog();
    }

    function markFailed(item, message, detail) {
      item.failed = true;
      item.error = message;
      item.detail = detail;
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
      log.appendChild(
        messageRow("assistant", text("greeting").split("{business}").join(config.business_name || ""))
      );
      state.history.forEach(function (item) {
        if (item.role === "notice") {
          var notice = el("p", "aw-notice");
          notice.textContent = text(item.key || "handedOff");
          log.appendChild(notice);
          return;
        }
        var row = messageRow(item.role, item.text, item.direction);
        if (item === state.pendingItem) {
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
          return !item.failed && item !== state.pendingItem;
        })
        .slice(-MAX_STORED_MESSAGES)
        .map(function (item) {
          return { role: item.role, text: item.text, direction: item.direction, key: item.key };
        });
      storageSet(localStorageOrNull(), storagePrefix + "history", JSON.stringify(stored));
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

  function requestJson(url, body) {
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
              ((item.role === "visitor" || item.role === "assistant") &&
                typeof item.text === "string"))
          );
        })
        .slice(-MAX_STORED_MESSAGES)
        .map(function (item) {
          return {
            role: item.role,
            text: item.text,
            direction: item.direction === "rtl" ? "rtl" : "ltr",
            key: item.key,
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

  function messageRow(role, messageText, direction) {
    var row = el("div", "aw-message aw-" + role);
    // Each message finds its own direction (a Hebrew reply in an English
    // interface, a phone number in an Arabic one).
    row.setAttribute("dir", "auto");
    if (direction === "rtl" || direction === "ltr") {
      row.setAttribute("data-language-direction", direction);
    }
    appendLinkedText(row, messageText);
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
    return luminance > 0.45 ? "#111827" : "#ffffff";
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
