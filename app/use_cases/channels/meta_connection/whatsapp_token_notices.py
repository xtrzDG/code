"""Telling the owners of a WhatsApp number about its token from Meta."""

import logging

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.owner_emails import OwnerAccountEmailFacilitatorContract
from app.schemas.constants.meta_connection import WhatsAppTokenNoticeStage
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.notifications.staff_alerts import StaffAlert
from app.utilities.channels.whatsapp_token_notice_texts import (
    WhatsAppTokenNoticeTexts,
)
from app.utilities.channels.whatsapp_token_schedule import (
    notice_subject,
    notice_tag,
)
from app.utilities.scheduling.zoned_time import load_time_zone

logger: logging.Logger = logging.getLogger(__name__)


class WhatsAppTokenNotices:
    """
    The owners of the business (their devices with notifications on and
    the e-mail address of their account) and its staff contacts hear that
    the access Meta gave for the business's WhatsApp number was not
    renewed, ends within three days, or ended (urgent: it comes through
    quiet hours), with a link to Channels and the way to connect the
    number again. Each stage reaches each recipient once per token: the
    subject names the channel, the day the token ends and the stage.
    Owners who sign in by phone hear it on their devices and through the
    staff contacts only. Never raises.
    """

    def __init__(
        self,
        staff_alerts: StaffAlertFacilitatorContract,
        owner_emails: OwnerAccountEmailFacilitatorContract,
        resolver: LocalizedTextResolverContract,
    ) -> None:
        self._staff_alerts: StaffAlertFacilitatorContract = staff_alerts
        self._owner_emails: OwnerAccountEmailFacilitatorContract = owner_emails
        self._resolver: LocalizedTextResolverContract = resolver

    def notify(
        self,
        business: BusinessDocument,
        channel: ChannelDocument,
        stage: WhatsAppTokenNoticeStage,
    ) -> None:
        if channel.credential_expires_at is None:
            return  # A token that never ends needs no reminder.

        try:
            alert = StaffAlert(
                business_id=business.id,
                target=StaffLinkTarget.CHANNELS,
                tag=notice_tag(channel.id),
                subject=notice_subject(
                    channel.id, channel.credential_expires_at, stage
                ),
                is_urgent=stage is WhatsAppTokenNoticeStage.ENDED,
                member_roles=[BusinessMemberRole.OWNER],
            )
            texts = WhatsAppTokenNoticeTexts(
                self._resolver,
                business.name,
                stage,
                channel.credential_expires_at,
                load_time_zone(business.timezone),
            )
        except Exception:
            logger.exception(
                "The WhatsApp token notice of channel %s could not be made.",
                channel.id,
            )
            return

        try:
            self._staff_alerts.alert(business, alert, texts)
        except Exception:
            logger.exception(
                "The WhatsApp token notice of channel %s failed.", channel.id
            )

        try:
            self._owner_emails.email_owners(business, alert, texts)
        except Exception:
            logger.exception(
                "The WhatsApp token e-mail of channel %s failed.", channel.id
            )
