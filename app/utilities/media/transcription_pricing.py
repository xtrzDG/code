"""What OpenAI charges per second of transcribed audio, by model."""

from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.media.constrained_integers import AudioDurationSeconds
from app.schemas.typings.media.constrained_strings import TranscriptionModelId

# Micro-USD per second (list prices per minute / 60): gpt-4o-mini-transcribe
# $0.003/min, gpt-4o-transcribe and whisper-1 $0.006/min. Unknown models
# are counted at the higher price, so a margin is never overstated.
MICRO_USD_PER_SECOND_BY_PREFIX: tuple[tuple[str, int], ...] = (
    ("gpt-4o-mini-transcribe", 50),
    ("gpt-4o-transcribe", 100),
    ("whisper-1", 100),
)
DEFAULT_MICRO_USD_PER_SECOND: int = 100


def transcription_cost(
    model_id: TranscriptionModelId, seconds: AudioDurationSeconds
) -> CostMicroUsd:
    rate: int = next(
        (
            price
            for prefix, price in MICRO_USD_PER_SECOND_BY_PREFIX
            if str(model_id).startswith(prefix)
        ),
        DEFAULT_MICRO_USD_PER_SECOND,
    )
    return CostMicroUsd(rate * int(seconds))
