from app.contracts.transformer_contract import TransformerContract
from app.schemas.domain.conversations import CallDocument
from app.schemas.dto.conversation_feed.conversation_views import (
    CallSummaryView,
    CallView,
)


class CallViewTransformer(TransformerContract[CallDocument, CallView]):
    """A phone call on the conversation card (concept section 8)."""

    def transform(self, input_data: CallDocument) -> CallView:
        return CallView(
            id=input_data.id,
            from_phone_number=input_data.from_phone_number,
            to_phone_number=input_data.to_phone_number,
            started_at=input_data.started_at,
            duration_seconds=input_data.duration_seconds,
            outcome=input_data.outcome,
            transcript=input_data.transcript,
            recording_path=input_data.recording_path,
            guard_verdict=input_data.guard_verdict,
            unverified_values=list(input_data.unverified_values),
            summaries=[
                CallSummaryView(language=summary.language, text=summary.text)
                for summary in input_data.summaries
            ],
        )
