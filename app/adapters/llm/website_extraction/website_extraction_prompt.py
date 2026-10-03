"""What the website reader model is asked, for one page of a business's site."""

from collections.abc import Sequence

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.knowledge.website.website_text_fencing import (
    describe_fence,
    fence_website_text,
)

MAX_OUTPUT_TOKENS: int = 8_000
KIND_MEANINGS: dict[KnowledgeItemKind, str] = {
    KnowledgeItemKind.FAQ: "faq for a question customers ask, with its answer",
    KnowledgeItemKind.POLICY: (
        "policy for rules and practical information (opening hours, "
        "delivery, payment, cancellation, parking, address and how to get there)"
    ),
    KnowledgeItemKind.MENU_ITEM: "menu_item for food and drinks",
    KnowledgeItemKind.SERVICE: "service for services",
    KnowledgeItemKind.ROOM_TYPE: "room_type for rooms",
    KnowledgeItemKind.PACKAGE: "package for packages and sets",
    KnowledgeItemKind.VEHICLE: "vehicle for vehicles",
    KnowledgeItemKind.PRODUCT: "product for goods",
}


def build_instructions(
    allowed_kinds: Sequence[KnowledgeItemKind], fence_key: str
) -> str:
    """The system prompt: the item shape, the rules and the fence."""

    kinds: str = "; ".join(KIND_MEANINGS[kind] for kind in allowed_kinds)
    return (
        "You read one page of a business's own website and list the facts a "
        "customer assistant may use to answer the business's customers. "
        'Answer with one JSON object only: {"items": [...]}, no prose and no '
        "code fences.\n"
        "Each item has these fields:\n"
        f"- kind: {kinds}. Use no other kind.\n"
        "- title: for faq the question as a customer would ask it; for policy "
        'a short name such as "Opening hours"; otherwise the name exactly as '
        "written. In the language of the page.\n"
        "- body: the answer, the rule or a short description as written on the "
        "page (at most three sentences), else null.\n"
        "- price: the written price as a plain number in major units with a dot "
        "(for example 18.50), else null. Never compute, convert or guess a price.\n"
        "- currency: the ISO 4217 code of the written currency (₾ is GEL, € is "
        "EUR, $ is USD, ₪ is ILS, ֏ is AMD), or null when no currency is written.\n"
        "- duration_minutes: the written duration of a service, else null.\n"
        "- tags: up to five short lowercase English tags, or an empty list.\n"
        "- confidence: from 0 to 1, how sure you are that the page states the "
        "item as you wrote it.\n"
        "Rules:\n"
        "- Only facts written on this page. Do not invent, generalize or fill "
        "gaps. A page without such facts (a blog post, a gallery, legal text) "
        'gives {"items": []}.\n'
        "- Opening hours are one policy item with every day in its body.\n"
        "- Skip navigation, cookie notices, newsletter and social media prompts, "
        "reviews and testimonials, and anything about other businesses.\n"
        f"- {describe_fence(fence_key)}"
    )


def build_page_message(
    page_url: str,
    title: str | None,
    text: str,
    currency_code: CurrencyCode,
    fence_key: str,
) -> str:
    """The user turn: where the page is, the business currency, the fenced text."""

    fenced_content: str = text if title is None else f"Title: {title}\n\n{text}"
    return (
        f"Page address: {page_url}\n"
        f"If no currency is written, the business currency is {currency_code}.\n"
        f"{fence_website_text(fenced_content, fence_key)}"
    )
