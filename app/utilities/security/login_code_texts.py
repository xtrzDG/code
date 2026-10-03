"""
Texts of login code messages (SMS and e-mail), resolved with the
LocalizedText fallback: requested tag -> base language -> English.

`{code}` and `{minutes}` are replaced with plain string replacement. SMS
texts name the service and stay in one part: 70 characters for texts
outside the GSM 7-bit alphabet (Cyrillic, Georgian, Hebrew, Arabic, Turkish
and Spanish letters), 160 otherwise.
Telegram Gateway and WhatsApp authentication templates are written by the
platforms themselves and need no text here.
"""

import html
import math

from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.messaging.strings import EmailBodyText
from app.schemas.typings.users.constrained_integers import OtpLifetimeSeconds
from app.schemas.typings.users.constrained_strings import OtpCode
from app.utilities.localization.localized_texts import build_localized_text

CODE_PLACEHOLDER: str = "{code}"
MINUTES_PLACEHOLDER: str = "{minutes}"
SECONDS_PER_MINUTE: int = 60

# Every text names the service, so a recipient can tell which sign-in the
# code is for (code-relay phishing), and stays within one SMS part.
LOGIN_CODE_SMS: LocalizedText = build_localized_text(
    en="Assistant Workshop sign-in code: {code}. Valid for {minutes} min. "
    "Do not share it.",
    ru="Assistant Workshop: код входа {code}, {minutes} мин. Никому не сообщайте.",
    ka="Assistant Workshop: შესვლის კოდი {code}, {minutes} წთ. არავის უთხრათ.",
    uk="Assistant Workshop: код входу {code}, {minutes} хв. Нікому не кажіть.",
    tr="Assistant Workshop giriş kodu: {code}, {minutes} dk. Kimseye söylemeyin.",
    he="Assistant Workshop: קוד כניסה {code}. בתוקף {minutes} דק'. אין למסור לאיש.",
    ar="Assistant Workshop: رمز الدخول {code}، {minutes} دقيقة. لا تشاركه.",
    de="Assistant Workshop Anmeldecode: {code}. Gültig {minutes} Min. "
    "Nicht weitergeben.",
    fr="Code de connexion Assistant Workshop : {code}. Valable {minutes} min. "
    "Ne le partagez pas.",
    es="Assistant Workshop: código {code}, válido {minutes} min. No lo compartas.",
)

LOGIN_CODE_EMAIL_SUBJECT: LocalizedText = build_localized_text(
    en="Your sign-in code: {code}",
    ru="Ваш код входа: {code}",
    ka="თქვენი შესვლის კოდი: {code}",
    uk="Ваш код входу: {code}",
    tr="Giriş kodunuz: {code}",
    he="קוד הכניסה שלך: {code}",
    ar="رمز الدخول الخاص بك: {code}",
    de="Ihr Anmeldecode: {code}",
    fr="Votre code de connexion : {code}",
    es="Tu código de acceso: {code}",
)

# Paragraphs are separated by an empty line; the HTML version keeps them.
LOGIN_CODE_EMAIL_BODY: LocalizedText = build_localized_text(
    en="Hello!\n\n"
    "Your Assistant Workshop sign-in code:\n\n{code}\n\n"
    "It is valid for {minutes} minutes. Do not share it with anyone: our "
    "team never asks for it.\n\n"
    "If you did not try to sign in, ignore this e-mail.",
    ru="Здравствуйте!\n\n"
    "Ваш код входа в Assistant Workshop:\n\n{code}\n\n"
    "Он действует {minutes} мин. Никому его не сообщайте: наши сотрудники "
    "никогда его не спрашивают.\n\n"
    "Если вы не пытались войти, просто проигнорируйте это письмо.",
    ka="გამარჯობა!\n\n"
    "თქვენი Assistant Workshop-ის შესვლის კოდი:\n\n{code}\n\n"
    "კოდი მოქმედებს {minutes} წუთის განმავლობაში. არავის გაუზიაროთ: ჩვენი "
    "გუნდი მას არასდროს მოგთხოვთ.\n\n"
    "თუ შესვლა არ გიცდიათ, უბრალოდ უგულებელყავით ეს წერილი.",
    uk="Вітаємо!\n\n"
    "Ваш код входу в Assistant Workshop:\n\n{code}\n\n"
    "Він дійсний {minutes} хв. Нікому його не повідомляйте: наші працівники "
    "ніколи його не запитують.\n\n"
    "Якщо ви не намагалися увійти, просто проігноруйте цей лист.",
    tr="Merhaba!\n\n"
    "Assistant Workshop giriş kodunuz:\n\n{code}\n\n"
    "Kod {minutes} dakika geçerlidir. Kimseyle paylaşmayın: ekibimiz bu kodu "
    "asla sormaz.\n\n"
    "Giriş yapmayı denemediyseniz bu e-postayı dikkate almayın.",
    he="שלום!\n\n"
    "קוד הכניסה שלך ל-Assistant Workshop:\n\n{code}\n\n"
    "הקוד בתוקף {minutes} דקות. אין למסור אותו לאיש: הצוות שלנו לעולם לא "
    "יבקש אותו.\n\n"
    "אם לא ניסית להתחבר, אפשר להתעלם מהודעה זו.",
    ar="مرحبًا!\n\n"
    "رمز الدخول الخاص بك إلى Assistant Workshop:\n\n{code}\n\n"
    "الرمز صالح لمدة {minutes} دقيقة. لا تشاركه مع أحد: فريقنا لن يطلبه منك "
    "أبدًا.\n\n"
    "إذا لم تحاول تسجيل الدخول، فتجاهل هذه الرسالة.",
    de="Hallo!\n\n"
    "Ihr Anmeldecode für Assistant Workshop:\n\n{code}\n\n"
    "Er ist {minutes} Minuten gültig. Geben Sie ihn an niemanden weiter: "
    "unser Team fragt nie danach.\n\n"
    "Wenn Sie sich nicht anmelden wollten, ignorieren Sie diese E-Mail.",
    fr="Bonjour,\n\n"
    "Votre code de connexion à Assistant Workshop :\n\n{code}\n\n"
    "Il est valable {minutes} minutes. Ne le communiquez à personne : notre "
    "équipe ne vous le demandera jamais.\n\n"
    "Si vous n'avez pas essayé de vous connecter, ignorez cet e-mail.",
    es="¡Hola!\n\n"
    "Tu código de acceso a Assistant Workshop:\n\n{code}\n\n"
    "Es válido durante {minutes} minutos. No lo compartas con nadie: nuestro "
    "equipo nunca te lo pedirá.\n\n"
    "Si no intentaste iniciar sesión, ignora este correo.",
)


def lifetime_in_minutes(lifetime_seconds: OtpLifetimeSeconds) -> int:
    """Whole minutes a code stays valid (rounded up, at least one)."""

    return max(1, math.ceil(int(lifetime_seconds) / SECONDS_PER_MINUTE))


def fill_login_code_text(template: str, code: OtpCode, minutes: int) -> str:
    """Insert the code and its lifetime into a resolved template."""

    return template.replace(CODE_PLACEHOLDER, str(code)).replace(
        MINUTES_PLACEHOLDER, str(minutes)
    )


def build_login_code_email_html(
    template: str, code: OtpCode, minutes: int
) -> EmailBodyText:
    """
    HTML version of a resolved e-mail body: escaped paragraphs, the code
    large and spaced. `dir="auto"` lays Hebrew and Arabic out right to left.
    """

    paragraphs: list[str] = []
    for paragraph in template.split("\n\n"):
        if paragraph.strip() == CODE_PLACEHOLDER:
            paragraphs.append(
                '<p style="font-size:28px;font-weight:700;letter-spacing:6px;'
                'font-family:ui-monospace,Menlo,Consolas,monospace;margin:24px 0">'
                f"{html.escape(str(code))}</p>"
            )
            continue

        text: str = fill_login_code_text(paragraph, code, minutes)
        paragraphs.append(
            '<p style="margin:0 0 16px">'
            + html.escape(text).replace("\n", "<br>")
            + "</p>"
        )

    return EmailBodyText(
        '<!doctype html><html><body style="margin:0;padding:24px;'
        "font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;"
        'font-size:16px;line-height:1.5;color:#111827">'
        f'<div dir="auto" style="max-width:520px">{"".join(paragraphs)}</div>'
        "</body></html>"
    )
