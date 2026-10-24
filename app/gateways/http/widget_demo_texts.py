"""
The texts of the website chat demo page (/widget/demo) in the cabinet's
languages. The page is opened from the cabinet ("Channels -> Website chat",
"Try the assistant"), so it speaks the cabinet's language; the widget on it
picks its own language among the business languages.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WidgetDemoTexts:
    title: str
    heading: str
    intro: str
    embed_title: str
    embed_body: str
    api_address: str
    options_title: str
    option_color: str
    option_position: str
    option_language: str
    option_open: str
    option_mode: str
    business_id_label: str
    show_button: str


DEFAULT_DEMO_LANGUAGE: str = "en"

WIDGET_DEMO_TEXTS: dict[str, WidgetDemoTexts] = {
    "en": WidgetDemoTexts(
        title="Website chat demo — Assistant Workshop",
        heading="Website chat demo",
        intro=(
            "This page shows the chat widget exactly as visitors see it on a "
            "business website. The widget picks the visitor's language from the "
            "browser among the business languages."
        ),
        embed_title="Embed code",
        embed_body=(
            "Paste it before the closing </body> tag of every page of the "
            "website. The cabinet (Channels → Website chat) shows it with the "
            "right address."
        ),
        api_address="<your API address>",
        options_title="Options",
        option_color="accent colour",
        option_position="chat button on the left",
        option_language="interface language",
        option_open="open the chat on the first page of a visit",
        option_mode="the chat fills the page (the hosted chat page uses it)",
        business_id_label="Business id",
        show_button="Show the widget",
    ),
    "ru": WidgetDemoTexts(
        title="Демо чата на сайте — Мастерская ассистентов",
        heading="Демо чата на сайте",
        intro=(
            "Здесь виджет чата выглядит так же, как его видят посетители на "
            "сайте бизнеса. Язык виджет выбирает по браузеру посетителя среди "
            "языков бизнеса."
        ),
        embed_title="Код для сайта",
        embed_body=(
            "Вставьте его перед закрывающим тегом </body> на каждой странице "
            "сайта. В кабинете (Каналы → Чат на сайте) он показан с правильным "
            "адресом."
        ),
        api_address="<адрес вашего API>",
        options_title="Настройки",
        option_color="цвет акцента",
        option_position="кнопка чата слева",
        option_language="язык интерфейса",
        option_open="открыть чат на первой странице визита",
        option_mode="чат на всю страницу (так работает страница чата по ссылке)",
        business_id_label="Идентификатор бизнеса",
        show_button="Показать виджет",
    ),
    "ka": WidgetDemoTexts(
        title="ჩატი საიტზე: დემო — ასისტენტების სახელოსნო",
        heading="ჩატი საიტზე: დემო",
        intro=(
            "ეს გვერდი გაჩვენებთ ჩატის ვიჯეტს ზუსტად ისე, როგორც მას "
            "ვიზიტორები ბიზნესის საიტზე ხედავენ. ვიჯეტი ვიზიტორის ენას "
            "ბრაუზერის მიხედვით ირჩევს ბიზნესის ენებს შორის."
        ),
        embed_title="კოდი საიტისთვის",
        embed_body=(
            "ჩასვით ის დამხურავი </body> ტეგის წინ საიტის ყველა გვერდზე. "
            "კაბინეტში (არხები → ჩატი საიტზე) ის სწორი მისამართით არის "
            "ნაჩვენები."
        ),
        api_address="<თქვენი API-ის მისამართი>",
        options_title="პარამეტრები",
        option_color="აქცენტის ფერი",
        option_position="ჩატის ღილაკი მარცხნივ",
        option_language="ინტერფეისის ენა",
        option_open="ჩატის გახსნა ვიზიტის პირველივე გვერდზე",
        option_mode="ჩატი მთელ გვერდზე (ასე მუშაობს ბმულით გასახსნელი ჩატის გვერდი)",
        business_id_label="ბიზნესის იდენტიფიკატორი",
        show_button="ვიჯეტის ჩვენება",
    ),
}
