"""
The WhatsApp template a campaign may write with once a customer's 24-hour
window is closed: its own (WHATSAPP_REBOOKING_TEMPLATE, registered in
Meta's MARKETING category), never one of the service messages' utility
templates. Meta's category policy forbids promotion in a utility template,
and a confirmation, a reminder or a freed place must stay free of
promotion, so a campaign whose template shares a name with any of them
writes only inside the open window, as if it had none.
"""

import logging

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName

LOGGER: logging.Logger = logging.getLogger(__name__)


def service_template_names(settings: AppSettings) -> frozenset[str]:
    """
    The templates of the messages the platform sends that are not
    marketing: the service messages' utility templates and the sign-in
    codes' authentication template.
    """

    names: tuple[WhatsAppTemplateName | None, ...] = (
        settings.whatsapp_booking_confirmation_template_name,
        settings.whatsapp_reminder_template_name,
        settings.whatsapp_notification_template_name,
        settings.whatsapp_owner_report_template_name,
        settings.whatsapp_otp_template_name,
        settings.growth.waitlist_template_name,
    )
    return frozenset(str(name) for name in names if name is not None)


def dedicated_marketing_template(
    settings: AppSettings,
) -> WhatsAppTemplateName | None:
    """
    The campaigns' own template, or None when none is set or it is one a
    service message uses as well (logged: the operator registers a separate
    MARKETING template under its own name).
    """

    template: WhatsAppTemplateName | None = settings.growth.rebooking_template_name
    if template is None:
        return None

    if str(template) in service_template_names(settings):
        LOGGER.warning(
            "WHATSAPP_REBOOKING_TEMPLATE %s is a service message's template: "
            "campaigns write only inside the 24-hour window until it has its "
            "own MARKETING template.",
            template,
        )
        return None

    return template
