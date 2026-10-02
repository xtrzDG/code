from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.billing_use_cases import BillingUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin import (
    AdminClientPage,
    AdminClientQuery,
    AdminClientsQuery,
    AdminClientSummary,
    ClientCabinetAccess,
    ClientHealthView,
    ClientSummarySource,
    OpenClientCabinetCommand,
)
from app.schemas.dto.admin_jobs import (
    AdminJobActionResult,
    AdminJobCommand,
    AdminJobsQuery,
    QueuedJobPage,
)
from app.schemas.dto.jobs import (
    JobReport,
    JobTick,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.authorize_platform_admin_use_case import (
    AuthorizePlatformAdminUseCase,
)
from app.use_cases.admin.get_client_health_use_case import GetClientHealthUseCase
from app.use_cases.admin.jobs.discard_queued_job_use_case import (
    DiscardQueuedJobUseCase,
)
from app.use_cases.admin.jobs.list_queued_jobs_use_case import ListQueuedJobsUseCase
from app.use_cases.admin.jobs.retry_queued_job_use_case import RetryQueuedJobUseCase
from app.use_cases.admin.list_clients_use_case import ListClientsUseCase
from app.use_cases.admin.open_client_cabinet_use_case import OpenClientCabinetUseCase
from app.use_cases.admin.summarize_client_use_case import SummarizeClientUseCase
from app.use_cases.jobs.purge_finished_jobs_use_case import PurgeFinishedJobsUseCase
from app.use_cases.maintenance.purge_stale_rows_use_case import PurgeStaleRowsUseCase
from app.use_cases.observability.flush_llm_traces_use_case import FlushLlmTracesUseCase


class PlatformUseCasesContainer(containers.DeclarativeContainer):
    """
    The platform's own work: the platform admin's client views and job
    queue, flushing LLM traces to the quality journal and purging finished
    jobs.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    billing_use_cases: BillingUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Platform admin.
    authorize_platform_admin_use_case: Factory[
        UseCaseContract[UserId, UserDocument]
    ] = Factory(
        AuthorizePlatformAdminUseCase,
        user_repo=repositories.user_repo,
    )
    summarize_client_use_case: Factory[
        UseCaseContract[ClientSummarySource, AdminClientSummary]
    ] = Factory(
        SummarizeClientUseCase,
        subscription_repo=repositories.subscription_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        handoff_repo=repositories.handoff_repo,
        unanswered_question_repo=repositories.unanswered_question_repo,
        message_repo=repositories.message_repo,
        usage_event_repo=repositories.usage_event_repo,
        plan_registry=registries.plan_registry,
        compute_client_cost=billing_use_cases.compute_client_cost_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_clients_use_case: Factory[
        UseCaseContract[AdminClientsQuery, AdminClientPage]
    ] = Factory(
        ListClientsUseCase,
        authorize_platform_admin=authorize_platform_admin_use_case,
        business_repo=repositories.business_repo,
        summarize_client=summarize_client_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_client_health_use_case: Factory[
        UseCaseContract[AdminClientQuery, ClientHealthView]
    ] = Factory(
        GetClientHealthUseCase,
        authorize_platform_admin=authorize_platform_admin_use_case,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        invoice_repo=repositories.invoice_repo,
        payment_order_repo=repositories.payment_order_repo,
        summarize_client=summarize_client_use_case,
    )
    open_client_cabinet_use_case: Factory[
        UseCaseContract[OpenClientCabinetCommand, ClientCabinetAccess]
    ] = Factory(
        OpenClientCabinetUseCase,
        authorize_platform_admin=authorize_platform_admin_use_case,
        business_repo=repositories.business_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    # --- Observability.
    flush_llm_traces_use_case: Factory[UseCaseContract[JobTick, JobReport]] = Factory(
        FlushLlmTracesUseCase,
        trace_facilitator=adapters.llm_trace_facilitator,
    )

    # --- Storage retention.
    purge_stale_rows_use_case: Factory[UseCaseContract[JobTick, JobReport]] = Factory(
        PurgeStaleRowsUseCase,
        user_session_repo=repositories.user_session_repo,
        otp_challenge_repo=repositories.otp_challenge_repo,
        channel_message_receipt_repo=repositories.channel_message_receipt_repo,
        inbound_event_repo=repositories.inbound_event_repo,
        outbound_message_repo=repositories.outbound_message_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # --- The job queue: the admin's dead letters and the purge job.
    list_queued_jobs_use_case: Factory[
        UseCaseContract[AdminJobsQuery, QueuedJobPage]
    ] = Factory(
        ListQueuedJobsUseCase,
        authorize_platform_admin=authorize_platform_admin_use_case,
        job_repo=repositories.queued_job_repo,
    )
    retry_queued_job_use_case: Factory[
        UseCaseContract[AdminJobCommand, AdminJobActionResult]
    ] = Factory(
        RetryQueuedJobUseCase,
        authorize_platform_admin=authorize_platform_admin_use_case,
        job_repo=repositories.queued_job_repo,
        audit_log_repo=repositories.audit_log_repo,
        job_wakeup=utilities.job_wakeup,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    discard_queued_job_use_case: Factory[
        UseCaseContract[AdminJobCommand, AdminJobActionResult]
    ] = Factory(
        DiscardQueuedJobUseCase,
        authorize_platform_admin=authorize_platform_admin_use_case,
        job_repo=repositories.queued_job_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    purge_finished_jobs_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            PurgeFinishedJobsUseCase,
            job_repo=repositories.queued_job_repo,
            periodic_run_repo=repositories.periodic_job_run_repo,
        )
    )
