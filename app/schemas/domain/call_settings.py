from base_pydantic_schemas import BaseDocument, SchemaVersion
from typed_time_provider import Microseconds

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calls.booleans import (
    IsCallRecordingEnabled,
    IsCallSummaryEnabled,
    IsSmsFallbackEnabled,
    IsStaffTransferConfirmed,
    IsTextBackEnabled,
)
from app.schemas.typings.calls.prefixed_id import CallSettingsId
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.users.prefixed_id import UserId


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

    Version 2 (optional fields, so version 1 rows read as they are):
    `is_recording_enabled`, whether the calls' audio is kept (off unless
    the owner turns it on; no business had a recording switch before, so
    every older row reads as off), and `is_staff_transfer_confirmed`, the
    owner's confirmation that staff taking transferred calls were told the
    voice platform may process the call after the transfer, with who
    confirmed it and when (`staff_transfer_confirmed_by`, `_at`): without
    it no call is put through to staff.
    """

    schema_version: SchemaVersion = SchemaVersion("2")
    id: CallSettingsId
    business_id: BusinessId
    is_summary_enabled: IsCallSummaryEnabled = True
    is_text_back_enabled: IsTextBackEnabled = False
    text_back_template_name: WhatsAppTemplateName | None = None
    is_sms_fallback_enabled: IsSmsFallbackEnabled = True
    is_recording_enabled: IsCallRecordingEnabled = False
    is_staff_transfer_confirmed: IsStaffTransferConfirmed = False
    staff_transfer_confirmed_by: UserId | None = None
    staff_transfer_confirmed_at: Microseconds | None = None
