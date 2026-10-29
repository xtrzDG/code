"""
What the assistant says instead of an answer: a handoff, a call-back, a limit.

Every text exists for the languages businesses launch with; resolution
falls back to the base language and then English. `{business}` is replaced
with the business name (see `business_name_placeholder`).
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

COLLEAGUE_TAKES_OVER: LocalizedText = build_localized_text(
    en="Thank you! I am passing your question to a colleague, who will get back "
    "to you soon.",
    ru="Спасибо! Я передаю ваш вопрос коллеге — с вами скоро свяжутся.",
    ka="გმადლობთ! თქვენს კითხვას კოლეგას გადავცემ — მალე დაგიკავშირდებიან.",
    tr="Teşekkürler! Sorunuzu bir çalışma arkadaşıma iletiyorum, en kısa sürede "
    "size dönüş yapılacak.",
    he="תודה! אני מעביר את השאלה שלך לעמית, שיחזור אליך בקרוב.",
    ar="شكرًا لك! سأحوّل سؤالك إلى أحد الزملاء، وسيتواصل معك قريبًا.",
    hy="Շնորհակալություն։ Ձեր հարցը փոխանցում եմ գործընկերոջս, ով շուտով "
    "կկապվի Ձեզ հետ։",
    uk="Дякую! Я передаю ваше питання колезі — з вами скоро зв'яжуться.",
    de="Vielen Dank! Ich gebe Ihre Frage an das Team weiter – wir melden uns in "
    "Kürze bei Ihnen.",
    fr="Merci ! Je transmets votre question à un collègue, qui vous répondra "
    "rapidement.",
    es="¡Gracias! Paso su consulta a un compañero, que se pondrá en contacto con "
    "usted en breve.",
    it="Grazie! Inoltro la sua domanda a un collega, che la ricontatterà a breve.",
    pt="Obrigado! Vou encaminhar sua pergunta a um colega, que entrará em contato "
    "em breve.",
    pl="Dziękuję! Przekazuję pytanie współpracownikowi — wkrótce się odezwiemy.",
    az="Təşəkkür edirik! Sualınızı həmkarıma ötürürəm, tezliklə sizinlə əlaqə "
    "saxlanılacaq.",
    kk="Рақмет! Сұрағыңызды әріптесіме жіберемін, жақын арада сізбен байланысады.",
    zh="谢谢！我会把您的问题转给同事，他们会尽快回复您。",
    ja="ありがとうございます。担当者に引き継ぎますので、まもなくご連絡いたします。",
)

COLLEAGUE_WILL_CALL_BACK: LocalizedText = build_localized_text(
    en="A colleague already has your request and will call you back soon. Thank "
    "you for calling!",
    ru="Ваш запрос уже у коллеги — вам скоро перезвонят. Спасибо за звонок!",
    ka="თქვენი მოთხოვნა უკვე კოლეგასთანაა — მალე გადმოგირეკავენ. გმადლობთ ზარისთვის!",
    tr="Talebiniz bir çalışma arkadaşıma iletildi, sizi kısa süre içinde geri "
    "arayacak. Aradığınız için teşekkürler!",
    he="הבקשה שלך כבר אצל עמית, שיחזור אליך בטלפון בקרוב. תודה שהתקשרת!",
    ar="طلبك الآن لدى أحد الزملاء، وسيعاود الاتصال بك قريبًا. شكرًا لاتصالك!",
    hy="Ձեր հարցումն արդեն գործընկերոջս մոտ է, նա շուտով հետ կզանգի Ձեզ։ "
    "Շնորհակալություն զանգի համար։",
    uk="Ваш запит уже в колеги — вам скоро передзвонять. Дякуємо за дзвінок!",
    de="Ihr Anliegen liegt bereits beim Team – wir rufen Sie in Kürze zurück. "
    "Danke für Ihren Anruf!",
    fr="Votre demande a été transmise à un collègue, qui vous rappellera "
    "rapidement. Merci de votre appel !",
    es="Su solicitud ya la tiene un compañero, que le devolverá la llamada en "
    "breve. ¡Gracias por llamar!",
    it="La sua richiesta è già passata a un collega, che la richiamerà a breve. "
    "Grazie per la chiamata!",
    pt="Sua solicitação já está com um colega, que vai retornar a ligação em "
    "breve. Obrigado por ligar!",
    pl="Twoja prośba trafiła już do współpracownika, który wkrótce oddzwoni. "
    "Dziękujemy za telefon!",
    az="Müraciətiniz artıq həmkarımdadır, tezliklə sizə geri zəng ediləcək. Zəng "
    "üçün təşəkkür edirik!",
    kk="Өтінішіңіз әріптесімде, ол жақын арада сізге қайта қоңырау шалады. "
    "Қоңырауыңызға рақмет!",
    zh="您的请求已转给同事，他们会尽快给您回电。感谢来电！",
    ja="ご用件は担当者に引き継ぎました。まもなく折り返しお電話いたします。お電話"
    "ありがとうございました。",
)

CONTACT_LIMIT_NOTICE: LocalizedText = build_localized_text(
    en="You have sent a lot of messages in a short time. Please write again a "
    "little later, and we will gladly continue.",
    ru="Вы отправили много сообщений за короткое время. Пожалуйста, напишите "
    "чуть позже — мы с радостью продолжим.",
    ka="მოკლე დროში ბევრი შეტყობინება გამოგიგზავნიათ. გთხოვთ, ცოტა "
    "მოგვიანებით მოგვწეროთ — სიამოვნებით გავაგრძელებთ.",
    tr="Kısa sürede çok sayıda mesaj gönderdiniz. Lütfen biraz sonra tekrar "
    "yazın, memnuniyetle devam ederiz.",
    he="שלחת הרבה הודעות בזמן קצר. אנא כתוב שוב מעט מאוחר יותר, ונשמח להמשיך.",
    ar="لقد أرسلت عددًا كبيرًا من الرسائل خلال وقت قصير. يُرجى الكتابة مرة "
    "أخرى بعد قليل، وسيسعدنا متابعة المحادثة.",
    hy="Կարճ ժամանակում շատ հաղորդագրություններ եք ուղարկել։ Խնդրում ենք գրել "
    "մի փոքր ուշ, և սիրով կշարունակենք։",
    uk="Ви надіслали багато повідомлень за короткий час. Будь ласка, напишіть "
    "трохи пізніше — ми охоче продовжимо.",
    de="Sie haben in kurzer Zeit sehr viele Nachrichten gesendet. Bitte "
    "schreiben Sie etwas später wieder – wir machen dann gerne weiter.",
    fr="Vous avez envoyé beaucoup de messages en peu de temps. Merci de "
    "réécrire un peu plus tard, nous continuerons avec plaisir.",
    es="Ha enviado muchos mensajes en poco tiempo. Por favor, vuelva a escribir "
    "un poco más tarde y con gusto continuaremos.",
    it="Ha inviato molti messaggi in poco tempo. La preghiamo di riscrivere un "
    "po' più tardi: continueremo volentieri.",
    pt="Você enviou muitas mensagens em pouco tempo. Por favor, escreva "
    "novamente um pouco mais tarde e continuaremos com prazer.",
    pl="Wysłano wiele wiadomości w krótkim czasie. Prosimy napisać ponownie "
    "nieco później — chętnie będziemy kontynuować.",
    az="Qısa müddətdə çoxlu mesaj göndərmisiniz. Zəhmət olmasa, bir az sonra "
    "yenidən yazın, məmnuniyyətlə davam edərik.",
    kk="Сіз қысқа уақытта көп хабарлама жібердіңіз. Біраз уақыттан кейін қайта "
    "жазыңыз, біз қуана жалғастырамыз.",
    zh="您在短时间内发送了很多消息。请稍后再写，我们很乐意继续为您服务。",
    ja="短時間に多くのメッセージが送信されました。少し時間をおいてから、もう一度"
    "ご連絡ください。",
)
