"""
The growth world with deposits stored in memory: the settings and requests,
the settlement told by every booking change, the restaurant's payment page
and the policy of its big table.
"""

from datetime import datetime

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.deposits.deposit_aware_growth_facilitator import (
    DepositAwareGrowthFacilitator,
)
from app.facilitators.deposits.deposit_settlement_facilitator import (
    DepositSettlementFacilitator,
)
from app.repositories.booking_outcome_repository import BookingOutcomeRepository
from app.repositories.deposit_repositories import (
    DepositRequestRepository,
    DepositSettingsRepository,
)
from app.schemas.constants.deposits import DepositRule, DepositTarget, PaymentLinkKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.deposits import (
    BookingDepositPolicy,
    DepositRequestDocument,
    DepositSettingsDocument,
    PaymentLink,
    TargetedDepositPolicy,
)
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.deposits.constrained_integers import (
    DepositAmountMinor,
    DepositHoldMinutes,
    DepositRefundCutoffHours,
)
from app.schemas.typings.deposits.constrained_strings import (
    PaymentLinkAddress,
    PaymentLinkLabel,
)
from app.schemas.typings.deposits.strings import PaymentLinkHost, PaymentLinkPreview
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.deposits.payment_lines import PaymentLines
from app.utilities.deposits.deposit_keys import deposit_settings_id_of
from tests.operations.builders import DEFAULT_NOW
from tests.operations.fakes import ReversingSecretCipher
from tests.waitlist.growth_world import GrowthWorld

PAGE: str = "https://pay.example.com/deposit?sum={amount}&ref={reference}"
DAY: str = "2026-10-07"
OFFSET: str = "+04:00"


def at(time: str, day: str = DAY) -> str:
    return f"{day}T{time}:00{OFFSET}"


class DepositStore(GrowthWorld):
    """The restaurant's deposit store, its payment page and its policy."""

    def __init__(self, now: datetime = DEFAULT_NOW) -> None:
        super().__init__(now)
        self.deposit_settings_repo = DepositSettingsRepository(
            InMemoryDocumentCollectionAdapter(DepositSettingsDocument)
        )
        self.deposit_request_repo = DepositRequestRepository(
            InMemoryDocumentCollectionAdapter(DepositRequestDocument)
        )
        self.booking_outcome_repo = BookingOutcomeRepository(self.booking_collection)
        self.cipher = ReversingSecretCipher()
        self.settlement = DepositSettlementFacilitator(
            deposit_request_repo=self.deposit_request_repo,
            deposit_settings_repo=self.deposit_settings_repo,
            booking_repo=self.booking_repo,
            business_repo=self.business_repo,
            staff_alerts=self.staff_alerts,
            localized_text_resolver=self.resolver,
        )
        # Every booking use case of the world tells the deposits too.
        self.growth = DepositAwareGrowthFacilitator(
            inner=self.growth, deposits=self.settlement
        )
        self.lines = PaymentLines(
            secret_cipher=self.cipher, text_resolver=self.resolver
        )
        self.owner_id: UserId = self.business.members[0].user_id
        self.now_at: datetime = now

    # The owner's setup -------------------------------------------------

    def take_deposits(
        self,
        rule: DepositRule = DepositRule.PER_GUEST,
        amount_minor: int = 2000,
        min_party_size: int | None = 6,
        hold_minutes: int = 60,
        refund_cutoff_hours: int = 24,
        is_enabled: bool = True,
        resource: ResourceDocument | None = None,
    ) -> DepositSettingsDocument:
        """Deposits on: the bank's page and the policy of the big table."""

        now = self.clock.now_microseconds()
        link = PaymentLink(
            label=PaymentLinkLabel("Bank"),
            kind=PaymentLinkKind.TEMPLATE,
            address=PaymentLinkAddress(PAGE),
            host=PaymentLinkHost("pay.example.com"),
            preview=PaymentLinkPreview(PAGE),
            added_at=now,
        )
        target = resource or self.table_for_eight
        settings = DepositSettingsDocument(
            id=deposit_settings_id_of(self.business.id),
            business_id=self.business.id,
            is_enabled=is_enabled,
            hold_minutes=DepositHoldMinutes(hold_minutes),
            refund_cutoff_hours=DepositRefundCutoffHours(refund_cutoff_hours),
            payment_links=[link],
            default_payment_link_id=link.id,
            policies=[
                TargetedDepositPolicy(
                    target=DepositTarget.RESOURCE,
                    resource_id=target.id,
                    policy=BookingDepositPolicy(
                        rule=rule,
                        amount_minor=DepositAmountMinor(amount_minor),
                        currency_code=self.business.currency_code,
                        min_party_size=(
                            None
                            if min_party_size is None
                            else PartySize(min_party_size)
                        ),
                    ),
                )
            ],
            created_at=now,
            updated_at=now,
        )
        self.deposit_settings_repo.save(settings)
        return settings

    def big_table_booking(
        self,
        guest: ContactDocument,
        chat: ConversationDocument,
        party_size: int = 6,
        time: str = "19:00",
        day: str = DAY,
    ) -> BookingDocument:
        """The guest's evening at the big table, made in their chat."""

        hour = int(time.split(":")[0])
        booking = self.add_booking(
            self.business,
            self.table_for_eight,
            guest,
            at(time, day),
            at(f"{hour + 2:02d}:00", day),
            party_size=party_size,
        )
        booking.conversation_id = chat.id
        booking.source_channel = chat.channel
        booking.created_at = self.clock.now_microseconds()
        self.booking_repo.save(booking)
        return booking
