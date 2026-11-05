"""
The sentences of a call's greeting that say who is responsible for the
caller's data, what it is used for and where the full privacy notice is
(GDPR art. 13, the first layer of a layered notice): the caller learns it
before they say anything about themselves.

The business is the controller ({business}, filled with its name) and
uses the call only to handle the caller's request. The full notice is on
the business's web page (its hosted chat page, whose privacy section
describes phone calls, or its own notice), and the caller may ask for the
link: send_link texts it right after the call when a messenger reaches
the caller (a link is never read aloud on the phone). The text exists in
every language the greeting has, so an English sentence never ends a
greeting in another language.
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

CALL_PRIVACY_NOTICE_HINT: LocalizedText = build_localized_text(
    en=(
        "{business} is responsible for your data and uses it only to handle "
        "your request. For the full privacy notice, ask me for the link or see "
        "our web page."
    ),
    ru=(
        "«{business}» отвечает за ваши данные и использует их только для "
        "вашего обращения. Чтобы получить полную политику конфиденциальности, "
        "попросите у меня ссылку или откройте нашу веб-страницу."
    ),
    ka=(
        "{business} პასუხისმგებელია თქვენს მონაცემებზე და მათ მხოლოდ თქვენი "
        "მოთხოვნის შესასრულებლად იყენებს. კონფიდენციალურობის სრული "
        "პოლიტიკისთვის მთხოვეთ ბმული ან ეწვიეთ ჩვენს ვებგვერდს."
    ),
    tr=(
        "{business}, verilerinizden sorumludur ve bunları yalnızca talebinizi "
        "yerine getirmek için kullanır. Gizlilik bildiriminin tamamı için benden "
        "bağlantıyı isteyin veya web sayfamıza bakın."
    ),
    he=(
        "{business} אחראי על הנתונים שלכם ומשתמש בהם רק כדי לטפל בפנייה שלכם. "
        "להודעת הפרטיות המלאה, בקשו ממני את הקישור או עיינו בדף האינטרנט שלנו."
    ),
    ar=(
        "{business} مسؤول عن بياناتك ويستخدمها فقط لمعالجة طلبك. للاطلاع على "
        "إشعار الخصوصية الكامل، اطلب مني الرابط أو تفضّل بزيارة صفحتنا على "
        "الإنترنت."
    ),
    hy=(
        "{business}-ը պատասխանատու է ձեր տվյալների համար և օգտագործում է դրանք "
        "միայն ձեր հարցումը կատարելու համար։ Գաղտնիության ամբողջական "
        "ծանուցման համար խնդրեք ինձնից հղումը կամ այցելեք մեր վեբ էջը։"
    ),
    uk=(
        "«{business}» відповідає за ваші дані й використовує їх лише для "
        "вашого звернення. Щоб отримати повне повідомлення про "
        "конфіденційність, попросіть у мене посилання або відкрийте нашу "
        "вебсторінку."
    ),
    de=(
        "{business} ist für Ihre Daten verantwortlich und nutzt sie nur, um Ihr "
        "Anliegen zu bearbeiten. Die vollständigen Datenschutzhinweise finden "
        "Sie auf unserer Webseite, oder fragen Sie mich nach dem Link."
    ),
    fr=(
        "{business} est responsable de vos données et ne les utilise que pour "
        "traiter votre demande. Pour la politique de confidentialité complète, "
        "demandez-moi le lien ou consultez notre page web."
    ),
    es=(
        "{business} es responsable de sus datos y solo los usa para atender su "
        "solicitud. Para el aviso de privacidad completo, pídame el enlace o "
        "consulte nuestra página web."
    ),
    it=(
        "{business} è titolare del trattamento dei suoi dati e li usa solo per "
        "gestire la sua richiesta. Per l'informativa privacy completa, mi "
        "chieda il link o consulti la nostra pagina web."
    ),
    pt=(
        "{business} é responsável pelos seus dados e os usa apenas para atender "
        "à sua solicitação. Para o aviso de privacidade completo, peça-me o "
        "link ou consulte nossa página na internet."
    ),
    pl=(
        "{business} odpowiada za Państwa dane i wykorzystuje je wyłącznie do "
        "obsługi Państwa sprawy. Pełna informacja o prywatności jest na naszej "
        "stronie internetowej; na życzenie wyślę też link."
    ),
    az=(
        "{business} məlumatlarınıza görə məsuliyyət daşıyır və onlardan yalnız "
        "sorğunuzu yerinə yetirmək üçün istifadə edir. Tam məxfilik bildirişi "
        "üçün məndən linki istəyin və ya veb səhifəmizə baxın."
    ),
    kk=(
        "{business} деректеріңізге жауап береді және оларды тек сұрауыңызды "
        "орындау үшін пайдаланады. Құпиялылық туралы толық хабарлама үшін "
        "менен сілтемені сұраңыз немесе веб-парақшамызды қараңыз."
    ),
    zh=(
        "{business}负责您的数据，仅用于处理您的请求。如需完整的隐私声明，"
        "请向我索取链接，或访问我们的网页。"
    ),
    ja=(
        "{business}がお客様のデータの管理責任者であり、ご用件の対応にのみ"
        "使用します。プライバシーに関するお知らせの全文は、リンクをお申し付け"
        "いただくか、当店のウェブページでご確認ください。"
    ),
    be=(
        "«{business}» адказвае за вашы даныя і выкарыстоўвае іх толькі для "
        "вашага звароту. Каб атрымаць поўнае паведамленне аб прыватнасці, "
        "папрасіце ў мяне спасылку або адкрыйце нашу вэб-старонку."
    ),
    bg=(
        "{business} отговаря за Вашите данни и ги използва само за обработка "
        "на Вашето запитване. За пълното известие за поверителност ме "
        "помолете за линка или посетете нашата уеб страница."
    ),
    bn=(
        "{business} আপনার তথ্যের দায়িত্বে আছে এবং শুধু আপনার অনুরোধ পূরণে তা "
        "ব্যবহার করে। সম্পূর্ণ গোপনীয়তা বিজ্ঞপ্তির জন্য আমার কাছে লিংক চান "
        "অথবা আমাদের ওয়েব পেজ দেখুন।"
    ),
    bs=(
        "{business} je odgovoran za vaše podatke i koristi ih samo za obradu "
        "vašeg zahtjeva. Za potpuno obavještenje o privatnosti zatražite od "
        "mene link ili posjetite našu web stranicu."
    ),
    ca=(
        "{business} és responsable de les vostres dades i només les fa servir "
        "per atendre la vostra sol·licitud. Per a l'avís de privadesa complet, "
        "demaneu-me l'enllaç o consulteu la nostra pàgina web."
    ),
    cs=(
        "{business} odpovídá za vaše údaje a používá je jen k vyřízení vašeho "
        "požadavku. Úplné informace o ochraně soukromí najdete na naší webové "
        "stránce, nebo si ode mě vyžádejte odkaz."
    ),
    da=(
        "{business} er ansvarlig for dine data og bruger dem kun til at "
        "behandle din henvendelse. Den fulde privatlivserklæring finder du på "
        "vores hjemmeside, eller bed mig om linket."
    ),
    el=(
        "Η επιχείρηση {business} είναι υπεύθυνη για τα δεδομένα σας και τα "
        "χρησιμοποιεί μόνο για να εξυπηρετήσει το αίτημά σας. Για την πλήρη "
        "ενημέρωση απορρήτου, ζητήστε μου τον σύνδεσμο ή επισκεφθείτε την "
        "ιστοσελίδα μας."
    ),
    et=(
        "{business} vastutab teie andmete eest ja kasutab neid ainult teie "
        "päringu täitmiseks. Täieliku privaatsusteate saamiseks küsige minult "
        "linki või vaadake meie veebilehte."
    ),
    fa=(
        "{business} مسئول داده‌های شماست و فقط برای رسیدگی به درخواست شما از "
        "آن‌ها استفاده می‌کند. برای اطلاعیهٔ کامل حریم خصوصی، لینک را از من "
        "بخواهید یا به صفحهٔ وب ما مراجعه کنید."
    ),
    fi=(
        "{business} vastaa tiedoistasi ja käyttää niitä vain pyyntösi "
        "hoitamiseen. Koko tietosuojailmoituksen löydät verkkosivultamme, tai "
        "pyydä minulta linkki."
    ),
    fil=(
        "Ang {business} ang may pananagutan sa iyong datos at ginagamit lang "
        "ito para asikasuhin ang iyong kahilingan. Para sa buong privacy "
        "notice, hingin sa akin ang link o tingnan ang aming web page."
    ),
    hi=(
        "{business} आपके डेटा के लिए ज़िम्मेदार है और इसका उपयोग केवल आपके "
        "अनुरोध को पूरा करने के लिए करता है। पूरी गोपनीयता सूचना के लिए मुझसे "
        "लिंक माँगें या हमारा वेब पेज देखें।"
    ),
    hr=(
        "{business} odgovoran je za vaše podatke i koristi ih samo za obradu "
        "vašeg zahtjeva. Za cjelovitu obavijest o privatnosti zatražite od "
        "mene poveznicu ili posjetite našu web-stranicu."
    ),
    hu=(
        "Az Ön adataiért {business} felel, és csak a kérése intézésére "
        "használja őket. A teljes adatvédelmi tájékoztatóért kérje tőlem a "
        "linket, vagy nézze meg a weboldalunkat."
    ),
    id=(
        "{business} bertanggung jawab atas data Anda dan hanya menggunakannya "
        "untuk menangani permintaan Anda. Untuk pemberitahuan privasi lengkap, "
        "minta tautannya kepada saya atau kunjungi halaman web kami."
    ),
    ko=(
        "{business}은(는) 고객님의 정보에 책임을 지며, 요청을 처리하는 데에만 "
        "사용합니다. 전체 개인정보 처리방침은 저에게 링크를 요청하시거나 저희 "
        "웹페이지에서 확인하실 수 있습니다."
    ),
    lt=(
        "{business} atsako už jūsų duomenis ir naudoja juos tik jūsų užklausai "
        "įvykdyti. Norėdami perskaityti visą privatumo pranešimą, paprašykite "
        "manęs nuorodos arba apsilankykite mūsų interneto puslapyje."
    ),
    lv=(
        "{business} atbild par jūsu datiem un izmanto tos tikai jūsu "
        "pieprasījuma izpildei. Pilnu privātuma paziņojumu atradīsiet mūsu "
        "tīmekļa lapā, vai palūdziet man saiti."
    ),
    mk=(
        "{business} е одговорен за вашите податоци и ги користи само за "
        "обработка на вашето барање. За целосното известување за приватност, "
        "побарајте ми линк или посетете ја нашата веб-страница."
    ),
    ms=(
        "{business} bertanggungjawab ke atas data anda dan hanya menggunakannya "
        "untuk mengendalikan permintaan anda. Untuk notis privasi penuh, minta "
        "pautan daripada saya atau lawati laman web kami."
    ),
    nb=(
        "{business} er ansvarlig for dataene dine og bruker dem bare til å "
        "behandle henvendelsen din. Den fullstendige personvernerklæringen "
        "finner du på nettsiden vår, eller be meg om lenken."
    ),
    nl=(
        "{business} is verantwoordelijk voor uw gegevens en gebruikt ze alleen "
        "om uw verzoek af te handelen. Voor de volledige privacyverklaring kunt "
        "u mij om de link vragen of onze webpagina bekijken."
    ),
    no=(
        "{business} er ansvarlig for dataene dine og bruker dem bare til å "
        "behandle henvendelsen din. Den fullstendige personvernerklæringen "
        "finner du på nettsiden vår, eller be meg om lenken."
    ),
    ro=(
        "{business} răspunde de datele dumneavoastră și le folosește doar "
        "pentru a vă soluționa solicitarea. Pentru nota de informare completă "
        "privind confidențialitatea, cereți-mi linkul sau vizitați pagina "
        "noastră web."
    ),
    sk=(
        "{business} zodpovedá za vaše údaje a používa ich len na vybavenie "
        "vašej požiadavky. Úplné informácie o ochrane súkromia nájdete na našej "
        "webovej stránke, alebo si odo mňa vyžiadajte odkaz."
    ),
    sl=(
        "{business} je odgovoren za vaše podatke in jih uporablja samo za "
        "obravnavo vaše zahteve. Za celotno obvestilo o zasebnosti me prosite "
        "za povezavo ali obiščite našo spletno stran."
    ),
    sq=(
        "{business} është përgjegjës për të dhënat tuaja dhe i përdor ato "
        "vetëm për të trajtuar kërkesën tuaj. Për njoftimin e plotë të "
        "privatësisë, më kërkoni lidhjen ose vizitoni faqen tonë të internetit."
    ),
    sr=(
        "{business} је одговоран за ваше податке и користи их само за обраду "
        "вашег захтева. За потпуно обавештење о приватности затражите од мене "
        "линк или посетите нашу веб-страницу."
    ),
    sv=(
        "{business} ansvarar för dina uppgifter och använder dem bara för att "
        "hantera ditt ärende. Hela integritetspolicyn finns på vår webbsida, "
        "eller be mig om länken."
    ),
    sw=(
        "{business} inawajibika kwa data yako na inaitumia tu kushughulikia "
        "ombi lako. Kwa taarifa kamili ya faragha, niombe kiungo au tembelea "
        "ukurasa wetu wa wavuti."
    ),
    th=(
        "{business} เป็นผู้รับผิดชอบข้อมูลของคุณและใช้ข้อมูลนั้นเพื่อดำเนินการตาม"
        "คำขอของคุณเท่านั้น หากต้องการประกาศความเป็นส่วนตัวฉบับเต็ม "
        "ขอลิงก์จากฉันหรือดูที่หน้าเว็บของเรา"
    ),
    ur=(
        "{business} آپ کے ڈیٹا کا ذمہ دار ہے اور اسے صرف آپ کی درخواست نمٹانے "
        "کے لیے استعمال کرتا ہے۔ مکمل رازداری نوٹس کے لیے مجھ سے لنک مانگیں یا "
        "ہمارا ویب صفحہ دیکھیں۔"
    ),
    uz=(
        "{business} maʼlumotlaringiz uchun javobgar va ulardan faqat "
        "so‘rovingizni bajarish uchun foydalanadi. To‘liq maxfiylik "
        "bildirishnomasi uchun mendan havolani so‘rang yoki veb-sahifamizga "
        "qarang."
    ),
    vi=(
        "{business} chịu trách nhiệm về dữ liệu của bạn và chỉ dùng dữ liệu đó "
        "để xử lý yêu cầu của bạn. Để xem toàn bộ thông báo quyền riêng tư, "
        "hãy hỏi tôi đường liên kết hoặc xem trang web của chúng tôi."
    ),
)
