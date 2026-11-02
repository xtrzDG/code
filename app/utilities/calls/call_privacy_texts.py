"""
The sentence of a call's greeting that tells the caller where the privacy
notice is (GDPR art. 13: the caller learns where to read how their call is
processed before they say anything about themselves).

It points to the business's page on the web (its hosted chat page, whose
privacy section describes phone calls, or its own notice): a link is never
read aloud on the phone. It exists in every language the greeting has, so
an English sentence never ends a greeting in another language.
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

CALL_PRIVACY_NOTICE_HINT: LocalizedText = build_localized_text(
    en="Our privacy notice is on our web page.",
    ru="Политика конфиденциальности — на нашей веб-странице.",
    ka="კონფიდენციალურობის პოლიტიკა ჩვენს ვებგვერდზეა.",
    tr="Gizlilik bildirimimiz web sayfamızda yer alıyor.",
    he="הודעת הפרטיות שלנו נמצאת בדף האינטרנט שלנו.",
    ar="إشعار الخصوصية متاح على صفحتنا على الإنترنت.",
    hy="Գաղտնիության ծանուցումը մեր վեբ էջում է։",
    uk="Повідомлення про конфіденційність — на нашій вебсторінці.",
    de="Unsere Datenschutzhinweise finden Sie auf unserer Webseite.",
    fr="Notre politique de confidentialité se trouve sur notre page web.",
    es="Nuestro aviso de privacidad está en nuestra página web.",
    it="L'informativa sulla privacy è sulla nostra pagina web.",
    pt="Nosso aviso de privacidade está na nossa página na internet.",
    pl="Informacja o prywatności jest na naszej stronie internetowej.",
    az="Məxfilik bildirişimiz veb səhifəmizdədir.",
    kk="Құпиялылық туралы хабарлама біздің веб-парақшада.",
    zh="我们的隐私声明在我们的网页上。",
    ja="プライバシーに関するお知らせは当店のウェブページに掲載しています。",
    be="Паведамленне аб прыватнасці — на нашай вэб-старонцы.",
    bg="Известието за поверителност е на нашата уеб страница.",
    bn="আমাদের গোপনীয়তা বিজ্ঞপ্তি আমাদের ওয়েব পেজে আছে।",
    bs="Obavještenje o privatnosti nalazi se na našoj web stranici.",
    ca="El nostre avís de privadesa és a la nostra pàgina web.",
    cs="Informace o ochraně soukromí najdete na naší webové stránce.",
    da="Vores privatlivserklæring findes på vores hjemmeside.",
    el="Η ενημέρωση απορρήτου βρίσκεται στην ιστοσελίδα μας.",
    et="Meie privaatsusteade on meie veebilehel.",
    fa="اطلاعیهٔ حریم خصوصی ما در صفحهٔ وب ما است.",
    fi="Tietosuojailmoituksemme löytyy verkkosivultamme.",
    fil="Nasa aming web page ang aming privacy notice.",
    hi="हमारी गोपनीयता सूचना हमारे वेब पेज पर है।",
    hr="Obavijest o privatnosti nalazi se na našoj web-stranici.",
    hu="Adatvédelmi tájékoztatónk a weboldalunkon olvasható.",
    id="Pemberitahuan privasi kami ada di halaman web kami.",
    ko="개인정보 처리방침은 저희 웹페이지에서 보실 수 있습니다.",
    lt="Privatumo pranešimas pateiktas mūsų interneto puslapyje.",
    lv="Mūsu privātuma paziņojums ir mūsu tīmekļa lapā.",
    mk="Известувањето за приватност е на нашата веб-страница.",
    ms="Notis privasi kami ada di laman web kami.",
    nb="Personvernerklæringen vår finner du på nettsiden vår.",
    nl="Onze privacyverklaring staat op onze webpagina.",
    no="Personvernerklæringen vår finner du på nettsiden vår.",
    ro="Nota de informare privind confidențialitatea este pe pagina noastră web.",
    sk="Informácie o ochrane súkromia nájdete na našej webovej stránke.",
    sl="Obvestilo o zasebnosti je na naši spletni strani.",
    sq="Njoftimi ynë i privatësisë është në faqen tonë të internetit.",
    sr="Обавештење о приватности налази се на нашој веб-страници.",
    sv="Vår integritetspolicy finns på vår webbsida.",
    sw="Taarifa yetu ya faragha iko kwenye ukurasa wetu wa wavuti.",
    th="ประกาศความเป็นส่วนตัวของเราอยู่บนหน้าเว็บของเรา",
    ur="ہمارا رازداری کا نوٹس ہمارے ویب صفحے پر موجود ہے۔",
    uz="Maxfiylik bildirishnomamiz veb-sahifamizda joylashgan.",
    vi="Thông báo quyền riêng tư của chúng tôi có trên trang web của chúng tôi.",
)
