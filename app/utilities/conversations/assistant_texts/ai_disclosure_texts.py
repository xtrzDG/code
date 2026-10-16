"""
The AI disclosure: the assistant says it is an AI assistant of the business.

It exists for every language with text support: the disclosure is legally
required.

Every text exists for the languages businesses launch with; resolution
falls back to the base language and then English. `{business}` is replaced
with the business name (see `business_name_placeholder`).
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

AI_DISCLOSURE: LocalizedText = build_localized_text(
    en="Hello! I am the AI assistant of {business}.",
    ru="Здравствуйте! Я AI-ассистент «{business}».",
    ka="გამარჯობა! მე ვარ {business}-ის AI-ასისტენტი.",
    tr="Merhaba! Ben {business} işletmesinin yapay zekâ asistanıyım.",
    he="שלום! אני עוזר ה-AI של {business}.",
    ar="مرحبًا! أنا مساعد الذكاء الاصطناعي لدى {business}.",
    hy="Բարև Ձեզ։ Ես {business}-ի AI օգնականն եմ։",
    uk="Вітаю! Я AI-асистент «{business}».",
    de="Hallo! Ich bin der KI-Assistent von {business}.",
    fr="Bonjour ! Je suis l'assistant IA de {business}.",
    es="¡Hola! Soy el asistente de IA de {business}.",
    it="Buongiorno! Sono l'assistente IA di {business}.",
    pt="Olá! Sou o assistente de IA de {business}.",
    pl="Dzień dobry! Jestem asystentem AI w {business}.",
    az="Salam! Mən {business} müəssisəsinin süni intellekt köməkçisiyəm.",
    kk="Сәлеметсіз бе! Мен {business} компаниясының AI көмекшісімін.",
    zh="您好！我是{business}的AI助手。",
    ja="こんにちは！{business}のAIアシスタントです。",
    be="Вітаю! Я AI-асістэнт «{business}».",
    bg="Здравейте! Аз съм AI асистентът на {business}.",
    bn="হ্যালো! আমি {business}-এর AI সহকারী।",
    bs="Zdravo! Ja sam AI asistent {business}.",
    ca="Hola! Sóc l'assistent d'IA de {business}.",
    cs="Dobrý den! Jsem AI asistent {business}.",
    da="Hej! Jeg er AI-assistenten hos {business}.",
    el="Γεια σας! Είμαι ο ψηφιακός βοηθός τεχνητής νοημοσύνης του {business}.",
    et="Tere! Olen ettevõtte {business} tehisintellekti assistent.",
    fa="سلام! من دستیار هوش مصنوعی {business} هستم.",
    fi="Hei! Olen yrityksen {business} tekoälyavustaja.",
    fil="Kumusta! Ako ang AI assistant ng {business}.",
    hi="नमस्ते! मैं {business} का AI सहायक हूँ।",
    hr="Pozdrav! Ja sam AI asistent tvrtke {business}.",
    hu="Üdvözlöm! A(z) {business} mesterségesintelligencia-asszisztense vagyok.",
    id="Halo! Saya asisten AI {business}.",
    ko="안녕하세요! 저는 {business}의 AI 어시스턴트입니다.",
    lt="Sveiki! Esu {business} dirbtinio intelekto asistentas.",
    lv="Sveiki! Esmu {business} mākslīgā intelekta asistents.",
    mk="Здраво! Јас сум AI асистентот на {business}.",
    ms="Helo! Saya pembantu AI {business}.",
    nb="Hei! Jeg er AI-assistenten til {business}.",
    nl="Hallo! Ik ben de AI-assistent van {business}.",
    no="Hei! Jeg er AI-assistenten til {business}.",
    ro="Bună ziua! Sunt asistentul AI al {business}.",
    sk="Dobrý deň! Som AI asistent {business}.",
    sl="Pozdravljeni! Sem AI-asistent podjetja {business}.",
    sq="Përshëndetje! Jam asistenti i inteligjencës artificiale i {business}.",
    sr="Здраво! Ја сам AI асистент компаније {business}.",
    sv="Hej! Jag är AI-assistenten på {business}.",
    sw="Habari! Mimi ni msaidizi wa AI wa {business}.",
    th="สวัสดี! ฉันคือผู้ช่วย AI ของ {business}",
    ur="السلام علیکم! میں {business} کا AI معاون ہوں۔",
    uz="Assalomu alaykum! Men {business} AI yordamchisiman.",
    vi="Xin chào! Tôi là trợ lý AI của {business}.",
)
