"""
Where owner-facing catalog texts live, for the policy test and the catalog
tests: the plan catalog, the niche templates, the call forwarding guides,
the staff notification texts and the billing texts, and apart from them
the wording of issued invoices and receipts (reviewed languages only).

Customer-facing texts (the confirmations, reminders and replies customers
read, in any of the widget's languages) are not owner texts: they live
next to them in the notification package and stay out of these lists.
"""

import importlib
from types import ModuleType

from pydantic import BaseModel

from app.registries.billing.plan_registry import PlanRegistry
from app.registries.localization.call_forwarding_carriers import (
    CARRIER_GUIDES_BY_COUNTRY,
)
from app.registries.localization.call_forwarding_guide_registry import (
    CallForwardingGuideRegistry,
)
from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import CountryCode

# Modules whose module-level texts are read by owners and their staff.
OWNER_TEXT_MODULES: tuple[str, ...] = (
    "app.registries.billing.plan_catalog",
    "app.registries.localization.call_forwarding_texts",
    "app.registries.localization.call_forwarding_carriers",
    "app.transformers.notifications.booking_cancelled_notification_transformer",
    "app.transformers.notifications.booking_moved_notification_transformer",
    "app.transformers.notifications.calendar_event_text_transformer",
    "app.transformers.notifications.call_report_texts",
    "app.transformers.notifications.handoff_notification_transformer",
    "app.transformers.notifications.handoff_summary_texts",
    "app.transformers.notifications.message_rendering",
    "app.transformers.notifications.new_booking_notification_transformer",
    "app.transformers.notifications.new_lead_notification_transformer",
    "app.transformers.notifications.staff_alert_texts",
    "app.transformers.notifications.value_digest_texts",
    "app.transformers.billing.billing_texts",
    "app.utilities.billing.win_back_texts",
)
# Modules whose texts are printed on issued invoices and receipts: they
# carry reviewed languages only (a draft would stay on a kept document).
ISSUED_DOCUMENT_MODULES: tuple[str, ...] = (
    "app.transformers.billing.invoice_wording_texts",
    "app.transformers.invoicing.billing_document_texts",
    "app.transformers.invoicing.invoice_line_texts_transformer",
)
# Texts in owner modules that customers read (in their own language).
CUSTOMER_TEXT_NAMES: dict[str, str] = {
    "app.transformers.notifications.message_rendering.CANCELLATION_POLICY": (
        "the cancellation policy line of a customer's booking confirmation"
    ),
}
# A country without named carriers: it gets the GSM codes only.
COUNTRY_WITHOUT_CARRIERS: CountryCode = CountryCode("US")


def collect_texts(value: object, found: list[LocalizedText]) -> None:
    """Every LocalizedText inside a value (DTOs, lists, tuples, mappings)."""

    if isinstance(value, LocalizedText):
        found.append(value)
    elif isinstance(value, BaseModel):
        for name in type(value).model_fields:
            collect_texts(getattr(value, name), found)
    elif isinstance(value, (list, tuple)):
        for item in value:
            collect_texts(item, found)
    elif isinstance(value, dict):
        for item in value.values():
            collect_texts(item, found)


def module_texts(module_name: str) -> list[LocalizedText]:
    module: ModuleType = importlib.import_module(module_name)
    found: list[LocalizedText] = []
    for name, value in vars(module).items():
        if f"{module_name}.{name}" in CUSTOMER_TEXT_NAMES or name.startswith("_"):
            continue
        if isinstance(value, (LocalizedText, BaseModel, list, tuple, dict)):
            collect_texts(value, found)

    return found


def cabinet_language_texts() -> list[LocalizedText]:
    """Owner texts shown in every cabinet language, as the service builds them."""

    found: list[LocalizedText] = []
    for module_name in OWNER_TEXT_MODULES:
        found.extend(module_texts(module_name))
    collect_texts(PlanRegistry().list_all(), found)
    collect_texts(NicheTemplateRegistry().list_all(), found)
    guides = CallForwardingGuideRegistry()
    for country_code in (*CARRIER_GUIDES_BY_COUNTRY, COUNTRY_WITHOUT_CARRIERS):
        collect_texts(guides.get(country_code), found)

    return found


def issued_document_texts() -> list[LocalizedText]:
    """The wording of issued invoices and receipts."""

    found: list[LocalizedText] = []
    for module_name in ISSUED_DOCUMENT_MODULES:
        found.extend(module_texts(module_name))

    return found


def owner_facing_texts() -> list[LocalizedText]:
    """Every owner-facing catalog text, as the running service builds it."""

    return cabinet_language_texts() + issued_document_texts()
