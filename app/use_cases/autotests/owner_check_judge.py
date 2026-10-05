"""Deciding one owner check: the rules, then the semantic judge for words."""

from collections.abc import Callable, Sequence

from app.contracts.llm import LlmAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import AutotestCheckCode, AutotestExpectation
from app.schemas.dto.assistants.autotest_runs import (
    AutotestCheckFailure,
    OwnerCheckDecision,
    OwnerCheckSpec,
)
from app.schemas.dto.conversations import AssistantReply, LlmRequest, LlmResponse
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.strings import JudgeNote, SystemPromptText
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.assembly.autotest_evaluation import check_failure, read_model_text
from app.utilities.assembly.owner_check_evaluation import check_owner_expectation
from app.utilities.assembly.owner_check_judging import (
    OWNER_CHECK_JUDGE_PROMPT,
    TEXT_EXPECTATIONS,
    build_owner_check_judge_text,
    can_judge_meaning,
    parse_owner_check_verdict,
)


class OwnerCheckJudge:
    """
    Decides an owner check by its expectation (`check_owner_expectation`).
    A check that must (not) mention something is then read for meaning by
    the judge model (LLM_JUDGE_MODEL_ID) when that is a real provider's: an
    answer that says the same in other words passes MUST_MENTION, and one
    that says the forbidden thing in other words fails MUST_NOT_MENTION.
    The rules alone decide when the words already did (a literal mention
    passes MUST_MENTION and fails MUST_NOT_MENTION), on the scripted
    rehearsal model, and when the judge cannot be asked or read (no key, a
    provider error): its note is kept in `judge_notes`.
    """

    def __init__(
        self,
        judge_llm_adapter: LlmAdapterContract,
        app_settings: AppSettings,
        estimate_cost: Callable[[LlmResponse], CostMicroUsd],
    ) -> None:
        self._judge: LlmAdapterContract = judge_llm_adapter
        self._settings: AppSettings = app_settings
        self._estimate_cost: Callable[[LlmResponse], CostMicroUsd] = estimate_cost

    def decide(
        self,
        check: OwnerCheckSpec,
        replies: Sequence[AssistantReply],
        notes_language: LanguageTag,
    ) -> OwnerCheckDecision:
        failures: list[AutotestCheckFailure] = check_owner_expectation(check, replies)
        answers: list[str] = [
            text for text in (read_model_text(reply) for reply in replies) if text
        ]
        must_mention: bool = check.expectation is AutotestExpectation.MUST_MENTION
        is_decided_by_words: bool = bool(failures) != must_mention
        if (
            check.expectation not in TEXT_EXPECTATIONS
            or is_decided_by_words
            or not answers
            or not can_judge_meaning(self._settings.llm_judge_model_id)
        ):
            return OwnerCheckDecision(failures=failures)

        try:
            response: LlmResponse = self._judge.complete(
                self._build_request(check, answers, notes_language)
            )
        except ApplicationError:
            return OwnerCheckDecision(failures=failures)

        cost: CostMicroUsd = self._estimate_cost(response)
        verdict: tuple[bool, JudgeNote | None] | None = parse_owner_check_verdict(
            None if response.text is None else str(response.text)
        )
        if verdict is None:
            return OwnerCheckDecision(failures=failures, cost=cost)

        conveys, note = verdict
        notes: list[JudgeNote] = [] if note is None else [note]
        if must_mention:
            return OwnerCheckDecision(
                failures=[] if conveys else failures, notes=notes, cost=cost
            )

        return OwnerCheckDecision(
            failures=(
                [
                    check_failure(
                        AutotestCheckCode.FORBIDDEN_TEXT_MENTIONED,
                        f'An answer conveyed "{check.expected_text}", which it '
                        "must not.",
                    )
                ]
                if conveys
                else []
            ),
            notes=notes,
            cost=cost,
        )

    def _build_request(
        self,
        check: OwnerCheckSpec,
        answers: Sequence[str],
        notes_language: LanguageTag,
    ) -> LlmRequest:
        return LlmRequest(
            model_id=self._settings.llm_judge_model_id,
            system_prompt=SystemPromptText(OWNER_CHECK_JUDGE_PROMPT),
            tools=[],
            transcript=[
                self._judge.build_user_text_turn(
                    MessageText(
                        build_owner_check_judge_text(check, answers, notes_language)
                    )
                )
            ],
            max_output_tokens=self._settings.llm_max_output_tokens,
            effort=self._settings.llm_judge_effort,
        )
