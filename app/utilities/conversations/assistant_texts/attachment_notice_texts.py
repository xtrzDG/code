"""
What the assistant says to a message it cannot read: a sticker, a file, a
contact card, a voice note without words or one too long to transcribe.
The customer is never left without an answer.

Every language of the text-supported list (`language_support_data`) and a
few more; resolution falls back to the base language and then English.
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

CANNOT_READ_ATTACHMENT: LocalizedText = build_localized_text(
    en="Sorry, I couldn't open this attachment. Could you please write your "
    "question in a message? I'll be glad to help.",
    ru="Извините, не получилось открыть это вложение. Напишите, пожалуйста, "
    "ваш вопрос текстом — я с радостью помогу.",
    ka="ბოდიში, ამ ფაილის გახსნა ვერ მოხერხდა. გთხოვთ, თქვენი კითხვა "
    "შეტყობინებით მოგვწეროთ — სიამოვნებით დაგეხმარებით.",
    uk="Вибачте, не вдалося відкрити це вкладення. Напишіть, будь ласка, ваше "
    "питання текстом — я із задоволенням допоможу.",
    be="Прабачце, не атрымалася адкрыць гэта ўкладанне. Напішыце, калі ласка, "
    "ваша пытанне тэкстам — я з радасцю дапамагу.",
    bg="Извинете, не успях да отворя този прикачен файл. Моля, напишете "
    "въпроса си в съобщение – с удоволствие ще помогна.",
    he="מצטערים, לא הצלחתי לפתוח את הקובץ המצורף. אפשר לכתוב את השאלה "
    "בהודעה? אשמח לעזור.",
    ar="عذرًا، لم أتمكن من فتح هذا المرفق. هل يمكنك كتابة سؤالك في رسالة؟ "
    "يسعدني مساعدتك.",
    fa="متأسفم، نتوانستم این پیوست را باز کنم. لطفاً سؤالتان را در یک پیام "
    "بنویسید؛ با کمال میل کمک می‌کنم.",
    ur="معذرت، یہ اٹیچمنٹ نہیں کھل سکی۔ براہِ کرم اپنا سوال پیغام میں لکھ دیں، "
    "ہم خوشی سے مدد کریں گے۔",
    hy="Ներողություն, չհաջողվեց բացել այս կցորդը։ Խնդրում եմ, գրեք Ձեր "
    "հարցը հաղորդագրությամբ, և ես սիրով կօգնեմ։",
    az="Bağışlayın, bu əlavəni aça bilmədim. Zəhmət olmasa, sualınızı mesajla "
    "yazın — məmnuniyyətlə kömək edərəm.",
    kk="Кешіріңіз, бұл тіркемені аша алмадым. Сұрағыңызды хабарлама арқылы "
    "жазып жіберіңізші — қуана көмектесемін.",
    ky="Кечиресиз, бул тиркемени ача алган жокмун. Сурооңузду билдирүү "
    "аркылуу жазып жибериңизчи — кубануу менен жардам берем.",
    tg="Бубахшед, ин замимаро кушода натавонистам. Лутфан, саволатонро бо "
    "паём нависед — бо хурсандӣ кӯмак мекунам.",
    uz="Kechirasiz, bu ilovani ochib bo‘lmadi. Iltimos, savolingizni xabar "
    "orqali yozing — bajonidil yordam beraman.",
    tr="Üzgünüm, bu eki açamadım. Sorunuzu mesaj olarak yazabilir misiniz? "
    "Memnuniyetle yardımcı olurum.",
    de="Entschuldigung, diesen Anhang kann ich leider nicht öffnen. Könnten "
    "Sie Ihre Frage bitte als Nachricht schreiben? Ich helfe gern.",
    fr="Désolé, je n’arrive pas à ouvrir cette pièce jointe. Pourriez-vous "
    "écrire votre question dans un message ? Je vous aiderai avec plaisir.",
    es="Lo siento, no he podido abrir este archivo adjunto. ¿Podría escribir "
    "su pregunta en un mensaje? Le ayudaré con gusto.",
    ca="Ho sento, no he pogut obrir aquest fitxer adjunt. Podríeu escriure la "
    "vostra pregunta en un missatge? Us ajudaré amb molt de gust.",
    it="Mi dispiace, non riesco ad aprire questo allegato. Potrebbe scrivere "
    "la sua domanda in un messaggio? Sarò felice di aiutarla.",
    pt="Desculpe, não consegui abrir este anexo. Pode escrever sua pergunta "
    "em uma mensagem? Terei prazer em ajudar.",
    ro="Ne pare rău, nu am reușit să deschid acest atașament. Vă rog să "
    "scrieți întrebarea într-un mesaj — vă ajut cu plăcere.",
    nl="Sorry, ik kon deze bijlage niet openen. Wilt u uw vraag in een "
    "bericht typen? Ik help u graag.",
    da="Beklager, jeg kunne ikke åbne denne vedhæftede fil. Vil du skrive dit "
    "spørgsmål i en besked? Jeg hjælper gerne.",
    nb="Beklager, jeg klarte ikke å åpne dette vedlegget. Kan du skrive "
    "spørsmålet ditt i en melding? Jeg hjelper gjerne.",
    no="Beklager, jeg klarte ikke å åpne dette vedlegget. Kan du skrive "
    "spørsmålet ditt i en melding? Jeg hjelper gjerne.",
    sv="Tyvärr kunde jag inte öppna den här bilagan. Kan du skriva din fråga "
    "i ett meddelande? Jag hjälper gärna till.",
    fi="Valitettavasti en pystynyt avaamaan tätä liitettä. Voisitko "
    "kirjoittaa kysymyksesi viestinä? Autan mielelläni.",
    et="Vabandust, ma ei saanud seda manust avada. Palun kirjutage oma "
    "küsimus sõnumina – aitan hea meelega.",
    lv="Atvainojiet, šo pielikumu neizdevās atvērt. Lūdzu, uzrakstiet savu "
    "jautājumu ziņā — labprāt palīdzēsim.",
    lt="Atsiprašome, šio priedo atidaryti nepavyko. Prašome parašyti savo "
    "klausimą žinute – mielai padėsime.",
    pl="Przepraszam, nie udało się otworzyć tego załącznika. Proszę napisać "
    "pytanie w wiadomości – chętnie pomogę.",
    cs="Omlouváme se, tuto přílohu se nepodařilo otevřít. Napište prosím svůj "
    "dotaz do zprávy – rádi pomůžeme.",
    sk="Prepáčte, túto prílohu sa nepodarilo otvoriť. Napíšte, prosím, svoju "
    "otázku do správy – radi pomôžeme.",
    sl="Oprostite, te priponke ni mogoče odpreti. Prosimo, napišite svoje "
    "vprašanje v sporočilu – z veseljem bomo pomagali.",
    hr="Ispričavamo se, ovaj privitak nije moguće otvoriti. Molimo napišite "
    "svoje pitanje u poruci – rado ćemo pomoći.",
    bs="Izvinite, ovaj prilog nije moguće otvoriti. Molimo napišite svoje "
    "pitanje u poruci — rado ćemo pomoći.",
    sr="Извините, овај прилог није могуће отворити. Молимо вас да питање "
    "напишете у поруци — радо ћемо помоћи.",
    mk="Извинете, овој прилог не може да се отвори. Ве молиме, напишете го "
    "прашањето во порака — со задоволство ќе помогнеме.",
    sq="Na vjen keq, nuk arrita ta hap këtë bashkëngjitje. Ju lutem, "
    "shkruajeni pyetjen tuaj në një mesazh — do t’ju ndihmoj me kënaqësi.",
    el="Λυπάμαι, δεν μπόρεσα να ανοίξω αυτό το συνημμένο. Μπορείτε να "
    "γράψετε την ερώτησή σας σε μήνυμα; Θα χαρώ να βοηθήσω.",
    hu="Elnézést, ezt a mellékletet nem sikerült megnyitni. Kérem, írja meg "
    "a kérdését üzenetben – szívesen segítek.",
    hi="क्षमा करें, यह अटैचमेंट नहीं खुल सका। कृपया अपना सवाल संदेश में लिखें — हमें मदद करके खुशी होगी।",
    bn="দুঃখিত, এই সংযুক্তিটি খোলা যায়নি। অনুগ্রহ করে আপনার প্রশ্নটি "
    "বার্তায় লিখুন — আমরা সানন্দে সাহায্য করব।",
    id="Maaf, saya tidak dapat membuka lampiran ini. Bisakah Anda menuliskan "
    "pertanyaan Anda dalam pesan? Saya dengan senang hati akan membantu.",
    ms="Maaf, saya tidak dapat membuka lampiran ini. Bolehkah anda tulis "
    "soalan anda dalam mesej? Saya sedia membantu.",
    fil="Paumanhin, hindi ko mabuksan ang attachment na ito. Maaari mo bang "
    "isulat ang iyong tanong sa isang mensahe? Ikalulugod kong tumulong.",
    th="ขออภัย ไม่สามารถเปิดไฟล์แนบนี้ได้ กรุณาพิมพ์คำถามของคุณเป็นข้อความ แล้วเรายินดีช่วยเหลือ",
    vi="Xin lỗi, tôi không mở được tệp đính kèm này. Bạn vui lòng nhắn câu "
    "hỏi bằng tin nhắn văn bản nhé, tôi rất sẵn lòng giúp đỡ.",
    sw="Samahani, sikuweza kufungua kiambatisho hiki. Tafadhali andika swali "
    "lako kwenye ujumbe — nitafurahi kukusaidia.",
    zh="抱歉，我无法打开这个附件。请用文字消息发送您的问题，我很乐意为您提供帮助。",
    ja="申し訳ありません、この添付ファイルを開けませんでした。ご質問をメッセージで"
    "送っていただけますか？喜んでお手伝いします。",
    ko="죄송합니다. 이 첨부 파일을 열 수 없었습니다. 질문을 메시지로 보내 "
    "주시겠어요? 기꺼이 도와드리겠습니다.",
)
