from base_pydantic_schemas import BaseDocument

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calls.booleans import (
    IsCallSummaryEnabled,
    IsSmsFallbackEnabled,
    IsTextBackEnabled,
)
from app.schemas.typings.calls.prefixed_id import CallSettingsId
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName


class CallSettingsDocument(BaseDocument):
    """
    What happens after the phone calls of one business (Settings → Calls).

    `is_summary_enabled`: staff get a short summary after every call, and
    a note about a caller who did not get through. `is_text_back_enabled`:
    a caller who did not get through gets a message on WhatsApp, in the
    approved template `text_back_template_name` of the business's WhatsApp
    number, or by SMS when WhatsApp cannot carry it and
    `is_sms_fallback_enabled`. Without a document: summaries on, text-backs
    off.
    """

    id: CallSettingsId
    business_id: BusinessId
    is_summary_enabled: IsCallSummaryEnabled = True
    is_text_back_enabled: IsTextBackEnabled = False
    text_back_template_name: WhatsAppTemplateName | None = None
    is_sms_fallback_enabled: IsSmsFallbackEnabled = True
