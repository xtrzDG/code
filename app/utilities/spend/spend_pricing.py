"""
What a window of usage cost, by provider.

Model tokens and transcriptions carry the cost the platform computed when
it recorded them. Voice minutes carry the voice platform's own figure only
after the call's report arrived, and WhatsApp templates and the minutes
after a transfer carry none; those are priced with the planned unit costs
below, and a kind that carries a cost is priced at the larger of the two,
so neither a late report nor a missing figure hides spend from the guard.
"""

from collections.abc import Iterable

from app.schemas.constants.billing import UsageKind
from app.schemas.constants.spend import SpendProvider
from app.schemas.dto.spend_guard import ProviderSpend, UsageKindTotal
from app.schemas.typings.billing.constrained_integers import CostMicroUsd

# Planned list prices in micro-USD per unit of the kind: ElevenLabs
# conversational minutes at about $0.09, a transferred call's telephony at
# about $0.02 a minute, a WhatsApp utility template at about $0.04 (Meta's
# list prices vary by country; this is the planning figure).
PLANNED_UNIT_COSTS_MICRO_USD: dict[UsageKind, int] = {
    UsageKind.VOICE_SECONDS: 1_500,
    UsageKind.TRANSFER_SECONDS: 333,
    UsageKind.WHATSAPP_TEMPLATE: 40_000,
}
PROVIDER_OF_KIND: dict[UsageKind, SpendProvider] = {
    UsageKind.LLM_INPUT_TOKENS: SpendProvider.LANGUAGE_MODEL,
    UsageKind.LLM_OUTPUT_TOKENS: SpendProvider.LANGUAGE_MODEL,
    UsageKind.VOICE_SECONDS: SpendProvider.VOICE,
    UsageKind.TRANSFER_SECONDS: SpendProvider.TELEPHONY,
    UsageKind.WHATSAPP_REPLY: SpendProvider.WHATSAPP,
    UsageKind.WHATSAPP_TEMPLATE: SpendProvider.WHATSAPP,
    UsageKind.TRANSCRIPTION_SECONDS: SpendProvider.TRANSCRIPTION,
}


def price_kind(total: UsageKindTotal) -> int:
    """The recorded cost, or the planned one when that is larger."""

    planned: int = PLANNED_UNIT_COSTS_MICRO_USD.get(total.kind, 0) * int(total.quantity)
    return max(int(total.cost_micro_usd), planned)


def price_usage(totals: Iterable[UsageKindTotal]) -> list[ProviderSpend]:
    """Spend per provider, in SpendProvider order, providers with none left out."""

    spend: dict[SpendProvider, int] = {}
    for total in totals:
        provider: SpendProvider | None = PROVIDER_OF_KIND.get(total.kind)
        if provider is None:
            continue

        spend[provider] = spend.get(provider, 0) + price_kind(total)

    return [
        ProviderSpend(provider=provider, spend_micro_usd=CostMicroUsd(spend[provider]))
        for provider in SpendProvider
        if spend.get(provider, 0) > 0
    ]


def total_spend(providers: Iterable[ProviderSpend]) -> CostMicroUsd:
    return CostMicroUsd(sum(int(item.spend_micro_usd) for item in providers))
