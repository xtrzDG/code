"""Script detection of replies and the LLM cost estimate from list prices."""

import pytest

from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.typings.assistants.constrained_integers import (
    LlmPricePerMillionTokensMicroUsd,
)
from app.schemas.typings.assistants.constrained_strings import (
    LlmModelId,
)
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.localization.constrained_strings import (
    ScriptCode,
)
from app.utilities.assembly.llm_costs import (
    DEFAULT_LLM_TOKEN_PRICES,
    estimate_llm_cost,
)
from app.utilities.assembly.script_detection import (
    is_detectable_script,
    is_written_in_script,
)


@pytest.mark.parametrize(
    ("text", "script", "expected"),
    [
        ("გამარჯობა! მე ვარ Café Rustaveli-ს AI ასისტენტი.", "Geor", True),
        ("Hello! I am the AI assistant of Café Rustaveli.", "Geor", False),
        ("שלום! אני עוזר AI של המרפאה.", "Hebr", True),
        ("مرحبا! أنا المساعد الذكي.", "Arab", True),
        ("こんにちは！AIアシスタントです。にぎりは1500円です。", "Jpan", True),
        ("Здравствуйте! Я AI-ассистент.", "Cyrl", True),
        ("Buongiorno! Sono l'assistente AI.", "Latn", True),
        ("Здравствуйте!", "Latn", False),
        ("18.00 GEL, +995 32 212 34 56", "Geor", None),
        ("Your VR arena booking is confirmed", "Geor", False),
        ("ჯავშანი VR არენაზე დადასტურებულია, 50 GEL.", "Geor", True),
        ("Hello", "Zzzz", None),
        ("Hello", None, None),
    ],
)
def test_script_detection(text: str, script: str | None, expected: bool | None) -> None:
    script_code = ScriptCode(script) if script is not None else None

    assert is_written_in_script(text, script_code) is expected


def test_detectable_scripts() -> None:
    assert is_detectable_script(ScriptCode("Geor"))
    assert is_detectable_script(ScriptCode("Hant"))
    assert not is_detectable_script(ScriptCode("Tfng"))
    assert not is_detectable_script(None)


def test_llm_cost_estimate_uses_list_prices() -> None:
    prices = [
        LlmTokenPrice(
            model_id=LlmModelId("judge-model"),
            input_price=LlmPricePerMillionTokensMicroUsd(1_000_000),
            output_price=LlmPricePerMillionTokensMicroUsd(3_000_000),
        )
    ]

    assert (
        estimate_llm_cost(
            DEFAULT_LLM_TOKEN_PRICES,
            LlmModelId("gpt-5-mini"),
            LlmTokenCount(1000),
            LlmTokenCount(500),
        )
        == 1250
    )
    assert (
        estimate_llm_cost(
            prices,
            LlmModelId("judge-model"),
            LlmTokenCount(1),
            LlmTokenCount(1),
        )
        == 4
    )
    assert (
        estimate_llm_cost(
            prices,
            LlmModelId("judge-model"),
            LlmTokenCount(0),
            LlmTokenCount(0),
        )
        == 0
    )
    assert (
        estimate_llm_cost(
            prices,
            LlmModelId("unknown-model"),
            LlmTokenCount(10_000),
            LlmTokenCount(10_000),
        )
        == 0
    )
