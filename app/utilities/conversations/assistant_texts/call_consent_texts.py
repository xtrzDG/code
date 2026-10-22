"""
The recording sentence of a call's first phrase where the law asks every
party's consent (`RecordingConsentRule.ALL_PARTY_CONSENT`, e.g. Germany,
France, Switzerland, Australia and the United States): the caller hears that
the call is recorded and that they may say no and go on without it (the
phone assistant then calls decline_recording). Elsewhere the call says
CALL_RECORDING_NOTICE (call_texts.py).

The languages are those of the notice; resolution falls back to the base
language and then English.
"""

from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

CALL_RECORDING_CONSENT: LocalizedText = build_localized_text(
    en=(
        "The call is recorded. If you do not want it recorded, just say so "
        "and we will continue without a recording."
    ),
    ru=(
        "Разговор записывается. Если вы не хотите, чтобы его записывали, "
        "просто скажите об этом, и мы продолжим без записи."
    ),
    ka=(
        "საუბარი იწერება. თუ არ გსურთ ჩაწერა, უბრალოდ თქვით და გავაგრძელებთ "
        "ჩაწერის გარეშე."
    ),
    tr=(
        "Görüşme kaydedilmektedir. Kaydedilmesini istemiyorsanız söylemeniz "
        "yeterli, kayıt olmadan devam ederiz."
    ),
    he="השיחה מוקלטת. אם אינכם רוצים שהשיחה תוקלט, פשוט אמרו זאת ונמשיך בלי הקלטה.",
    ar="يتم تسجيل المكالمة. إذا كنت لا ترغب في تسجيلها، فأخبرنا فقط وسنواصل دون تسجيل.",
    hy=(
        "Զանգը ձայնագրվում է։ Եթե չեք ցանկանում, որ այն ձայնագրվի, պարզապես "
        "ասեք, և կշարունակենք առանց ձայնագրության։"
    ),
    uk=(
        "Розмова записується. Якщо ви не хочете, щоб її записували, просто "
        "скажіть про це, і ми продовжимо без запису."
    ),
    de=(
        "Das Gespräch wird aufgezeichnet. Wenn Sie das nicht möchten, sagen Sie "
        "es einfach, dann sprechen wir ohne Aufzeichnung weiter."
    ),
    fr=(
        "L'appel est enregistré. Si vous ne le souhaitez pas, dites-le "
        "simplement et nous continuerons sans enregistrement."
    ),
    es=(
        "La llamada se está grabando. Si no desea que se grabe, solo dígalo y "
        "continuaremos sin grabación."
    ),
    it=(
        "La chiamata viene registrata. Se non desidera la registrazione, lo "
        "dica pure e continueremo senza registrare."
    ),
    pt=(
        "A ligação está sendo gravada. Se não quiser que seja gravada, é só "
        "dizer e continuamos sem gravação."
    ),
    pl=(
        "Rozmowa jest nagrywana. Jeśli nie chcą Państwo nagrania, proszę to "
        "powiedzieć, a będziemy kontynuować bez nagrywania."
    ),
    az=(
        "Zəng qeydə alınır. Qeydə alınmasını istəmirsinizsə, sadəcə deyin, "
        "qeydsiz davam edəcəyik."
    ),
    kk=(
        "Әңгіме жазылып жатыр. Жазылғанын қаламасаңыз, соны айтыңыз, жазбасыз "
        "жалғастырамыз."
    ),
    zh="本次通话将被录音。如果您不同意录音，请直接告诉我们，我们将在不录音的情况下继续。",
    ja="この通話は録音されます。録音をご希望でない場合はお申し付けください。録音せずに続けます。",
    be=(
        "Размова запісваецца. Калі вы не хочаце, каб яе запісвалі, проста "
        "скажыце пра гэта, і мы працягнем без запісу."
    ),
    bg=(
        "Разговорът се записва. Ако не желаете да бъде записван, просто "
        "кажете и ще продължим без запис."
    ),
    bn=(
        "এই কলটি রেকর্ড করা হচ্ছে। আপনি রেকর্ড করতে না চাইলে শুধু বলুন, আমরা "
        "রেকর্ড ছাড়াই কথা চালিয়ে যাব।"
    ),
    bs=(
        "Poziv se snima. Ako ne želite da se snima, samo recite i nastavit "
        "ćemo bez snimanja."
    ),
    ca=(
        "La trucada s'està enregistrant. Si no voleu que s'enregistri, només "
        "cal que ho digueu i continuarem sense enregistrament."
    ),
    cs=(
        "Hovor je nahráván. Pokud si nahrávání nepřejete, stačí to říct a "
        "budeme pokračovat bez nahrávání."
    ),
    da=(
        "Opkaldet bliver optaget. Hvis du ikke ønsker det, så sig det bare, så "
        "fortsætter vi uden optagelse."
    ),
    el=(
        "Η κλήση καταγράφεται. Αν δεν επιθυμείτε την καταγραφή, απλώς πείτε το "
        "και θα συνεχίσουμε χωρίς καταγραφή."
    ),
    et=(
        "Kõne salvestatakse. Kui te salvestamist ei soovi, öelge seda ja "
        "jätkame ilma salvestuseta."
    ),
    fa=(
        "این تماس ضبط می‌شود. اگر نمی‌خواهید ضبط شود، کافی است بگویید "
        "تا بدون ضبط ادامه دهیم."
    ),
    fi=(
        "Puhelu nauhoitetaan. Jos et halua nauhoitusta, sano se, niin jatkamme "
        "ilman nauhoitusta."
    ),
    fil=(
        "Nire-record ang tawag na ito. Kung ayaw ninyong ma-record, sabihin "
        "lang po at magpapatuloy tayo nang walang recording."
    ),
    hi=(
        "यह कॉल रिकॉर्ड की जा रही है। अगर आप रिकॉर्डिंग नहीं चाहते, तो बस बता "
        "दीजिए, हम बिना रिकॉर्डिंग के बात जारी रखेंगे।"
    ),
    hr=(
        "Poziv se snima. Ako ne želite snimanje, samo recite i nastavit ćemo "
        "bez snimanja."
    ),
    hu=(
        "A hívást rögzítjük. Ha nem szeretné, hogy rögzítsük, csak mondja, és "
        "felvétel nélkül folytatjuk."
    ),
    id=(
        "Panggilan ini direkam. Jika Anda tidak ingin direkam, cukup katakan "
        "dan kami akan melanjutkan tanpa rekaman."
    ),
    ko=(
        "이 통화는 녹음됩니다. 녹음을 원하지 않으시면 말씀해 주세요. "
        "녹음 없이 계속하겠습니다."
    ),
    lt=(
        "Pokalbis įrašomas. Jei nenorite, kad jis būtų įrašomas, tiesiog "
        "pasakykite ir tęsime be įrašo."
    ),
    lv=(
        "Saruna tiek ierakstīta. Ja nevēlaties ierakstu, vienkārši pasakiet, un "
        "turpināsim bez ieraksta."
    ),
    mk=(
        "Разговорот се снима. Ако не сакате да се снима, само кажете и ќе "
        "продолжиме без снимање."
    ),
    ms=(
        "Panggilan ini dirakam. Jika anda tidak mahu dirakam, beritahu sahaja "
        "dan kami akan teruskan tanpa rakaman."
    ),
    nb=(
        "Samtalen blir tatt opp. Hvis du ikke vil det, er det bare å si fra, så "
        "fortsetter vi uten opptak."
    ),
    nl=(
        "Het gesprek wordt opgenomen. Wilt u dat niet, zeg het dan gerust; dan "
        "gaan we verder zonder opname."
    ),
    no=(
        "Samtalen blir tatt opp. Hvis du ikke vil det, er det bare å si fra, så "
        "fortsetter vi uten opptak."
    ),
    ro=(
        "Apelul este înregistrat. Dacă nu doriți să fie înregistrat, spuneți-ne "
        "și vom continua fără înregistrare."
    ),
    sk=(
        "Hovor sa nahráva. Ak si nahrávanie neželáte, stačí to povedať a budeme "
        "pokračovať bez nahrávania."
    ),
    sl=(
        "Klic se snema. Če snemanja ne želite, to preprosto povejte in "
        "nadaljevali bomo brez posnetka."
    ),
    sq=(
        "Telefonata po regjistrohet. Nëse nuk dëshironi të regjistrohet, "
        "thjesht na e thoni dhe do të vazhdojmë pa regjistrim."
    ),
    sr="Позив се снима. Ако не желите снимање, само реците и наставићемо без снимања.",
    sv=(
        "Samtalet spelas in. Om du inte vill det räcker det att säga till, så "
        "fortsätter vi utan inspelning."
    ),
    sw=(
        "Simu hii inarekodiwa. Ikiwa hutaki irekodiwe, sema tu na tutaendelea "
        "bila kurekodi."
    ),
    th=("การสนทนานี้มีการบันทึกเสียง หากคุณไม่ต้องการให้บันทึก เพียงแจ้งเรา แล้วเราจะคุยต่อโดยไม่บันทึก"),
    ur=(
        "یہ کال ریکارڈ کی جا رہی ہے۔ اگر آپ ریکارڈنگ نہیں چاہتے تو بس بتا دیں، "
        "ہم ریکارڈنگ کے بغیر بات جاری رکھیں گے۔"
    ),
    uz=(
        "Qo'ng'iroq yozib olinmoqda. Agar yozib olinishini istamasangiz, "
        "shunchaki ayting, yozuvsiz davom etamiz."
    ),
    vi=(
        "Cuộc gọi này đang được ghi âm. Nếu bạn không muốn ghi âm, chỉ cần nói "
        "với chúng tôi và chúng ta sẽ tiếp tục mà không ghi âm."
    ),
)
