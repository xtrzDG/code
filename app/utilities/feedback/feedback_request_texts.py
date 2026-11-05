"""
The request for feedback after a visit, in the customer's language.

FEEDBACK_REQUEST_TEXT is also the body of the WhatsApp utility template
the owner registers in Meta for a closed 24-hour window: its one
parameter, {{1}}, is the business name (`template_body` shows it that
way). It names the localized STOP word, so the customer knows how to stop
such messages.
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

BUSINESS_FIELD: str = "{business}"
TEMPLATE_PARAMETER: str = "{{1}}"

FEEDBACK_REQUEST_TEXT: LocalizedText = build_localized_text(
    en=(
        "Hello from {business}! How was your visit? Please reply with a "
        "number from 1 to 5 (5 = excellent). Reply STOP to stop such messages."
    ),
    ru=(
        "Здравствуйте, это {business}! Как прошёл ваш визит? Ответьте цифрой "
        "от 1 до 5 (5 — отлично). Чтобы не получать такие сообщения, ответьте СТОП."
    ),
    ka=(
        "გამარჯობა, ეს არის {business}! როგორ ჩაიარა თქვენმა ვიზიტმა? "
        "გვიპასუხეთ ციფრით 1-დან 5-მდე (5 — შესანიშნავი). ასეთი "
        "შეტყობინებების შესაწყვეტად უპასუხეთ: სტოპ."
    ),
    uk=(
        "Вітаємо, це {business}! Як пройшов ваш візит? Дайте відповідь цифрою "
        "від 1 до 5 (5 — чудово). Щоб не отримувати такі повідомлення, "
        "надішліть СТОП."
    ),
    hy=(
        "Բարև Ձեզ, սա {business}-ն է։ Ինչպե՞ս անցավ Ձեր այցը։ Պատասխանեք "
        "1-ից 5 թվով (5՝ գերազանց)։ Նման հաղորդագրություններ չստանալու "
        "համար պատասխանեք ՍՏՈՊ։"
    ),
    az=(
        "Salam, bu {business}-dir! Ziyarətiniz necə keçdi? Zəhmət olmasa 1-dən "
        "5-ə qədər rəqəmlə cavab verin (5 — əla). Belə mesajları dayandırmaq "
        "üçün STOP yazın."
    ),
    kk=(
        "Сәлеметсіз бе, бұл {business}! Сапарыңыз қалай өтті? 1-ден 5-ке "
        "дейінгі санмен жауап беріңіз (5 — керемет). Мұндай хабарламаларды "
        "тоқтату үшін СТОП деп жазыңыз."
    ),
    tr=(
        "Merhaba, burası {business}! Ziyaretiniz nasıl geçti? Lütfen 1'den 5'e "
        "kadar bir sayıyla yanıt verin (5 = mükemmel). Bu tür mesajları "
        "durdurmak için DUR yazın."
    ),
    he=(
        "שלום מ-{business}! איך היה הביקור? נשמח לתשובה במספר מ-1 עד 5 "
        "(5 = מצוין). כדי להפסיק הודעות כאלה, השיבו עצור."
    ),
    ar=(
        "مرحبًا من {business}! كيف كانت زيارتك؟ يُرجى الرد برقم من 1 إلى 5 "
        "(5 = ممتاز). لإيقاف مثل هذه الرسائل، أرسل توقف."
    ),
    de=(
        "Hallo von {business}! Wie war Ihr Besuch? Antworten Sie bitte mit "
        "einer Zahl von 1 bis 5 (5 = ausgezeichnet). Mit STOPP bestellen Sie "
        "solche Nachrichten ab."
    ),
    fr=(
        "Bonjour de la part de {business} ! Comment s'est passée votre visite ? "
        "Répondez par un chiffre de 1 à 5 (5 = excellent). Répondez STOP pour "
        "ne plus recevoir ces messages."
    ),
    es=(
        "¡Hola de parte de {business}! ¿Qué tal tu visita? Responde con un "
        "número del 1 al 5 (5 = excelente). Responde STOP para dejar de "
        "recibir estos mensajes."
    ),
    it=(
        "Ciao da {business}! Com'è andata la tua visita? Rispondi con un "
        "numero da 1 a 5 (5 = eccellente). Rispondi STOP per non ricevere più "
        "questi messaggi."
    ),
    pt=(
        "Olá da {business}! Como foi a sua visita? Responda com um número de "
        "1 a 5 (5 = excelente). Responda PARAR para não receber mais estas "
        "mensagens."
    ),
    pl=(
        "Dzień dobry, tu {business}! Jak minęła Państwa wizyta? Prosimy o "
        "odpowiedź cyfrą od 1 do 5 (5 = świetnie). Aby nie otrzymywać takich "
        "wiadomości, odpisz STOP."
    ),
)
