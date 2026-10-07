from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.dto.calls.missed_calls import MissedCallReport, RegisteredMissedCall
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
    keep the report in the inbox for the worker. A call the platform could
    not start is a caller who did not get through: it is stored with its
    text-back and staff are told at once. Other events are ignored.
    """

    def __init__(
        self,
        authenticate_post_call: UseCaseContract[
            PostCallWebhookRequest, FinishedCallReport | None
        ],
        store_post_call_report: UseCaseContract[
            VerifiedPostCallReport, PostCallWebhookOutcome
        ],
        read_failed_call_start: UseCaseContract[
            PostCallWebhookRequest, MissedCallReport | None
        ],
        handle_missed_call: OrchestratorContract[
            MissedCallReport, RegisteredMissedCall | None
        ],
    ) -> None:
        self._authenticate_post_call: UseCaseContract[
            PostCallWebhookRequest, FinishedCallReport | None
        ] = authenticate_post_call
        self._store_post_call_report: UseCaseContract[
            VerifiedPostCallReport, PostCallWebhookOutcome
        ] = store_post_call_report
        self._read_failed_call_start: UseCaseContract[
            PostCallWebhookRequest, MissedCallReport | None
        ] = read_failed_call_start
        self._handle_missed_call: OrchestratorContract[
            MissedCallReport, RegisteredMissedCall | None
        ] = handle_missed_call

    def execute(self, input_data: PostCallWebhookRequest) -> PostCallWebhookOutcome:
        report: FinishedCallReport | None = self._authenticate_post_call.run(input_data)
        if report is None:
            return self._accept_failed_start(input_data)

        return self._store_post_call_report.run(
            VerifiedPostCallReport(body=input_data.body, report=report)
        )

    def _accept_failed_start(
        self, input_data: PostCallWebhookRequest
    ) -> PostCallWebhookOutcome:
        failure: MissedCallReport | None = self._read_failed_call_start.run(input_data)
        registered: RegisteredMissedCall | None = (
            None if failure is None else self._handle_missed_call.execute(failure)
        )
        if registered is None:
            return PostCallWebhookOutcome(status=PostCallEventStatus.IGNORED)

        return PostCallWebhookOutcome(
            status=(
                PostCallEventStatus.RECORDED
                if registered.is_new
                else PostCallEventStatus.DUPLICATE
            )
        )
