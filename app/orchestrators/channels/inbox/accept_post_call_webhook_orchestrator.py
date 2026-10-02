from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.dto.deliveries import VerifiedPostCallReport
from app.schemas.dto.voice_webhooks import (
    FinishedCallReport,
    PostCallWebhookOutcome,
    PostCallWebhookRequest,
)


class AcceptPostCallWebhookOrchestrator(
    OrchestratorContract[PostCallWebhookRequest, PostCallWebhookOutcome]
):
    """
    Post-call webhook of the voice platform, acknowledged at once: check
    its signature (at most 30 minutes old) and read the finished call, then
    keep the report in the inbox for the worker. Events that are not a
    finished call are ignored.
    """

    def __init__(
        self,
        authenticate_post_call: UseCaseContract[
            PostCallWebhookRequest, FinishedCallReport | None
        ],
        store_post_call_report: UseCaseContract[
            VerifiedPostCallReport, PostCallWebhookOutcome
        ],
    ) -> None:
        self._authenticate_post_call: UseCaseContract[
            PostCallWebhookRequest, FinishedCallReport | None
        ] = authenticate_post_call
        self._store_post_call_report: UseCaseContract[
            VerifiedPostCallReport, PostCallWebhookOutcome
        ] = store_post_call_report

    def execute(self, input_data: PostCallWebhookRequest) -> PostCallWebhookOutcome:
        report: FinishedCallReport | None = self._authenticate_post_call.run(input_data)
        if report is None:
            return PostCallWebhookOutcome(status=PostCallEventStatus.IGNORED)

        return self._store_post_call_report.run(
            VerifiedPostCallReport(body=input_data.body, report=report)
        )
