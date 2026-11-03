"""
A campaign whose recent messages made too many customers opt out is held
for the platform team's review (ABUSE-05): it writes nothing more, its
owners are told why, and the platform alert counts it.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.campaigns import CampaignMessageStatus, RebookingRuleKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.businesses import BusinessMember
from app.schemas.domain.campaigns import (
    CampaignMessageDocument,
    CampaignSettingsDocument,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.campaigns.constrained_integers import CampaignMessageCount
from app.schemas.typings.campaigns.constrained_strings import CampaignMonthKey
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.campaigns.campaign_opt_out_review import (
    CampaignOptOutRate,
    measure_opt_outs,
)
from app.use_cases.campaigns.campaign_review_gate import CampaignReviewGate
from app.utilities.campaigns.campaign_keys import campaign_message_id_of
from tests.campaigns.campaign_world import CampaignWorld
from tests.campaigns.test_rebooking_campaigns import VISIT_ENDS, VISIT_STARTS
from tests.invoicing.attachment_fakes import RecordingStaffNotifier
from tests.platform_ops.failure_signal_doubles import CountedSignals

DAY: int = 24 * 60 * 60 * 1_000_000


def write_to(
    world: CampaignWorld, guest: ContactDocument, days_ago: int = 1
) -> CampaignMessageDocument:
    """A campaign message that reached `guest` in Telegram `days_ago`."""

    now = int(world.clock.now_microseconds())
    sent_at = Microseconds(now - days_ago * DAY)
    anchor = BookingId()
    message = CampaignMessageDocument(
        id=campaign_message_id_of(world.business.id, RebookingRuleKind.REBOOK, anchor),
        business_id=world.business.id,
        contact_id=guest.id,
        rule_kind=RebookingRuleKind.REBOOK,
        anchor_booking_id=anchor,
        status=CampaignMessageStatus.SENT,
        month=CampaignMonthKey("2026-10"),
        language=LanguageTag("en"),
        channel=ChannelKind.TELEGRAM,
        sent_at=sent_at,
        created_at=sent_at,
        updated_at=sent_at,
    )
    world.campaign_message_repo.insert_if_new(message)
    return message


def stop(world: CampaignWorld, guest: ContactDocument) -> None:
    """The guest said STOP in Telegram."""

    stored = world.contact_repo.get(world.business.id, guest.id)
    assert stored is not None
    stored.opted_out_channels = [ChannelKind.TELEGRAM]
    world.contact_repo.save(stored)


def reach(world: CampaignWorld, count: int, stops: int, days_ago: int = 1) -> None:
    for index in range(count):
        guest = world.guest(f"Guest {index}")
        write_to(world, guest, days_ago)
        if index < stops:
            stop(world, guest)


def build_gate(
    world: CampaignWorld,
) -> tuple[CampaignReviewGate, RecordingStaffNotifier, CountedSignals]:
    owner = UserDocument(
        id=UserId(),
        login_method=LoginMethod.EMAIL,
        email=EmailAddress("owner@trattoria.example"),
        locale=LanguageTag("it"),
        created_at=world.clock.now_microseconds(),
        updated_at=world.clock.now_microseconds(),
    )
    world.user_repo.save(owner)
    world.business.members = [
        BusinessMember(user_id=owner.id, role=BusinessMemberRole.OWNER)
    ]
    world.business_repo.save(world.business)
    notifier = RecordingStaffNotifier()
    signals = CountedSignals()
    gate = CampaignReviewGate(
        settings_repo=world.campaign_settings_repo,
        message_repo=world.campaign_message_repo,
        contact_repo=world.contact_repo,
        user_repo=world.user_repo,
        manager_notifier=notifier,
        text_resolver=world.resolver,
        signal_counter=signals,
    )
    return gate, notifier, signals


def settings_of(world: CampaignWorld) -> CampaignSettingsDocument:
    settings = world.campaign_settings_repo.get_by_business(world.business.id)
    assert settings is not None
    return settings


def test_a_campaign_past_the_opt_out_rate_is_held_and_its_owner_told() -> None:
    world = CampaignWorld()
    world.enable()
    reach(world, 40, stops=2)
    gate, notifier, signals = build_gate(world)
    now = world.clock.now_microseconds()

    assert gate.is_held(world.business, settings_of(world), now) is False

    reach(world, 1, stops=1)
    assert gate.is_held(world.business, settings_of(world), now) is True

    hold = settings_of(world).review_hold
    assert hold is not None
    assert (int(hold.sent), int(hold.opted_out), int(hold.held_at)) == (
        41,
        3,
        int(now),
    )
    [notice] = notifier.notifications
    assert str(notice.contact.address) == "owner@trattoria.example"
    assert "41" in str(notice.text) and "3" in str(notice.text)
    assert signals.of(PlatformSignal.CAMPAIGN_HOLD) == 1


def test_a_held_campaign_stays_held_without_measuring_again() -> None:
    world = CampaignWorld()
    world.enable()
    reach(world, 40, stops=3)
    gate, notifier, signals = build_gate(world)
    now = world.clock.now_microseconds()
    gate.is_held(world.business, settings_of(world), now)

    assert gate.is_held(world.business, settings_of(world), now) is True
    assert len(notifier.notifications) == 1
    assert signals.of(PlatformSignal.CAMPAIGN_HOLD) == 1


def test_few_messages_or_old_ones_never_hold_a_campaign() -> None:
    world = CampaignWorld()
    reach(world, 39, stops=10)
    reach(world, 30, stops=30, days_ago=31)

    rate = measure_opt_outs(
        world.campaign_message_repo,
        world.contact_repo,
        world.business.id,
        world.clock.now_microseconds(),
    )

    assert (int(rate.sent), int(rate.opted_out)) == (39, 10)
    assert rate.needs_review() is False


def test_a_consent_taken_back_after_the_message_counts() -> None:
    world = CampaignWorld()
    guest = world.guest("Anna")
    message = write_to(world, guest)

    def withdraw(stored: ContactDocument) -> None:
        assert stored.marketing_consent is not None
        stored.marketing_consent = stored.marketing_consent.model_copy(
            update={"withdrawn_at": world.clock.now_microseconds()}
        )

    world.contact_repo.change_card(world.business.id, guest.id, withdraw)

    rate = measure_opt_outs(
        world.campaign_message_repo,
        world.contact_repo,
        world.business.id,
        world.clock.now_microseconds(),
    )

    assert message.sent_at is not None
    assert (int(rate.sent), int(rate.opted_out)) == (1, 1)


def test_the_thresholds() -> None:
    def rate(sent: int, opted_out: int) -> bool:
        return CampaignOptOutRate(
            sent=CampaignMessageCount(sent), opted_out=CampaignMessageCount(opted_out)
        ).needs_review()

    assert rate(40, 2) is False  # fewer than 3 opt-outs
    assert rate(60, 3) is True  # 5 %
    assert rate(61, 3) is False  # under 5 %
    assert rate(39, 20) is False  # too few messages to mean anything


def test_the_job_writes_nothing_while_the_campaign_is_held() -> None:
    world = CampaignWorld()
    world.enable()
    nino = world.guest("Nino", "ru")
    world.visit(nino, VISIT_STARTS, VISIT_ENDS)
    reach(world, 40, stops=3)
    gate, _, _ = build_gate(world)

    report = world.run_campaigns(gate)

    assert int(report.processed_count) == 0
    assert world.messages_of(nino) == []
    assert settings_of(world).review_hold is not None


def test_a_campaign_under_the_rate_writes_as_usual() -> None:
    world = CampaignWorld()
    world.enable()
    nino = world.guest("Nino", "ru")
    world.visit(nino, VISIT_STARTS, VISIT_ENDS)
    reach(world, 40, stops=1)
    gate, notifier, _ = build_gate(world)

    report = world.run_campaigns(gate)

    assert int(report.processed_count) == 1
    assert notifier.notifications == []
