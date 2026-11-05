"""
The rebooking campaign's messages, in the customer's language, each naming
the localized STOP word so the customer knows how to stop them.

REBOOK_TEXT is also the body of the WhatsApp template for a closed
24-hour window (WHATSAPP_REBOOKING_TEMPLATE, one parameter: {{1}} the
business); a recall goes out with the same template. A pre-arrival note
names the date, so it goes only where the customer can be written freely.
"""

from app.schemas.constants.campaigns import RebookingRuleKind
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

REBOOK_TEXT: LocalizedText = build_localized_text(
    en="{business}: it has been a while since your last visit. Would you like to "
    "book again? Reply here and we will find a time for you. Reply STOP to stop "
    "such messages.",
    ru="{business}: давно вас не видели! Хотите записаться снова? Ответьте здесь — "
    "подберём удобное время. Чтобы не получать такие сообщения, ответьте СТОП.",
    ka="{business}: დიდი ხანია არ გვინახავხართ! გსურთ ხელახლა ჩაწერა? გვიპასუხეთ "
    "აქ და მოსახერხებელ დროს შეგირჩევთ. ასეთი შეტყობინებების შესაწყვეტად "
    "უპასუხეთ: სტოპ.",
    uk="{business}: давно вас не бачили! Бажаєте записатися знову? Дайте відповідь "
    "тут — підберемо зручний час. Щоб не отримувати такі повідомлення, надішліть "
    "СТОП.",
    hy="{business}: վաղուց Ձեզ չենք տեսել։ Կցանկանա՞ք կրկին գրանցվել։ Պատասխանեք "
    "այստեղ, և մենք կգտնենք Ձեզ հարմար ժամ։ Նման հաղորդագրություններ չստանալու "
    "համար պատասխանեք ՍՏՈՊ։",
    az="{business}: sizi çoxdan görmürük! Yenidən yazılmaq istəyirsiniz? Buradan "
    "cavab verin, sizə uyğun vaxt tapaq. Belə mesajları dayandırmaq üçün STOP "
    "yazın.",
    kk="{business}: сізді көптен бері көрмедік! Қайта жазылғыңыз келе ме? Осында "
    "жауап беріңіз — ыңғайлы уақыт табамыз. Мұндай хабарламаларды тоқтату үшін "
    "СТОП деп жазыңыз.",
    tr="{business}: sizi uzun zamandır görmedik! Yeniden randevu almak ister "
    "misiniz? Buradan yanıt verin, size uygun bir zaman bulalım. Bu tür mesajları "
    "durdurmak için DUR yazın.",
    he="{business}: מזמן לא התראינו! רוצים לקבוע שוב? השיבו כאן ונמצא לכם זמן נוח. "
    "כדי להפסיק הודעות כאלה, השיבו עצור.",
    ar="{business}: لم نرك منذ فترة! هل ترغب في الحجز مجددًا؟ رُدّ هنا وسنجد لك "
    "موعدًا مناسبًا. لإيقاف مثل هذه الرسائل، أرسل توقف.",
    de="{business}: Ihr letzter Besuch ist schon eine Weile her. Möchten Sie wieder "
    "einen Termin buchen? Antworten Sie hier, und wir finden eine passende Zeit. "
    "Mit STOPP bestellen Sie solche Nachrichten ab.",
    fr="{business} : cela fait un moment depuis votre dernière visite. Souhaitez-vous "
    "réserver à nouveau ? Répondez ici et nous trouverons un créneau qui vous "
    "convient. Répondez STOP pour ne plus recevoir ces messages.",
    es="{business}: hace tiempo que no te vemos. ¿Quieres reservar de nuevo? "
    "Responde aquí y buscamos un horario que te venga bien. Responde STOP para "
    "dejar de recibir estos mensajes.",
    it="{business}: è passato un po' di tempo dalla tua ultima visita. Vuoi "
    "prenotare di nuovo? Rispondi qui e troveremo un orario comodo per te. "
    "Rispondi STOP per non ricevere più questi messaggi.",
    pt="{business}: já faz algum tempo desde a sua última visita. Quer marcar de "
    "novo? Responda aqui e encontramos um horário que lhe convenha. Responda "
    "PARAR para não receber mais estas mensagens.",
    pl="{business}: dawno Państwa u nas nie było. Czy chcą Państwo umówić się "
    "ponownie? Prosimy odpisać tutaj, a znajdziemy dogodny termin. Aby nie "
    "otrzymywać takich wiadomości, odpisz STOP.",
)

RECALL_TEXT: LocalizedText = build_localized_text(
    en="{business}: it is time for your regular check-up. Reply here and we will "
    "find a time that suits you. Reply STOP to stop such messages.",
    ru="{business}: подошло время планового визита. Ответьте здесь — подберём "
    "удобное для вас время. Чтобы не получать такие сообщения, ответьте СТОП.",
    ka="{business}: დადგა თქვენი გეგმიური ვიზიტის დრო. გვიპასუხეთ აქ და "
    "მოსახერხებელ დროს შეგირჩევთ. ასეთი შეტყობინებების შესაწყვეტად უპასუხეთ: სტოპ.",
    uk="{business}: настав час планового візиту. Дайте відповідь тут — підберемо "
    "зручний для вас час. Щоб не отримувати такі повідомлення, надішліть СТОП.",
    hy="{business}: եկել է Ձեր պլանային այցի ժամանակը։ Պատասխանեք այստեղ, և մենք "
    "կգտնենք Ձեզ հարմար ժամ։ Նման հաղորդագրություններ չստանալու համար "
    "պատասխանեք ՍՏՈՊ։",
    az="{business}: növbəti planlı ziyarətinizin vaxtı çatıb. Buradan cavab verin, "
    "sizə uyğun vaxt tapaq. Belə mesajları dayandırmaq üçün STOP yazın.",
    kk="{business}: жоспарлы сапарыңыздың уақыты келді. Осында жауап беріңіз — "
    "сізге ыңғайлы уақыт табамыз. Мұндай хабарламаларды тоқтату үшін СТОП деп "
    "жазыңыз.",
    tr="{business}: düzenli kontrolünüzün zamanı geldi. Buradan yanıt verin, size "
    "uygun bir zaman bulalım. Bu tür mesajları durdurmak için DUR yazın.",
    he="{business}: הגיע הזמן לביקור התקופתי שלכם. השיבו כאן ונמצא לכם זמן נוח. "
    "כדי להפסיק הודעות כאלה, השיבו עצור.",
    ar="{business}: حان موعد زيارتك الدورية. رُدّ هنا وسنجد لك موعدًا مناسبًا. "
    "لإيقاف مثل هذه الرسائل، أرسل توقف.",
    de="{business}: Es ist Zeit für Ihren regelmäßigen Termin. Antworten Sie hier, "
    "und wir finden eine passende Zeit. Mit STOPP bestellen Sie solche Nachrichten "
    "ab.",
    fr="{business} : c'est le moment de votre visite de contrôle. Répondez ici et "
    "nous trouverons un créneau qui vous convient. Répondez STOP pour ne plus "
    "recevoir ces messages.",
    es="{business}: es hora de tu revisión periódica. Responde aquí y buscamos un "
    "horario que te venga bien. Responde STOP para dejar de recibir estos mensajes.",
    it="{business}: è il momento del tuo controllo periodico. Rispondi qui e "
    "troveremo un orario comodo per te. Rispondi STOP per non ricevere più questi "
    "messaggi.",
    pt="{business}: está na hora da sua consulta de rotina. Responda aqui e "
    "encontramos um horário que lhe convenha. Responda PARAR para não receber mais "
    "estas mensagens.",
    pl="{business}: nadszedł czas na regularną wizytę kontrolną. Prosimy odpisać "
    "tutaj, a znajdziemy dogodny termin. Aby nie otrzymywać takich wiadomości, "
    "odpisz STOP.",
)

PRE_ARRIVAL_TEXT: LocalizedText = build_localized_text(
    en="{business}: we look forward to welcoming you on {date}. If your plans "
    "change or you have a question, just reply here. Reply STOP to stop such "
    "messages.",
    ru="{business}: ждём вас {date}. Если планы изменятся или появятся вопросы, "
    "просто ответьте здесь. Чтобы не получать такие сообщения, ответьте СТОП.",
    ka="{business}: გელოდებით {date}. თუ გეგმები შეგეცვლებათ ან კითხვა "
    "გაგიჩნდებათ, უბრალოდ გვიპასუხეთ აქ. ასეთი შეტყობინებების შესაწყვეტად "
    "უპასუხეთ: სტოპ.",
    uk="{business}: чекаємо на вас {date}. Якщо плани зміняться або з'являться "
    "запитання, просто дайте відповідь тут. Щоб не отримувати такі повідомлення, "
    "надішліть СТОП.",
    hy="{business}: սպասում ենք Ձեզ {date}։ Եթե Ձեր ծրագրերը փոխվեն կամ հարց "
    "ունենաք, պարզապես պատասխանեք այստեղ։ Նման հաղորդագրություններ չստանալու "
    "համար պատասխանեք ՍՏՈՊ։",
    az="{business}: sizi {date} tarixində gözləyirik. Planlarınız dəyişsə və ya "
    "sualınız olsa, sadəcə buradan cavab verin. Belə mesajları dayandırmaq üçün "
    "STOP yazın.",
    kk="{business}: сізді {date} күтеміз. Жоспарыңыз өзгерсе немесе сұрағыңыз "
    "болса, осында жауап беріңіз. Мұндай хабарламаларды тоқтату үшін СТОП деп "
    "жазыңыз.",
    tr="{business}: sizi {date} tarihinde ağırlamayı dört gözle bekliyoruz. "
    "Planlarınız değişirse ya da bir sorunuz olursa buradan yanıt verin. Bu tür "
    "mesajları durdurmak için DUR yazın.",
    he="{business}: מחכים לכם ב-{date}. אם התוכניות משתנות או שיש לכם שאלה, פשוט "
    "השיבו כאן. כדי להפסיק הודעות כאלה, השיבו עצור.",
    ar="{business}: نتطلع إلى استقبالك في {date}. إذا تغيّرت خططك أو كان لديك "
    "سؤال، فقط رُدّ هنا. لإيقاف مثل هذه الرسائل، أرسل توقف.",
    de="{business}: Wir freuen uns, Sie am {date} zu begrüßen. Wenn sich Ihre Pläne "
    "ändern oder Sie eine Frage haben, antworten Sie einfach hier. Mit STOPP "
    "bestellen Sie solche Nachrichten ab.",
    fr="{business} : nous avons hâte de vous accueillir le {date}. Si vos plans "
    "changent ou si vous avez une question, répondez simplement ici. Répondez STOP "
    "pour ne plus recevoir ces messages.",
    es="{business}: te esperamos el {date}. Si cambian tus planes o tienes alguna "
    "pregunta, responde aquí. Responde STOP para dejar de recibir estos mensajes.",
    it="{business}: ti aspettiamo il {date}. Se i tuoi piani cambiano o hai una "
    "domanda, rispondi pure qui. Rispondi STOP per non ricevere più questi "
    "messaggi.",
    pt="{business}: esperamos por si no dia {date}. Se os seus planos mudarem ou "
    "tiver alguma dúvida, basta responder aqui. Responda PARAR para não receber "
    "mais estas mensagens.",
    pl="{business}: czekamy na Państwa {date}. Jeśli plany się zmienią lub pojawią "
    "się pytania, wystarczy odpisać tutaj. Aby nie otrzymywać takich wiadomości, "
    "odpisz STOP.",
)

CAMPAIGN_TEXTS: dict[RebookingRuleKind, LocalizedText] = {
    RebookingRuleKind.REBOOK: REBOOK_TEXT,
    RebookingRuleKind.RECALL: RECALL_TEXT,
    RebookingRuleKind.PRE_ARRIVAL: PRE_ARRIVAL_TEXT,
}
# Rules whose message the WhatsApp template can carry (it names no date).
TEMPLATED_RULES: frozenset[RebookingRuleKind] = frozenset(
    {RebookingRuleKind.REBOOK, RebookingRuleKind.RECALL}
)
