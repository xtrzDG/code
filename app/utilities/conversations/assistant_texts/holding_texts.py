"""
What the assistant says when a reply takes long: one short "one moment"
sent once, CHAT_TURN_DEADLINE_SECONDS after the customer's first unanswered
message, so nobody waits in silence; the answer (or a colleague) follows.

The text exists for every language the AI disclosure has (and a few
more); resolution falls back to the base language and then English. It
names no business and makes no promise beyond "shortly", and avoids
gendered first-person forms where a language has them.
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

ONE_MOMENT: LocalizedText = build_localized_text(
    en="One moment, please — I'm checking and will answer you shortly.",
    ru="Минутку, пожалуйста — уточняю и скоро отвечу.",
    ka="ერთი წუთით — ვამოწმებ და მალე გიპასუხებთ.",
    tr="Bir dakika lütfen — kontrol ediyorum, birazdan yanıtlayacağım.",
    he="רגע אחד בבקשה — בודקים ונחזור אליך בקרוב.",
    ar="لحظة من فضلك — أتحقق من الأمر وسأرد عليك قريبًا.",
    hy="Մեկ րոպե, խնդրում եմ — ստուգում եմ և շուտով կպատասխանեմ։",
    uk="Хвилинку, будь ласка — уточнюю і скоро відповім.",
    de="Einen Moment bitte – ich prüfe das und antworte gleich.",
    fr="Un instant, s'il vous plaît — je vérifie et je vous réponds tout de suite.",
    es="Un momento, por favor: lo estoy comprobando y le respondo enseguida.",
    it="Un momento, per favore: sto verificando e le rispondo subito.",
    pt="Um momento, por favor — estou verificando e já respondo.",
    pl="Chwileczkę — sprawdzam i zaraz odpowiem.",
    az="Bir dəqiqə, zəhmət olmasa — yoxlayıram və tezliklə cavab verəcəyəm.",
    kk="Бір минут, өтінемін — тексеріп жатырмын, жақында жауап беремін.",
    zh="请稍等，我正在查询，马上回复您。",
    ja="少々お待ちください。確認してすぐにお返事します。",
    be="Хвілінку, калі ласка — удакладняю і хутка адкажу.",
    bg="Един момент, моля — проверявам и ще отговоря скоро.",
    bn="একটু অপেক্ষা করুন — যাচাই করছি, শীঘ্রই উত্তর দেব।",
    bs="Trenutak, molim — provjeravam i uskoro ću odgovoriti.",
    ca="Un moment, si us plau: ho estic comprovant i us responc de seguida.",
    cs="Moment, prosím — ověřuji to a hned odpovím.",
    da="Et øjeblik — jeg tjekker det og svarer om lidt.",
    el="Μια στιγμή, παρακαλώ — το ελέγχω και θα σας απαντήσω σύντομα.",
    et="Üks hetk, palun — kontrollin ja vastan kohe.",
    fa="لطفاً چند لحظه صبر کنید — در حال بررسی هستم و به‌زودی پاسخ می‌دهم.",
    fi="Hetkinen — tarkistan asian ja vastaan pian.",
    fil="Sandali lang po — tinitingnan ko at sasagot ako agad.",
    hi="कृपया एक पल रुकें — जाँच की जा रही है, जल्द ही जवाब मिलेगा।",
    hr="Trenutak, molim — provjeravam i uskoro ću odgovoriti.",
    hu="Egy pillanat — utánanézek, és hamarosan válaszolok.",
    id="Mohon tunggu sebentar — saya sedang memeriksanya dan akan segera membalas.",
    ko="잠시만 기다려 주세요. 확인 후 곧 답변드리겠습니다.",
    ky="Бир мүнөт күтө туруңуз — текшерип жатам, жакында жооп берем.",
    lt="Akimirką — tikrinu ir netrukus atsakysiu.",
    lv="Mirklīti, lūdzu — pārbaudu un drīz atbildēšu.",
    mk="Еден момент, ве молам — проверувам и наскоро ќе одговорам.",
    mn="Түр хүлээнэ үү — шалгаж байна, удахгүй хариулна.",
    ms="Sebentar ya — saya sedang menyemak dan akan membalas tidak lama lagi.",
    nb="Et øyeblikk — jeg sjekker og svarer straks.",
    nl="Een ogenblikje — ik zoek het even na en antwoord zo.",
    no="Et øyeblikk — jeg sjekker og svarer straks.",
    ro="O clipă, vă rog — verific și vă răspund imediat.",
    sk="Moment, prosím — overujem to a hneď odpoviem.",
    sl="Trenutek, prosim — preverjam in kmalu odgovorim.",
    sq="Një moment, ju lutem — po e kontrolloj dhe do t'ju përgjigjem së shpejti.",
    sr="Тренутак, молим — проверавам и ускоро ћу одговорити.",
    sv="Ett ögonblick — jag kollar och svarar strax.",
    sw="Subiri kidogo tafadhali — ninaangalia na nitakujibu hivi punde.",
    tg="Лутфан, як лаҳза — тафтиш карда истодаам ва ба наздикӣ ҷавоб медиҳам.",
    th="กรุณารอสักครู่ กำลังตรวจสอบและจะตอบกลับในไม่ช้า",
    ur="براہ کرم ایک لمحہ — جانچ کی جا رہی ہے، جلد جواب دیا جائے گا۔",
    uz="Bir daqiqa, iltimos — tekshiryapman va tez orada javob beraman.",
    vi="Xin chờ một chút — tôi đang kiểm tra và sẽ trả lời ngay.",
)
