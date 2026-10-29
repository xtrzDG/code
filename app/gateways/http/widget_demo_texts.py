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
    "it": WidgetDemoTexts(
        title="Demo della chat sul sito — Assistant Workshop",
        heading="Demo della chat sul sito",
        intro=(
            "Questa pagina mostra il widget della chat esattamente come lo "
            "vedono i visitatori sul sito di un'attività. Il widget sceglie la "
            "lingua del visitatore dal browser tra le lingue dell'attività."
        ),
        embed_title="Codice da incorporare",
        embed_body=(
            "Incollalo prima del tag di chiusura </body> in ogni pagina del "
            "sito. Il pannello (Canali → Chat sul sito) lo mostra con "
            "l'indirizzo corretto."
        ),
        api_address="<indirizzo della tua API>",
        options_title="Opzioni",
        option_color="colore d'accento",
        option_position="pulsante della chat a sinistra",
        option_language="lingua dell'interfaccia",
        option_open="apre la chat sulla prima pagina della visita",
        option_mode=(
            "la chat occupa tutta la pagina (così funziona la pagina della chat "
            "ospitata)"
        ),
        business_id_label="ID dell'attività",
        show_button="Mostra il widget",
    ),
}
