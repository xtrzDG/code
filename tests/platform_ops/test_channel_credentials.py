"""
The hourly Meta token check: which channels it asks about (active Meta
channels not asked within 20 hours), what it stores, and what it leaves
for the next hour.
"""

from collections.abc import Callable

from typed_time_provider import Microseconds

from app.contracts.channel_clients import ProviderToken
from app.contracts.channel_credentials import MetaTokenDebugClientContract
from app.repositories.business_repositories import ChannelRepository
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels.credential_inspection import MetaTokenFacts
from app.schemas.dto.jobs import JobTick
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelSecret, EncryptedChannelSecret
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from app.use_cases.admin.system.check_channel_credentials_use_case import (
    INSPECTIONS_PER_RUN,
    CheckChannelCredentialsUseCase,
)
from tests.channels.channels_fakes import FakeSecretCipher
from tests.platform_ops.ops_documents import DAY, HOUR, at, channel
from tests.platform_ops.ops_world import OpsWorld, put

APP_ID: PlatformIdentifier = PlatformIdentifier("1234567890")
APP_SECRET: PlatformSecret = PlatformSecret("test-app-secret-0000")  # gitleaks:allow
CIPHER = FakeSecretCipher()
TICK = JobTick(job_name=JobName("check_channel_credentials"), scheduled_at=at(0))


class FakeTokenClient(MetaTokenDebugClientContract):
    """Meta's answers by token; a token without one fails like an outage."""

    def __init__(self, answers: dict[str, MetaTokenFacts]) -> None:
        self.answers: dict[str, MetaTokenFacts] = answers
        self.asked: list[str] = []
        self.before_answer: Callable[[str], None] | None = None

    def inspect_token(
        self,
        token: ProviderToken,
        app_id: PlatformIdentifier,
        app_secret: PlatformSecret,
    ) -> MetaTokenFacts:
        assert (app_id, app_secret) == (APP_ID, APP_SECRET)
        self.asked.append(str(token))
        if self.before_answer is not None:
            self.before_answer(str(token))
        if str(token) not in self.answers:
            raise ExternalServiceError("Meta Graph API request failed: ConnectError.")
        return self.answers[str(token)]


def sealed(token: str) -> EncryptedChannelSecret:
    return CIPHER.encrypt(ChannelSecret(token))


def meta_channel(
    token: str,
    kind: ChannelKind = ChannelKind.WHATSAPP,
    status: ChannelStatus = ChannelStatus.CONNECTED,
    checked_at: Microseconds | None = None,
) -> ChannelDocument:
    return channel(BusinessId(), status=status, kind=kind).model_copy(
        update={"encrypted_secret": sealed(token), "credential_checked_at": checked_at}
    )


def check(
    world: OpsWorld,
    client: FakeTokenClient,
    app_id: PlatformIdentifier | None = APP_ID,
) -> int:
    report = CheckChannelCredentialsUseCase(
        system_health_repo=world.health_repo,
        channel_repo=ChannelRepository(world.channels),
        secret_cipher=CIPHER,
        token_client=client,
        meta_app_id=app_id,
        meta_app_secret=APP_SECRET,
        wall_clock=world.clock.wall_clock,
    ).run(TICK)
    return int(report.processed_count)


def stored(world: OpsWorld, document: ChannelDocument) -> ChannelDocument:
    found = world.channels.get(str(document.id))
    assert found is not None
    return found


def test_active_meta_tokens_get_their_end_and_the_time_they_were_asked() -> None:
    world = OpsWorld()
    expiring = meta_channel("token-a")
    never = meta_channel("token-b", ChannelKind.INSTAGRAM, ChannelStatus.ERROR)
    asked_lately = meta_channel("token-c", checked_at=at(-2 * HOUR))
    asked_yesterday = meta_channel(
        "token-d", ChannelKind.MESSENGER, checked_at=at(-21 * HOUR)
    )
    pending = meta_channel("token-e", status=ChannelStatus.PENDING)
    telegram = meta_channel("token-f", ChannelKind.TELEGRAM)
    unsealed = channel(BusinessId())
    put(
        world.channels,
        expiring,
        never,
        asked_lately,
        asked_yesterday,
        pending,
        telegram,
        unsealed,
    )
    client = FakeTokenClient(
        {
            "token-a": MetaTokenFacts(is_valid=True, expires_at=at(9 * DAY)),
            "token-b": MetaTokenFacts(is_valid=True),
            "token-d": MetaTokenFacts(is_valid=True, expires_at=at(60 * DAY)),
        }
    )

    assert check(world, client) == 3

    assert sorted(client.asked) == ["token-a", "token-b", "token-d"]
    assert stored(world, expiring).credential_expires_at == at(9 * DAY)
    assert stored(world, expiring).credential_checked_at == at(0)
    assert stored(world, never).credential_expires_at is None
    assert stored(world, never).credential_checked_at == at(0)
    assert stored(world, asked_yesterday).credential_expires_at == at(60 * DAY)
    assert stored(world, asked_lately).credential_checked_at == at(-2 * HOUR)
    assert stored(world, pending).credential_checked_at is None
    assert stored(world, telegram).credential_checked_at is None


def test_a_token_meta_no_longer_accepts_reads_as_run_out() -> None:
    world = OpsWorld()
    revoked = meta_channel("token-a")
    lapsed = meta_channel("token-b")
    put(world.channels, revoked, lapsed)
    client = FakeTokenClient(
        {
            "token-a": MetaTokenFacts(is_valid=False, expires_at=at(5 * DAY)),
            "token-b": MetaTokenFacts(is_valid=False, expires_at=at(-DAY)),
        }
    )

    assert check(world, client) == 2

    assert stored(world, revoked).credential_expires_at == at(0)
    assert stored(world, lapsed).credential_expires_at == at(-DAY)


def test_without_the_meta_app_nobody_is_asked() -> None:
    world = OpsWorld()
    put(world.channels, meta_channel("token-a"))
    client = FakeTokenClient({})

    assert check(world, client, app_id=None) == 0
    assert client.asked == []


def test_a_token_that_cannot_be_checked_now_waits_for_the_next_hour() -> None:
    world = OpsWorld()
    outage = meta_channel("token-a")
    unreadable = channel(BusinessId()).model_copy(
        update={"encrypted_secret": EncryptedChannelSecret("not-sealed-0000")}
    )
    put(world.channels, outage, unreadable)
    client = FakeTokenClient({})

    assert check(world, client) == 0

    assert client.asked == ["token-a"]
    assert stored(world, outage).credential_checked_at is None
    assert stored(world, unreadable).credential_checked_at is None


def test_a_channel_reconnected_meanwhile_keeps_its_new_token() -> None:
    world = OpsWorld()
    reconnected = meta_channel("token-a")
    put(world.channels, reconnected)
    client = FakeTokenClient({"token-a": MetaTokenFacts(is_valid=False)})

    def reconnect(_: str) -> None:
        put(
            world.channels,
            reconnected.model_copy(update={"encrypted_secret": sealed("token-new")}),
        )

    client.before_answer = reconnect

    assert check(world, client) == 0

    assert stored(world, reconnected).encrypted_secret == sealed("token-new")
    assert stored(world, reconnected).credential_expires_at is None


def test_one_run_asks_about_a_bounded_number_of_tokens() -> None:
    world = OpsWorld()
    tokens = [f"token-{index:04d}" for index in range(INSPECTIONS_PER_RUN + 5)]
    put(world.channels, *(meta_channel(token) for token in tokens))
    client = FakeTokenClient({token: MetaTokenFacts(is_valid=True) for token in tokens})

    assert check(world, client) == INSPECTIONS_PER_RUN
    world.clock.advance(HOUR)
    assert check(world, client) == 5
    assert sorted(client.asked) == tokens
