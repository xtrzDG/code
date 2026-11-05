"""
The win-back messages to owners who cancelled, in English, Russian and
Georgian: what the assistant did since (it kept taking requests), that
everything they set up is kept, and a way back. The second message adds a
line for the reason they gave.
"""

from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    WinBackStage,
)
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.owner_texts import owner_text

WIN_BACK_TITLES: dict[WinBackStage, LocalizedText] = {
    WinBackStage.DAY_14: owner_text("billing.win_back.win_back_titles.day_14"),
    WinBackStage.DAY_30: owner_text("billing.win_back.win_back_titles.day_30"),
}
CONVERSATIONS_LINE: LocalizedText = owner_text("billing.win_back.conversations_line")
KEPT_LINE: LocalizedText = owner_text("billing.win_back.kept_line")
PAUSE_HINT: LocalizedText = owner_text("billing.win_back.pause_hint")
PRICE_HINT: LocalizedText = owner_text("billing.win_back.price_hint")
QUALITY_HINT: LocalizedText = owner_text("billing.win_back.quality_hint")
REASON_HINTS: dict[CancellationReason, LocalizedText] = {
    CancellationReason.SEASONAL_BREAK: PAUSE_HINT,
    CancellationReason.NOT_ENOUGH_USE: PAUSE_HINT,
    CancellationReason.TOO_EXPENSIVE: PRICE_HINT,
    CancellationReason.ANSWER_QUALITY: QUALITY_HINT,
    CancellationReason.MISSING_FEATURE: QUALITY_HINT,
}
