"""
The line that links the business's privacy notice under the AI disclosure
of the first reply in a messenger (WhatsApp, Telegram, Instagram,
Messenger), where the person has no page footer to find it.

It exists for the languages of the AI disclosure; resolution falls back to
the base language and then English. `{url}` is replaced with the notice's
address (see `fill_privacy_url`).
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

PRIVACY_URL_PLACEHOLDER: str = "{url}"

PRIVACY_NOTICE_LINE: LocalizedText = build_localized_text(
    en="Privacy notice: {url}",
    ru="Политика конфиденциальности: {url}",
    ka="კონფიდენციალურობის პოლიტიკა: {url}",
    tr="Gizlilik bildirimi: {url}",
    he="הודעת פרטיות: {url}",
    ar="إشعار الخصوصية: {url}",
    hy="Գաղտնիության քաղաքականություն՝ {url}",
    uk="Повідомлення про конфіденційність: {url}",
    de="Datenschutzhinweise: {url}",
    fr="Politique de confidentialité : {url}",
    es="Aviso de privacidad: {url}",
    it="Informativa sulla privacy: {url}",
    pt="Aviso de privacidade: {url}",
    pl="Informacja o prywatności: {url}",
    az="Məxfilik bildirişi: {url}",
    kk="Құпиялылық туралы хабарлама: {url}",
    zh="隐私声明：{url}",
    ja="プライバシーに関するお知らせ：{url}",
    be="Палітыка канфідэнцыяльнасці: {url}",
    bg="Политика за поверителност: {url}",
    bn="গোপনীয়তা বিজ্ঞপ্তি: {url}",
    bs="Obavještenje o privatnosti: {url}",
    ca="Avís de privadesa: {url}",
    cs="Zásady ochrany osobních údajů: {url}",
    da="Privatlivspolitik: {url}",
    el="Πολιτική απορρήτου: {url}",
    et="Privaatsusteade: {url}",
    fa="اطلاعیه حریم خصوصی: {url}",
    fi="Tietosuojaseloste: {url}",
    fil="Abiso sa privacy: {url}",
    hi="गोपनीयता सूचना: {url}",
    hr="Obavijest o privatnosti: {url}",
    hu="Adatvédelmi tájékoztató: {url}",
    id="Pemberitahuan privasi: {url}",
    ko="개인정보 처리방침: {url}",
    lt="Privatumo pranešimas: {url}",
    lv="Privātuma paziņojums: {url}",
    mk="Известување за приватност: {url}",
    ms="Notis privasi: {url}",
    nb="Personvernerklæring: {url}",
    nl="Privacyverklaring: {url}",
    no="Personvernerklæring: {url}",
    ro="Informare privind confidențialitatea: {url}",
    sk="Informácie o ochrane súkromia: {url}",
    sl="Obvestilo o zasebnosti: {url}",
    sq="Njoftimi i privatësisë: {url}",
    sr="Обавештење о приватности: {url}",
    sv="Integritetspolicy: {url}",
    sw="Taarifa ya faragha: {url}",
    th="ประกาศความเป็นส่วนตัว: {url}",
    ur="رازداری کا نوٹس: {url}",
    uz="Maxfiylik bildirishnomasi: {url}",
    vi="Thông báo quyền riêng tư: {url}",
    am="የግላዊነት ማስታወቂያ፦ {url}",
    bo="སྒེར་གསང་གསལ་བསྒྲགས། {url}",
    dv="ޕްރައިވެސީ ނޯޓިސް: {url}",
    gu="ગોપનીયતા સૂચના: {url}",
    km="សេចក្តីជូនដំណឹងអំពីឯកជនភាព៖ {url}",
    kn="ಗೌಪ್ಯತಾ ಸೂಚನೆ: {url}",
    lo="ແຈ້ງການຄວາມເປັນສ່ວນຕົວ: {url}",
    ml="സ്വകാര്യതാ അറിയിപ്പ്: {url}",
    mr="गोपनीयता सूचना: {url}",
    my="ကိုယ်ရေးအချက်အလက် ကာကွယ်မှု အသိပေးချက်- {url}",
    ne="गोपनीयता सूचना: {url}",
    pa="ਪਰਦੇਦਾਰੀ ਨੋਟਿਸ: {url}",
    si="රහස්‍යතා දැනුම්දීම: {url}",
    ta="தனியுரிமை அறிவிப்பு: {url}",
    te="గోప్యతా నోటీసు: {url}",
    # Odia: "or" is a keyword of Python.
    **{"or": "ଗୋପନୀୟତା ସୂଚନା: {url}"},
)


def fill_privacy_url(template: str, url: str) -> str:
    """Insert the notice's address into a resolved line."""

    return template.replace(PRIVACY_URL_PLACEHOLDER, url)
