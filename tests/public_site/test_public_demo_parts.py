"""
The parts of the landing page's demos one by one: the message limits, the
demo places of one process and the list that leaves out demos which
cannot answer.
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager

import pytest
from typed_time_provider import Microseconds

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.orchestrators.demo.list_public_demos_orchestrator import (
    ListPublicDemosOrchestrator,
)
from app.pipelines.demo.public_demo_message_pipeline import PublicDemoMessagePipeline
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.registries.public_site.public_demo_slots import (
    build_public_demo_slots,
    refuse_busy_public_demo,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.dto.public_demo import (
    PublicDemoBusinessIds,
    PublicDemoCard,
    PublicDemoCardQuery,
    PublicDemoListQuery,
    PublicDemoMessageCommand,
    PublicDemoMessageRequest,
    PublicDemoReply,
    PublicDemoTurnOutcome,
)
from app.schemas.exceptions.application_errors import NotFoundError, RateLimitedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.schemas.typings.public_site.constrained_integers import (
    PublicDemoMessagesLeft,
    PublicDemoMessagesPerHour,
)
from app.schemas.typings.public_site.constrained_strings import (
    PublicDemoMessageText,
    PublicDemoSessionKey,
)
from app.utilities.public_site.public_demo_limits import (
    refuse_too_many_demo_messages,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext

DEMO: BusinessId = BusinessId("business_0f8f6bd6-e9b2-4a4c-8b8c-3c1f2a7e9d10")
GONE: BusinessId = BusinessId("business_6a0c1f2e-3b4d-4e5f-8a6b-7c8d9e0f1a2b")
NOW: Microseconds = Microseconds(1_790_000_000_000_000)


def key(raw: str) -> PublicDemoSessionKey:
    return PublicDemoSessionKey(raw)


class TestDemoMessageLimits:
    def setup_method(self) -> None:
        self.registry = RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter())

    def send(
        self, session: str, address: str | None = "203.0.113.7", site_budget: int = 300
    ) -> None:
        refuse_too_many_demo_messages(
            self.registry,
            DEMO,
            key(session),
            None if address is None else ClientIpAddress(address),
            PublicDemoMessagesPerHour(site_budget),
            NOW,
        )

    def test_one_network_shares_a_budget_across_conversations(self) -> None:
        for index in range(60):
            self.send(f"visitor-session-{index:04d}")

        with pytest.raises(RateLimitedError) as refused:
            self.send("visitor-session-9999")

        assert refused.value.retry_after_seconds is not None
        # Another network is not affected.
        self.send("visitor-session-9999", address="198.51.100.4")

    def test_the_site_budget_bounds_every_visitor_together(self) -> None:
        self.send("visitor-session-0001", address=None, site_budget=2)
        self.send("visitor-session-0002", address=None, site_budget=2)

        with pytest.raises(RateLimitedError):
            self.send("visitor-session-0003", address=None, site_budget=2)

    def test_a_refused_message_counts_for_no_limit(self) -> None:
        for _ in range(20):
            self.send("visitor-session-0001")
        with pytest.raises(RateLimitedError):
            self.send("visitor-session-0001")

        # The refusal took no place of the network's budget: 39 more fit.
        for index in range(40):
            self.send(f"visitor-session-{index + 100:04d}")
        with pytest.raises(RateLimitedError):
            self.send("visitor-session-0999")


class BusySlots:
    @contextmanager
    def hold(self) -> Generator[None]:
        raise refuse_busy_public_demo()
        yield  # pragma: no cover


class Recorder[In, Out]:
    def __init__(self, answer: Out) -> None:
        self.answer: Out = answer
        self.calls: list[In] = []

    def execute(self, input_data: In) -> Out:
        self.calls.append(input_data)
        return self.answer


def test_busy_demo_places_ask_the_visitor_to_try_again() -> None:
    message = InboundMessage(
        business_id=DEMO,
        channel=ChannelKind.OWNER_TEST,
        channel_user_id=ChannelUserId("public-demo:visitor-session-0001"),
        text=MessageText("Hello"),
        is_sandbox=True,
    )
    admit = Recorder[PublicDemoMessageCommand, InboundMessage](message)
    turn = Recorder[InboundMessage, AssistantReply](
        AssistantReply.model_construct()  # never reached
    )
    summarize = Recorder[PublicDemoTurnOutcome, PublicDemoReply](
        PublicDemoReply(
            text=None,
            language=LanguageTag("en"),
            messages_left=PublicDemoMessagesLeft(0),
        )
    )
    pipeline = PublicDemoMessagePipeline(
        admit_message=admit,
        turn_orchestrator=turn,
        summarize_reply=summarize,
        public_demo_slots=BusySlots(),
    )

    with pytest.raises(RateLimitedError) as refused:
        pipeline.start(
            PublicDemoMessageCommand(
                business_id=DEMO,
                request=PublicDemoMessageRequest(
                    text=PublicDemoMessageText("Hello"),
                    session_key=key("visitor-session-0001"),
                ),
            )
        )

    assert refused.value.retry_after_seconds == 5
    assert len(admit.calls) == 1
    assert turn.calls == [] and summarize.calls == []
    assert build_public_demo_slots() is not build_public_demo_slots()


class ListedDemos:
    def run(self, input_data: PublicDemoListQuery) -> PublicDemoBusinessIds:
        del input_data
        return PublicDemoBusinessIds(business_ids=[GONE, DEMO])


class DescribedDemos:
    def __init__(self, scope: StorageScopeContext) -> None:
        self.scope: StorageScopeContext = scope
        self.scopes: list[BusinessId | None] = []

    def run(self, input_data: PublicDemoCardQuery) -> PublicDemoCard:
        self.scopes.append(self.scope.current().business_id)
        if input_data.business_id == GONE:
            raise NotFoundError("This demo is not available.")

        return PublicDemoCard(
            business_id=input_data.business_id,
            business_name=BusinessName("Mtsvane Ezo"),
            niche_key=NicheKey.RESTAURANT,
            niche_name=LocalizedTextValue("Restaurants and cafes"),
            country_code=CountryCode("GE"),
            default_language=LanguageTag("ka"),
            languages=[LanguageTag("ka"), LanguageTag("en")],
        )


def test_the_list_describes_each_demo_in_its_scope_and_skips_gone_ones(
    caplog: pytest.LogCaptureFixture,
) -> None:
    scope = StorageScopeContext()
    describe = DescribedDemos(scope)
    orchestrator = ListPublicDemosOrchestrator(
        list_demo_businesses=ListedDemos(),
        describe_public_demo=describe,
        storage_scope=scope,
    )

    with caplog.at_level(logging.WARNING):
        listed = orchestrator.execute(PublicDemoListQuery(language=LanguageTag("en")))

    assert [demo.business_id for demo in listed.demos] == [DEMO]
    assert listed.messages_per_hour == 20
    assert describe.scopes == [GONE, DEMO]
    assert str(GONE) in caplog.text
