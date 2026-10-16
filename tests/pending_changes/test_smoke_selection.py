"""Which test conversations the quick check of "Apply changes" plays."""

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.setup import (
    PendingChangeAction,
    PendingChangeArea,
    PendingChangeDetail,
)
from app.schemas.dto.assistants.autotest_runs import AutotestLanguage
from app.schemas.dto.setup.pending_changes import PendingChange
from app.schemas.typings.localization.constrained_strings import LanguageTag, ScriptCode
from app.schemas.typings.localization.strings import LanguageDisplayName
from app.schemas.typings.setup.strings import PendingChangeSubject
from app.utilities.assembly.smoke_selection import (
    plan_smoke_scenarios,
    select_core_kinds,
    select_smoke_checks,
)

Kind = AutotestScenarioKind
RESTAURANT_KINDS: list[AutotestScenarioKind] = [
    Kind.BOOKING,
    Kind.BOOKING_OUT_OF_HOURS,
    Kind.CANCELLATION,
    Kind.PRICE_QUESTION,
    Kind.HUMAN_REQUEST,
    Kind.RUDE_CUSTOMER,
    Kind.PROMPT_INJECTION,
    Kind.UNKNOWN_QUESTION,
]
KA = LanguageTag("ka")
RU = LanguageTag("ru")


def change(
    area: PendingChangeArea,
    subject: str | None = None,
    action: PendingChangeAction = PendingChangeAction.CHANGED,
) -> PendingChange:
    return PendingChange(
        area=area,
        action=action,
        subject=None if subject is None else PendingChangeSubject(subject),
        detail=PendingChangeDetail.PRICE if area is PendingChangeArea.OFFER else None,
    )


def picked(
    changes: list[PendingChange], titles: tuple[str, ...] = ()
) -> list[tuple[str, str]]:
    selection = select_smoke_checks(changes, RESTAURANT_KINDS, [KA, RU], KA, titles)
    return [(pick.kind.value, str(pick.language)) for pick in selection.picks]


def test_three_core_kinds_the_version_can_play() -> None:
    assert select_core_kinds(RESTAURANT_KINDS) == [
        Kind.BOOKING,
        Kind.PRICE_QUESTION,
        Kind.HUMAN_REQUEST,
    ]
    assert select_core_kinds(
        [Kind.HUMAN_REQUEST, Kind.UNKNOWN_QUESTION, Kind.RUDE_CUSTOMER, Kind.EMERGENCY]
    ) == [
        Kind.HUMAN_REQUEST,
        Kind.UNKNOWN_QUESTION,
        Kind.RUDE_CUSTOMER,
    ]


def test_new_hours_add_the_scenarios_they_touch_in_the_default_language() -> None:
    assert picked([change(PendingChangeArea.HOURS)]) == [
        ("booking", "ka"),
        ("booking_out_of_hours", "ka"),
        ("price_question", "ka"),
        ("human_request", "ka"),
        ("rude_customer", "ka"),
    ]


def test_new_languages_play_the_core_kinds_in_every_language() -> None:
    assert picked([change(PendingChangeArea.LANGUAGES)]) == [
        ("booking", "ka"),
        ("price_question", "ka"),
        ("human_request", "ka"),
        ("booking", "ru"),
        ("price_question", "ru"),
        ("human_request", "ru"),
    ]


def test_changed_prices_get_their_own_questions_up_to_three() -> None:
    changes = [
        change(PendingChangeArea.OFFER, title)
        for title in ("Khachapuri", "Lobio", "Pkhali", "Mtsvadi")
    ] + [
        change(PendingChangeArea.OFFER, "Badrijani", PendingChangeAction.REMOVED),
        change(PendingChangeArea.OFFER, "Without a price"),
    ]
    titles = ("Khachapuri", "Lobio", "Pkhali", "Mtsvadi", "Badrijani")

    selection = select_smoke_checks(changes, RESTAURANT_KINDS, [KA], KA, titles)

    assert [str(title) for title in selection.price_item_titles] == [
        "Khachapuri",
        "Lobio",
        "Pkhali",
    ]
    assert str(selection.price_language) == "ka"


def test_the_plan_keys_scenarios_as_a_full_run_and_drops_what_cannot_be_played() -> (
    None
):
    selection = select_smoke_checks(
        [
            change(PendingChangeArea.OFFER, "Khachapuri"),
            change(PendingChangeArea.LANGUAGES),
        ],
        RESTAURANT_KINDS,
        [KA, RU],
        KA,
        ("Khachapuri",),
    )
    georgian = AutotestLanguage(
        tag=KA, name=LanguageDisplayName("Georgian"), script=ScriptCode("Geor")
    )

    scenarios = plan_smoke_scenarios(
        selection,
        [georgian],
        [Kind.BOOKING, Kind.PRICE_QUESTION],
        resource_noun="table",
        party_size=2,
    )

    assert [str(scenario.key) for scenario in scenarios] == [
        "booking__ka",
        "price_question__ka",
        "price_question__ka__1",
    ]
    assert "Khachapuri" in str(scenarios[-1].goal)
