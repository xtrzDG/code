"""
The links the phone assistant promised during a call, and the message that
brings them to the caller afterwards.

On the phone send_link never hands the agent the address (see
`render_phone_link`): when a messenger reaches the caller, the result says
`texted_after_call` and the platform sends the links right after the call.
"""

import json
from collections.abc import Sequence
from typing import cast

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.localized_texts import build_localized_text

PROMISE_FIELD: str = "texted_after_call"
LINK_KINDS: dict[str, BusinessLinkKind] = {
    kind.value: kind for kind in BusinessLinkKind
}

# The first line of the message with the links promised during a call.
CALL_LINKS_TEXT: LocalizedText = build_localized_text(
    en="{business}: here are the links from your call.",
    ru="{business}: ссылки из вашего звонка.",
    ka="{business}: ბმულები თქვენი ზარიდან.",
    uk="{business}: посилання з вашого дзвінка.",
    hy="{business}․ ձեր զանգի հղումները։",
    he="{business}: הקישורים מהשיחה שלך.",
    ar="{business}: الروابط من مكالمتك.",
    tr="{business}: aramanızdaki bağlantılar.",
    pl="{business}: linki z Twojej rozmowy.",
    de="{business}: die Links aus Ihrem Anruf.",
    es="{business}: los enlaces de tu llamada.",
    fr="{business} : les liens de votre appel.",
    it="{business}: i link della tua chiamata.",
    pt="{business}: os links da sua ligação.",
    kk="{business}: қоңырауыңыздағы сілтемелер.",
)


def find_promised_link_kinds(
    messages: Sequence[MessageDocument],
) -> list[BusinessLinkKind]:
    """Kinds of links the agent promised to text, in call order, each once."""

    kinds: list[BusinessLinkKind] = []
    for message in messages:
        for record in message.tool_calls:
            if record.tool_name is not AssistantToolName.SEND_LINK or record.is_error:
                continue

            kind: BusinessLinkKind | None = read_promised_kind(str(record.result_json))
            if kind is not None and kind not in kinds:
                kinds.append(kind)

    return kinds


def read_promised_kind(result_json: str) -> BusinessLinkKind | None:
    """The link kind of a send_link result that promised a text, else None."""

    try:
        result: object = json.loads(result_json)
    except ValueError:
        return None

    if not isinstance(result, dict):
        return None

    fields: dict[str, object] = cast(dict[str, object], result)
    kind_value: object = fields.get("kind")
    if fields.get(PROMISE_FIELD) is not True or not isinstance(kind_value, str):
        return None

    return LINK_KINDS.get(kind_value)


def build_call_links_text(header: str, urls: Sequence[str]) -> str:
    """The header, then one link per line."""

    return "\n".join([header, *urls])
