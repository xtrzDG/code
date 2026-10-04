"""
A customer's STOP (or START) recorded on their contact and on the
business's suppression list: messages they did not ask for stop in every
channel (START brings them back), the change is audited (the customer made
it, so no actor), and the customer is told what changed in their language.

The suppression list keeps a digest of every way to reach the customer
(their numbers, this account), so the STOP outlives an erasure of their
data: a new contact with the same number or account is still not messaged.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.privacy import SuppressionListContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.feedback import CustomerSignalKind
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.feedback.customer_signals import CustomerSignalReply
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.privacy.suppression import SuppressedIdentity
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.channels.opt_out import with_opt_out
from app.utilities.channels.opt_out_texts import OPTED_IN_TEXT, OPTED_OUT_TEXT
from app.utilities.privacy.suppressed_identities import (
    channel_identity,
    contact_identities,
)

OPT_OUT_ENTITY: AuditEntityName = AuditEntityName("message_opt_out")


@dataclass(frozen=True)
class MessagingPreferences:
    contact_repo: ContactRepoContract
    audit_log_repo: AuditLogRepoContract
    text_resolver: LocalizedTextResolverContract
    suppression_list: SuppressionListContract

    def apply(
        self,
        turn: PreparedTurn,
        kind: CustomerSignalKind,
        now: Microseconds,
    ) -> CustomerSignalReply | None:
        """
        STOP: the conversation's channel joins the opted-out ones. START:
        every opt-out is lifted; None for a customer who never stopped
        anything (the assistant answers their "start").
        """

        contact: ContactDocument = (
            self.contact_repo.get(turn.business.id, turn.contact.id) or turn.contact
        )
        identities: list[SuppressedIdentity] = [
            channel_identity(
                turn.conversation.channel, turn.conversation.channel_user_id
            ),
            *contact_identities(contact),
        ]
        if kind is CustomerSignalKind.OPT_OUT:
            self.suppression_list.suppress(turn.business.id, identities, now)
            stopped = with_opt_out(contact, turn.conversation.channel)
            if stopped != contact.opted_out_channels:
                self._store(contact, stopped, AuditAction.CREATE, now)

            return self._reply(turn, kind, OPTED_OUT_TEXT)

        lifted: int = self.suppression_list.lift(turn.business.id, identities)
        if not contact.opted_out_channels:
            if lifted == 0:
                return None

            # STOP said before an erasure: only the list remembered it.
            self._audit(contact, AuditAction.DELETE, now)
            return self._reply(turn, kind, OPTED_IN_TEXT)

        self._store(contact, [], AuditAction.DELETE, now)
        return self._reply(turn, kind, OPTED_IN_TEXT)

    def _store(
        self,
        contact: ContactDocument,
        opted_out_channels: list[ChannelKind],
        action: AuditAction,
        now: Microseconds,
    ) -> None:
        contact.opted_out_channels = opted_out_channels
        contact.updated_at = now
        self.contact_repo.save(contact)
        self._audit(contact, action, now)

    def _audit(
        self, contact: ContactDocument, action: AuditAction, now: Microseconds
    ) -> None:
        self.audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=contact.business_id,
                action=action,
                entity=OPT_OUT_ENTITY,
                entity_id=AuditEntityReference(str(contact.id)),
                created_at=now,
                updated_at=now,
            )
        )

    def _reply(
        self,
        turn: PreparedTurn,
        kind: CustomerSignalKind,
        text: LocalizedText,
    ) -> CustomerSignalReply:
        template: str = str(self.text_resolver.resolve(text, turn.reply_language))
        return CustomerSignalReply(
            kind=kind,
            text=MessageText(template.format(business=turn.business.name)),
        )
