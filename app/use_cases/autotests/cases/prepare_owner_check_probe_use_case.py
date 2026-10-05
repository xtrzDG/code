from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import (
    LanguageRegistryContract,
    RequestRateLimitRegistryContract,
)
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.autotest_case_repositories import (
    AutotestCaseRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.autotest_cases import AutotestCaseDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants.autotest_cases import (
    OwnerCheckProbeCommand,
    OwnerCheckProbeStart,
)
from app.schemas.dto.assistants.autotest_runs import (
    AutotestScenario,
    AutotestScenarioRun,
)
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    RateLimitedError,
)
from app.schemas.typings.assistants.prefixed_id import AutotestRunId
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.assembly.fact_formatting import find_example_mobile_number
from app.utilities.assembly.language_profiles import (
    build_autotest_languages,
    collect_language_profiles,
)
from app.utilities.assembly.owner_check_scenarios import plan_owner_check_scenarios

# A "Check now" is a test conversation with the model the owner waits for:
# a few dozen an hour per business is plenty for teaching, and keeps a
# script from spending the business's model budget.
PROBES_PER_HOUR: RequestsPerWindow = RequestsPerWindow(30)
PROBE_WINDOW_SECONDS: RateWindowSeconds = RateWindowSeconds(3600)


class PrepareOwnerCheckProbeUseCase(
    UseCaseContract[OwnerCheckProbeCommand, OwnerCheckProbeStart]
):
    """
    "Check now" (owner only): the check's one scenario against the version
    customers talk to, as an apply's quick check would play it (its
    question word for word, in its language), even while the check is
    paused. Each business may ask PROBES_PER_HOUR checks an hour, counted
    for every API instance together.

    Raises:
        NotFoundError: no such check of this business.
        ConflictError: nothing is live yet, so there is nothing to ask.
        RateLimitedError: the business asked too many checks this hour
            (with Retry-After).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        autotest_case_repo: AutotestCaseRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        language_registry: LanguageRegistryContract,
        rate_limit_registry: RequestRateLimitRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._autotest_case_repo: AutotestCaseRepoContract = autotest_case_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._language_registry: LanguageRegistryContract = language_registry
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: OwnerCheckProbeCommand) -> OwnerCheckProbeStart:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        case: AutotestCaseDocument | None = self._autotest_case_repo.get(
            business.id, input_data.case_id
        )
        if case is None:
            raise NotFoundError(f"Check {input_data.case_id} was not found.")

        live: AssistantVersionDocument | None = (
            None
            if business.published_assistant_version_id is None
            else self._assistant_version_repo.get(
                business.id, business.published_assistant_version_id
            )
        )
        if live is None:
            raise ConflictError(
                "The assistant is not answering customers yet; launch it first."
            )

        self._count_probe(business)
        played = case.model_copy(update={"is_active": True})
        scenario: AutotestScenario = plan_owner_check_scenarios(
            [played],
            build_autotest_languages(
                [case.language],
                collect_language_profiles(self._language_registry, [case.language]),
            ),
        )[0]
        return OwnerCheckProbeStart(
            case=case,
            scenario_run=AutotestScenarioRun(
                # A run of its own: the probe's test conversation is new.
                run_id=AutotestRunId(),
                business=business,
                version=live,
                scenario=scenario,
                customer_phone_number=find_example_mobile_number(business.country_code),
            ),
            language=input_data.language or business.owner_language,
        )

    def _count_probe(self, business: BusinessDocument) -> None:
        now: Microseconds = self._wall_clock.now_unix()
        counter = RateLimitCounter(
            key=RateLimitKey(f"owner-check-probe:{business.id}"),
            limit=PROBES_PER_HOUR,
        )
        if (
            self._rate_limit_registry.try_acquire_all(
                [counter], PROBE_WINDOW_SECONDS, now
            )
            is None
        ):
            return

        raise RateLimitedError(
            "Too many checks were asked this hour; try again later.",
            retry_after_seconds=self._rate_limit_registry.seconds_until_free(
                counter, PROBE_WINDOW_SECONDS, now
            ),
        )
