"""
Banquet deposits: an open banquet request gets the owner's banquet policy
amount and link, shows its deposit to staff, and "Paid" or the link's
lapse keep it in step; a closed request or one that is not a banquet asks
none, and a status change made at the same moment never drops the deposit.
"""

from collections.abc import Callable

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.repositories.booking_repositories import LeadRepository
from app.schemas.constants.bookings import LeadStatus, LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deposits import (
    DepositExemption,
    DepositRule,
    DepositStatus,
    DepositSubject,
    DepositTarget,
    PaymentLinkOutcome,
)
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.deposits import BookingDepositPolicy, TargetedDepositPolicy
from app.schemas.dto.deposits.payment_link_requests import (
    PaymentLinkReceipt,
    SendPaymentLinkCommand,
)
from app.schemas.dto.operations.leads import UpdateLeadStatusCommand
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.prefixed_id import LeadId
from app.schemas.typings.bookings.strings import LeadDetails
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deposits.constrained_integers import DepositAmountMinor
from app.schemas.typings.deposits.prefixed_id import DepositRequestId
from app.use_cases.leads.update_lead_status_use_case import UpdateLeadStatusUseCase
from app.use_cases.shared.lead_views import build_lead_list_item
from tests.deposits.deposit_world import DepositWorld


def banquet_world(per_guest_minor: int = 1000) -> DepositWorld:
    """Deposits on, with 10.00 a guest asked of banquets from 20 guests."""

    world = DepositWorld()
    settings = world.take_deposits()
    settings.policies.append(
        TargetedDepositPolicy(
            target=DepositTarget.BANQUET,
            policy=BookingDepositPolicy(
                rule=DepositRule.PER_GUEST,
                amount_minor=DepositAmountMinor(per_guest_minor),
                currency_code=world.business.currency_code,
                min_party_size=PartySize(20),
            ),
        )
    )
    world.deposit_settings_repo.save(settings)
    return world


def banquet_request(
    world: DepositWorld,
    guest: ContactDocument,
    chat: ConversationDocument,
    party_size: int = 30,
    lead_type: LeadType = LeadType.BANQUET,
    status: LeadStatus = LeadStatus.NEW,
) -> LeadDocument:
    now = world.clock.now_microseconds()
    lead = LeadDocument(
        business_id=world.business.id,
        contact_id=guest.id,
        conversation_id=chat.id,
        lead_type=lead_type,
        details=LeadDetails("Wedding dinner"),
        party_size=PartySize(party_size),
        source_channel=ChannelKind.TELEGRAM,
        status=status,
        created_at=now,
        updated_at=now,
    )
    world.lead_repo.save(lead)
    return lead


def ask_for_request(
    world: DepositWorld,
    guest: ContactDocument,
    chat: ConversationDocument,
    lead: LeadDocument,
) -> PaymentLinkReceipt:
    return world.send_payment_link().run(
        SendPaymentLinkCommand(
            business_id=world.business.id,
            contact_id=guest.id,
            conversation_id=chat.id,
            source_channel=chat.channel,
            language=chat.language or world.business.default_language,
            lead_id=lead.id,
        )
    )


def lead_of(world: DepositWorld, lead: LeadDocument) -> LeadDocument:
    found = world.lead_repo.get(world.business.id, lead.id)
    assert found is not None
    return found


def waiting_banquet() -> tuple[DepositWorld, LeadDocument, DepositRequestId]:
    world = banquet_world()
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    lead = banquet_request(world, nino, chat)
    receipt = world.ask_deposit(nino, chat)
    assert receipt.issued is not None
    return world, lead, receipt.issued.request_id


def test_a_banquet_request_gets_the_banquet_amount_and_shows_it() -> None:
    world = banquet_world()
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    lead = banquet_request(world, nino, chat, party_size=30)

    receipt = world.ask_deposit(nino, chat)

    assert receipt.outcome is PaymentLinkOutcome.SENT
    assert receipt.subject is DepositSubject.BANQUET
    assert receipt.lead_id == lead.id
    assert receipt.issued is not None
    assert int(receipt.issued.amount.amount_minor) == 30000
    assert "sum=300.00" in str(receipt.issued.line)
    shown = lead_of(world, lead)
    assert shown.deposit is not None
    assert shown.deposit.request_id == receipt.issued.request_id
    assert shown.deposit.status is DepositStatus.AWAITING
    assert shown.status is LeadStatus.NEW
    row = build_lead_list_item(shown, nino)
    assert row.deposit is not None
    assert int(row.deposit.amount_minor) == 30000
    assert LiveEventKind.LEAD_CHANGED in world.live_events.kinds()


def test_a_closed_banquet_request_needs_no_deposit() -> None:
    world = banquet_world()
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    lead = banquet_request(world, nino, chat, status=LeadStatus.LOST)

    named = ask_for_request(world, nino, chat, lead)
    latest = world.ask_deposit(nino, chat)

    for receipt in (named, latest):
        assert receipt.outcome is PaymentLinkOutcome.NOT_REQUIRED
        assert receipt.exemption is DepositExemption.NOTHING_OPEN
    assert lead_of(world, lead).deposit is None


def test_a_request_that_is_no_banquet_needs_no_deposit() -> None:
    world = banquet_world()
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    lead = banquet_request(world, nino, chat, lead_type=LeadType.CORPORATE)

    receipt = ask_for_request(world, nino, chat, lead)

    assert receipt.outcome is PaymentLinkOutcome.NOT_REQUIRED
    assert receipt.exemption is DepositExemption.NOT_A_BANQUET
    assert lead_of(world, lead).deposit is None


def test_a_small_banquet_needs_no_deposit() -> None:
    world = banquet_world()
    nino = world.guest("Nino", "ru")
    chat = world.telegram_conversation(nino)
    lead = banquet_request(world, nino, chat, party_size=12)

    receipt = ask_for_request(world, nino, chat, lead)

    assert receipt.exemption is DepositExemption.SMALL_PARTY
    assert lead_of(world, lead).deposit is None


def test_paid_shows_on_the_banquet_request() -> None:
    world, lead, request_id = waiting_banquet()
    world.pass_minutes(10)

    view = world.mark_paid(request_id)

    assert view.status is DepositStatus.PAID
    shown = lead_of(world, lead)
    assert shown.deposit is not None
    assert shown.deposit.status is DepositStatus.PAID
    assert shown.deposit.hold_expires_at is None
    assert shown.status is LeadStatus.NEW


def test_a_lapsed_banquet_link_shows_expired_and_changes_nothing_else() -> None:
    world, lead, request_id = waiting_banquet()
    world.pass_minutes(60)

    world.sweep()

    assert world.request(request_id).status is DepositStatus.EXPIRED
    shown = lead_of(world, lead)
    assert shown.deposit is not None
    assert shown.deposit.status is DepositStatus.EXPIRED
    assert shown.status is LeadStatus.NEW
    assert world.live_events.kinds().count(LiveEventKind.LEAD_CHANGED) >= 2


class PaidRightAfterTheRead(LeadRepository):
    """
    The lead store of a status change that "Paid" overtakes: the moment the
    change first reads the lead, staff mark its deposit paid (an exact
    interleaving, no timing). An atomic change reads inside its write, so
    it sees the payment; a read-then-save would write the stale lead back.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[LeadDocument],
        overtake: Callable[[], object],
    ) -> None:
        super().__init__(collection)
        self._overtake: Callable[[], object] | None = overtake

    def _overtake_once(self) -> None:
        overtake, self._overtake = self._overtake, None
        if overtake is not None:
            overtake()

    def get(self, business_id: BusinessId, lead_id: LeadId) -> LeadDocument | None:
        found = super().get(business_id, lead_id)
        self._overtake_once()
        return found

    def update(
        self,
        business_id: BusinessId,
        lead_id: LeadId,
        change: Callable[[LeadDocument], LeadDocument | None],
    ) -> LeadDocument | None:
        self._overtake_once()
        return super().update(business_id, lead_id, change)


def test_a_status_change_overtaken_by_paid_keeps_the_paid_deposit() -> None:
    world, lead, request_id = waiting_banquet()
    store = PaidRightAfterTheRead(
        world.lead_collection, lambda: world.mark_paid(request_id)
    )
    change = UpdateLeadStatusUseCase(
        lead_repo=store,
        live_events=world.live_events,
        wall_clock=world.clock.wall_clock,
        refresh_open_request=world.refresh_open_request(),
    )

    change.run(
        UpdateLeadStatusCommand(
            business_id=world.business.id,
            lead_id=lead.id,
            status=LeadStatus.IN_PROGRESS,
        )
    )

    shown = lead_of(world, lead)
    assert shown.status is LeadStatus.IN_PROGRESS
    assert shown.deposit is not None
    assert shown.deposit.status is DepositStatus.PAID
