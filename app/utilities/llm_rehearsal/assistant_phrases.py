"""
What the rehearsal assistant says (LLM_PROVIDER=scripted), in the
language the customer wrote in. No numbers, prices or times: it names
nothing a reply check could find invented.
"""

from enum import StrEnum


class RehearsalReply(StrEnum):
    """The few things the rehearsal assistant can say."""

    ANSWER = "answer"
    BOOKED = "booked"
    NO_TIME = "no_time"
    PASSED_ON = "passed_on"


ASSISTANT_PHRASES: dict[str, dict[RehearsalReply, str]] = {
    "en": {
        RehearsalReply.ANSWER: (
            "Thank you for your message! This is the test assistant of a staging "
            "server: its answers are scripted, no language model reads your message."
        ),
        RehearsalReply.BOOKED: "Done, your booking is confirmed. See you soon!",
        RehearsalReply.NO_TIME: "Sorry, there is no free time in the next days.",
        RehearsalReply.PASSED_ON: "I have passed your message to a colleague.",
    },
    "ru": {
        RehearsalReply.ANSWER: (
            "Спасибо за сообщение! Это тестовый помощник: его ответы заранее "
            "заданы, языковая модель ваше сообщение не читает."
        ),
        RehearsalReply.BOOKED: "Готово, ваша бронь подтверждена. Ждём вас!",
        RehearsalReply.NO_TIME: "К сожалению, в ближайшие дни свободного времени нет.",
        RehearsalReply.PASSED_ON: "Я передал ваше сообщение коллеге.",
    },
    "uk": {
        RehearsalReply.ANSWER: (
            "Дякуємо за повідомлення! Це тестовий помічник: його відповіді "
            "задані заздалегідь, мовна модель ваше повідомлення не читає."
        ),
        RehearsalReply.BOOKED: "Готово, ваше бронювання підтверджено. Чекаємо на вас!",
        RehearsalReply.NO_TIME: "На жаль, найближчими днями вільного часу немає.",
        RehearsalReply.PASSED_ON: "Я передав ваше повідомлення колезі.",
    },
    "ka": {
        RehearsalReply.ANSWER: (
            "გმადლობთ შეტყობინებისთვის! ეს სატესტო ასისტენტია: მისი პასუხები "
            "წინასწარ არის გაწერილი და ენობრივი "
            "მოდელი თქვენს შეტყობინებას არ კითხულობს."
        ),
        RehearsalReply.BOOKED: "მზადაა, თქვენი ჯავშანი დადასტურებულია. გელოდებით!",
        RehearsalReply.NO_TIME: "სამწუხაროდ, უახლოეს დღეებში თავისუფალი დრო არ არის.",
        RehearsalReply.PASSED_ON: "თქვენი შეტყობინება კოლეგას გადავეცი.",
    },
    "de": {
        RehearsalReply.ANSWER: (
            "Danke für Ihre Nachricht! Dies ist der Testassistent eines "
            "Testservers: Seine Antworten sind vorgegeben, kein Sprachmodell "
            "liest Ihre Nachricht."
        ),
        RehearsalReply.BOOKED: "Erledigt, Ihre Buchung ist bestätigt. Bis bald!",
        RehearsalReply.NO_TIME: "Leider ist in den nächsten Tagen nichts mehr frei.",
        RehearsalReply.PASSED_ON: (
            "Ich habe Ihre Nachricht an einen Kollegen weitergegeben."
        ),
    },
    "fr": {
        RehearsalReply.ANSWER: (
            "Merci pour votre message ! Ceci est l'assistant de test d'un "
            "serveur d'essai : ses réponses sont préparées, aucun modèle de "
            "langage ne lit votre message."
        ),
        RehearsalReply.BOOKED: (
            "C'est fait, votre réservation est confirmée. À bientôt !"
        ),
        RehearsalReply.NO_TIME: (
            "Désolé, il n'y a plus de créneau libre ces prochains jours."
        ),
        RehearsalReply.PASSED_ON: "J'ai transmis votre message à un collègue.",
    },
    "es": {
        RehearsalReply.ANSWER: (
            "¡Gracias por su mensaje! Este es el asistente de prueba de un "
            "servidor de pruebas: sus respuestas están preparadas y ningún "
            "modelo de lenguaje lee su mensaje."
        ),
        RehearsalReply.BOOKED: "Listo, su reserva está confirmada. ¡Hasta pronto!",
        RehearsalReply.NO_TIME: (
            "Lo siento, no hay horarios libres en los próximos días."
        ),
        RehearsalReply.PASSED_ON: "He pasado su mensaje a un compañero.",
    },
    "it": {
        RehearsalReply.ANSWER: (
            "Grazie per il messaggio! Questo è l'assistente di prova di un "
            "server di test: le sue risposte sono preimpostate e nessun "
            "modello linguistico legge il suo messaggio."
        ),
        RehearsalReply.BOOKED: "Fatto, la sua prenotazione è confermata. A presto!",
        RehearsalReply.NO_TIME: (
            "Mi dispiace, nei prossimi giorni non c'è posto libero."
        ),
        RehearsalReply.PASSED_ON: "Ho passato il suo messaggio a un collega.",
    },
    "pt": {
        RehearsalReply.ANSWER: (
            "Obrigado pela mensagem! Este é o assistente de teste de um "
            "servidor de testes: as respostas são predefinidas e nenhum "
            "modelo de linguagem lê a sua mensagem."
        ),
        RehearsalReply.BOOKED: "Pronto, a sua reserva está confirmada. Até breve!",
        RehearsalReply.NO_TIME: "Desculpe, não há horários livres nos próximos dias.",
        RehearsalReply.PASSED_ON: "Passei a sua mensagem a um colega.",
    },
    "tr": {
        RehearsalReply.ANSWER: (
            "Mesajınız için teşekkürler! Bu bir test sunucusunun test "
            "asistanıdır: yanıtları önceden hazırlanmıştır, mesajınızı bir "
            "dil modeli okumaz."
        ),
        RehearsalReply.BOOKED: "Tamam, rezervasyonunuz onaylandı. Görüşmek üzere!",
        RehearsalReply.NO_TIME: "Üzgünüz, önümüzdeki günlerde boş saat yok.",
        RehearsalReply.PASSED_ON: "Mesajınızı bir meslektaşıma ilettim.",
    },
    "pl": {
        RehearsalReply.ANSWER: (
            "Dziękujemy za wiadomość! To asystent testowy serwera testowego: "
            "jego odpowiedzi są przygotowane, żaden model językowy nie czyta "
            "Twojej wiadomości."
        ),
        RehearsalReply.BOOKED: (
            "Gotowe, Twoja rezerwacja jest potwierdzona. Do zobaczenia!"
        ),
        RehearsalReply.NO_TIME: (
            "Niestety, w najbliższych dniach nie ma wolnych terminów."
        ),
        RehearsalReply.PASSED_ON: "Przekazałem Twoją wiadomość koledze.",
    },
    "az": {
        RehearsalReply.ANSWER: (
            "Mesajınız üçün təşəkkür edirik! Bu, test serverinin test "
            "köməkçisidir: cavabları əvvəlcədən hazırlanıb, mesajınızı dil "
            "modeli oxumur."
        ),
        RehearsalReply.BOOKED: "Hazırdır, rezervasiyanız təsdiqləndi. Gözləyirik!",
        RehearsalReply.NO_TIME: "Təəssüf ki, yaxın günlərdə boş vaxt yoxdur.",
        RehearsalReply.PASSED_ON: "Mesajınızı həmkarıma ötürdüm.",
    },
    "hy": {
        RehearsalReply.ANSWER: (
            "Շնորհակալություն հաղորդագրության համար։ Սա փորձնական օգնական է․ "
            "նրա պատասխանները նախապես գրված են, և լեզվական մոդելը ձեր "
            "հաղորդագրությունը չի կարդում։"
        ),
        RehearsalReply.BOOKED: (
            "Պատրաստ է, ձեր ամրագրումը հաստատված է։ Սպասում ենք ձեզ։"
        ),
        RehearsalReply.NO_TIME: "Ցավոք, մոտակա օրերին ազատ ժամանակ չկա։",
        RehearsalReply.PASSED_ON: "Ձեր հաղորդագրությունը փոխանցեցի գործընկերոջս։",
    },
    "el": {
        RehearsalReply.ANSWER: (
            "Ευχαριστούμε για το μήνυμα! Αυτός είναι ο δοκιμαστικός βοηθός "
            "ενός δοκιμαστικού διακομιστή: οι απαντήσεις του είναι έτοιμες "
            "και κανένα γλωσσικό μοντέλο δεν διαβάζει το μήνυμά σας."
        ),
        RehearsalReply.BOOKED: "Έγινε, η κράτησή σας επιβεβαιώθηκε. Τα λέμε σύντομα!",
        RehearsalReply.NO_TIME: (
            "Λυπούμαστε, τις επόμενες μέρες δεν υπάρχει ελεύθερη ώρα."
        ),
        RehearsalReply.PASSED_ON: "Προώθησα το μήνυμά σας σε συνάδελφο.",
    },
    "he": {
        RehearsalReply.ANSWER: (
            "תודה על ההודעה! זהו עוזר הבדיקה של שרת ניסיון: התשובות שלו "
            "מוכנות מראש, ואף מודל שפה לא קורא את ההודעה שלכם."
        ),
        RehearsalReply.BOOKED: "בוצע, ההזמנה שלכם אושרה. נתראה בקרוב!",
        RehearsalReply.NO_TIME: "מצטערים, אין זמן פנוי בימים הקרובים.",
        RehearsalReply.PASSED_ON: "העברתי את ההודעה שלכם לעמית.",
    },
    "ar": {
        RehearsalReply.ANSWER: (
            "شكرا على رسالتك! هذا هو المساعد التجريبي لخادم تجريبي: إجاباته "
            "معدّة مسبقا ولا يقرأ أي نموذج لغوي رسالتك."
        ),
        RehearsalReply.BOOKED: "تم، حجزك مؤكد. نراك قريبا!",
        RehearsalReply.NO_TIME: "عذرا، لا يوجد وقت متاح في الأيام القادمة.",
        RehearsalReply.PASSED_ON: "لقد نقلت رسالتك إلى زميل.",
    },
}

# A name the rehearsal books under, in the customer's language.
CUSTOMER_NAMES: dict[str, str] = {
    "en": "Anna",
    "ru": "Анна",
    "uk": "Ганна",
    "ka": "ნინო",
    "de": "Anna",
    "fr": "Anne",
    "es": "Ana",
    "it": "Anna",
    "pt": "Ana",
    "tr": "Ayşe",
    "pl": "Anna",
    "az": "Aysel",
    "hy": "Աննա",
    "el": "Άννα",
    "he": "חנה",
    "ar": "سارة",
}
FALLBACK_LANGUAGE: str = "en"
