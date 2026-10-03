"""
What a caller who did not get through receives (the text-back).

TEXT_BACK_MESSAGE_TEXT is the body of the WhatsApp utility template the
owner registers in Meta for the business's WhatsApp number (its one
parameter, {{1}}, is the business name; `template_body` shows it that
way); the conversation the caller's reply continues in keeps the same text.
TEXT_BACK_SMS_TEXT goes by SMS from the platform's sender, where a reply
cannot reach the business, so it promises a call back instead.
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

BUSINESS_FIELD: str = "{business}"
TEMPLATE_PARAMETER: str = "{{1}}"

TEXT_BACK_MESSAGE_TEXT: LocalizedText = build_localized_text(
    en=(
        "Hello, this is {business}. You called us and we could not answer. "
        "How can we help? Reply to this message and we will continue here."
    ),
    ru=(
        "Здравствуйте, это {business}. Вы нам звонили, но мы не смогли "
        "ответить. Чем можем помочь? Ответьте на это сообщение — продолжим здесь."
    ),
    ka=(
        "გამარჯობა, ეს არის {business}. დაგვირეკეთ, მაგრამ ვერ გიპასუხეთ. "
        "რით შეგვიძლია დაგეხმაროთ? უპასუხეთ ამ შეტყობინებას და აქვე გავაგრძელებთ."
    ),
    uk=(
        "Вітаємо, це {business}. Ви нам телефонували, але ми не змогли "
        "відповісти. Чим можемо допомогти? Дайте відповідь на це повідомлення — "
        "продовжимо тут."
    ),
    hy=(
        "Բարև Ձեզ, սա {business}-ն է։ Դուք զանգահարել եք մեզ, բայց չկարողացանք "
        "պատասխանել։ Ինչո՞վ կարող ենք օգնել։ Պատասխանեք այս հաղորդագրությանը, "
        "և կշարունակենք այստեղ։"
    ),
    he=(
        "שלום, כאן {business}. התקשרת אלינו ולא הצלחנו לענות. איך נוכל לעזור? "
        "אפשר להשיב להודעה הזו ונמשיך כאן."
    ),
    ar=(
        "مرحبًا، معك {business}. اتصلت بنا ولم نتمكن من الرد. كيف يمكننا "
        "مساعدتك؟ رُدّ على هذه الرسالة وسنكمل هنا."
    ),
    tr=(
        "Merhaba, burası {business}. Bizi aradınız ama yanıt veremedik. Size "
        "nasıl yardımcı olabiliriz? Bu mesaja yanıt verin, buradan devam edelim."
    ),
    pl=(
        "Dzień dobry, tu {business}. Dzwonili Państwo do nas, ale nie mogliśmy "
        "odebrać. W czym możemy pomóc? Wystarczy odpowiedzieć na tę wiadomość, "
        "a będziemy kontynuować tutaj."
    ),
    de=(
        "Hallo, hier ist {business}. Sie haben uns angerufen, aber wir konnten "
        "nicht rangehen. Wie können wir helfen? Antworten Sie einfach auf diese "
        "Nachricht, dann machen wir hier weiter."
    ),
    es=(
        "Hola, somos {business}. Nos llamaste y no pudimos atenderte. ¿En qué "
        "podemos ayudarte? Responde a este mensaje y seguimos por aquí."
    ),
    fr=(
        "Bonjour, ici {business}. Vous nous avez appelés et nous n'avons pas pu "
        "répondre. Comment pouvons-nous vous aider ? Répondez à ce message et "
        "nous continuerons ici."
    ),
    it=(
        "Ciao, siamo {business}. Ci hai chiamato e non siamo riusciti a "
        "rispondere. Come possiamo aiutarti? Rispondi a questo messaggio e "
        "continuiamo qui."
    ),
    pt=(
        "Olá, aqui é {business}. Você nos ligou e não conseguimos atender. Como "
        "podemos ajudar? Responda a esta mensagem e continuamos por aqui."
    ),
    kk=(
        "Сәлеметсіз бе, бұл {business}. Сіз бізге қоңырау шалдыңыз, бірақ біз "
        "жауап бере алмадық. Қалай көмектесе аламыз? Осы хабарламаға жауап "
        "беріңіз, осында жалғастырамыз."
    ),
)

TEXT_BACK_SMS_TEXT: LocalizedText = build_localized_text(
    en="{business}: sorry, we missed your call. We will get back to you soon.",
    ru="{business}: извините, мы пропустили ваш звонок. Скоро с вами свяжемся.",
    ka="{business}: ბოდიშს გიხდით, ზარს ვერ ვუპასუხეთ. მალე დაგიკავშირდებით.",
    uk="{business}: вибачте, ми пропустили ваш дзвінок. Незабаром зв'яжемося з вами.",
    hy="{business}․ ներողություն, բաց ենք թողել Ձեր զանգը։ Շուտով կկապվենք Ձեզ հետ։",
    he="{business}: מצטערים, פספסנו את השיחה שלך. נחזור אליך בקרוב.",
    ar="{business}: نعتذر، فاتنا اتصالك. سنتواصل معك قريبًا.",
    tr="{business}: Üzgünüz, aramanızı kaçırdık. En kısa sürede size dönüş yapacağız.",
    pl="{business}: przepraszamy, nie odebraliśmy połączenia. Wkrótce się odezwiemy.",
    de=(
        "{business}: Entschuldigung, wir haben Ihren Anruf verpasst. "
        "Wir melden uns bald."
    ),
    es="{business}: perdona, no pudimos atender tu llamada. Te contactaremos pronto.",
    fr="{business} : désolés, nous avons manqué votre appel. Nous vous rappelons vite.",
    it="{business}: scusa, abbiamo perso la tua chiamata. Ti ricontatteremo presto.",
    pt="{business}: desculpe, perdemos sua ligação. Entraremos em contato em breve.",
    kk="{business}: кешіріңіз, қоңырауыңызға жауап бере алмадық. Жақында хабарласамыз.",
)


def template_body(message: str) -> str:
    """The text-back with the template's parameter in place of the business."""

    return message.replace(BUSINESS_FIELD, TEMPLATE_PARAMETER)
