"""
Instagram comment-to-DM on the channels testbed: a business whose
Instagram account answers comments that name its keywords, Meta's webhook
handled by the real orchestrator, and a worker that also runs
`process_comment_trigger`.
"""

from typing import Any

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.gateways.worker.background_worker import BackgroundWorker
from app.orchestrators.channels.inbox.process_comment_trigger_orchestrator import (
    ProcessCommentTriggerOrchestrator,
)
from app.orchestrators.channels.meta_webhook_orchestrator import (
    MetaWebhookOrchestrator,
)
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.channels import ChannelDocument, InstagramCommentReplies
from app.schemas.dto.channels.channel_webhooks import (
    ChannelWebhookOutcome,
    ChannelWebhookPayload,
    MetaWebhookRequest,
)
from app.schemas.dto.release_gates import ReleaseGate
from app.schemas.typings.channels.strings import WebhookSignatureHeader
from app.schemas.typings.meta_connection.constrained_strings import (
    CommentReplyText,
    CommentTriggerKeyword,
)
from app.schemas.typings.platform.constrained_integers import WorkerPollSeconds
from app.use_cases.channels.comment_replies.accept_instagram_comments_use_case import (
    AcceptInstagramCommentsUseCase,
)
from app.use_cases.channels.comment_replies.reply_to_comment_trigger_use_case import (
    ReplyToCommentTriggerUseCase,
)
from app.utilities.deliveries.comment_trigger_jobs import PROCESS_COMMENT_TRIGGER_JOB
from app.utilities.storage import release_gates
from app.utilities.storage.release_gates import COMMENT_REPLIES_GATE
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.channels.channels_deliveries import as_job_operator
from tests.channels.channels_payloads import sign_meta, to_json_bytes
from tests.channels.testbed import ChannelsTestbed
from tests.platform.worker_fakes import TEST_LANE_CONCURRENCY

INSTAGRAM_ACCOUNT: str = "17841400000000001"
PAGE_TOKEN: str = "test-page-token-0000-0000"
REPLY: str = "Hi! Here is our menu: write here and we answer at once."


def opened_gates() -> tuple[ReleaseGate, ...]:
    """This release's gates with comment replies open (the next release)."""

    return tuple(
        gate.model_copy(update={"is_open": True})
        if gate.name == COMMENT_REPLIES_GATE
        else gate
        for gate in release_gates.RELEASE_GATES
    )


def comment(
    comment_id: str, text: str, author: str = "1789000000000001"
) -> dict[str, Any]:
    return {
        "field": "comments",
        "value": {
            "from": {"id": author, "username": "nino.k"},
            "media": {"id": "18000000000000001", "media_product_type": "FEED"},
            "id": comment_id,
            "text": text,
        },
    }


def comments_webhook(
    changes: list[dict[str, Any]], account: str = INSTAGRAM_ACCOUNT
) -> dict[str, Any]:
    return {
        "object": "instagram",
        "entry": [{"id": account, "time": 1790856000, "changes": changes}],
    }


class CommentWorld:
    def __init__(self) -> None:
        self.testbed = ChannelsTestbed()
        testbed = self.testbed
        owner = testbed.add_user("owner")
        self.business = testbed.add_business(owner)
        self.channel: ChannelDocument = testbed.add_channel(
            self.business.id,
            ChannelKind.INSTAGRAM,
            external_id=INSTAGRAM_ACCOUNT,
            secret=PAGE_TOKEN,
        )
        self.set_replies(is_on=True, keywords=["menu", "price list"])
        self.rate_limits = RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter())
        self.webhook = MetaWebhookOrchestrator(
            testbed.receive_meta_webhook,
            testbed.store_inbound_messages,
            AcceptInstagramCommentsUseCase(
                testbed.channel_repo,
                testbed.instagram_adapter,
                testbed.inbound_event_repo,
                testbed.job_queue,
                testbed.wall_clock,
            ),
        )
        self.reply = ReplyToCommentTriggerUseCase(
            testbed.channel_repo,
            testbed.outbound_message_repo,
            testbed.job_queue,
            self.rate_limits,
            testbed.wall_clock,
        )
        self.worker = BackgroundWorker(
            periodic_jobs=[],
            queued_job_operators={
                **testbed.job_operators(),
                PROCESS_COMMENT_TRIGGER_JOB: as_job_operator(
                    ProcessCommentTriggerOrchestrator(
                        testbed.claim_inbound_event,
                        self.reply,
                        testbed.finish_inbound_event,
                        testbed.release_inbound_event,
                    )
                ),
            },
            job_repo=testbed.jobs.job_repo,
            periodic_run_repo=testbed.jobs.periodic_run_repo,
            wall_clock=testbed.wall_clock,
            error_reporter=testbed.worker_errors,
            poll_seconds=WorkerPollSeconds(5),
            storage_scope=StorageScopeContext(),
            job_wakeup=testbed.jobs.job_wakeup,
            lane_concurrency=TEST_LANE_CONCURRENCY,
        )
        testbed.meta_transport.respond(
            "POST", r"/me/messages$", {"recipient_id": "1", "message_id": "mid.reply"}
        )

    def set_replies(
        self, is_on: bool, keywords: list[str], text: str | None = REPLY
    ) -> None:
        def change(stored: ChannelDocument) -> ChannelDocument:
            return stored.model_copy(
                update={
                    "comment_replies": InstagramCommentReplies(
                        is_on=is_on,
                        keywords=[CommentTriggerKeyword(word) for word in keywords],
                        reply_text=None if text is None else CommentReplyText(text),
                    )
                }
            )

        self.testbed.channel_repo.modify(self.business.id, self.channel.id, change)

    def post(
        self, payload: dict[str, Any], signature: str | None = None
    ) -> ChannelWebhookOutcome:
        body: bytes = to_json_bytes(payload)
        return self.webhook.execute(
            MetaWebhookRequest(
                payload=ChannelWebhookPayload(
                    body=body,
                    signature_header=WebhookSignatureHeader(
                        signature or sign_meta(body)
                    ),
                )
            )
        )

    def run_worker(self) -> None:
        for _ in range(20):
            if int(self.worker.run_once().queued_runs) == 0:
                return

    def private_replies(self) -> list[dict[str, Any]]:
        return [
            request.json()
            for request in self.testbed.meta_transport.requests_to("/me/messages")
        ]
