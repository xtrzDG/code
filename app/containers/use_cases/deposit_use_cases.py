from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.deposits.deposit_report import DepositReport, DepositReportQuery
from app.schemas.dto.deposits.deposit_settings import (
    AddPaymentLinkCommand,
    DepositSettingsQuery,
    DepositSettingsView,
    RemovePaymentLinkCommand,
    SetDepositPolicyCommand,
    UpdateDepositSettingsCommand,
)
from app.schemas.dto.deposits.deposit_views import (
    DepositRequestQuery,
    DepositRequestView,
    MarkDepositPaidCommand,
)
from app.schemas.dto.deposits.payment_link_requests import (
    DepositQuote,
    DepositQuoteQuery,
    PaymentLinkReceipt,
    SendPaymentLinkCommand,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.use_cases.deposits.add_payment_link_use_case import AddPaymentLinkUseCase
from app.use_cases.deposits.deposit_hold_release import DepositHoldRelease
from app.use_cases.deposits.deposit_issuing import DepositIssuing
from app.use_cases.deposits.deposit_notice_texts import DepositNoticeTexts
from app.use_cases.deposits.deposit_notices import DepositNotices
from app.use_cases.deposits.deposit_settings_changes import DepositSettingsChanges
from app.use_cases.deposits.deposit_subjects import DepositSubjects
from app.use_cases.deposits.get_deposit_report_use_case import GetDepositReportUseCase
from app.use_cases.deposits.get_deposit_request_use_case import (
    GetDepositRequestUseCase,
)
from app.use_cases.deposits.get_deposit_settings_use_case import (
    GetDepositSettingsUseCase,
)
from app.use_cases.deposits.mark_deposit_paid_use_case import MarkDepositPaidUseCase
from app.use_cases.deposits.payment_lines import PaymentLines
from app.use_cases.deposits.quote_deposit_use_case import QuoteDepositUseCase
from app.use_cases.deposits.remove_payment_link_use_case import (
    RemovePaymentLinkUseCase,
)
from app.use_cases.deposits.send_payment_link_use_case import SendPaymentLinkUseCase
from app.use_cases.deposits.set_deposit_policy_use_case import SetDepositPolicyUseCase
from app.use_cases.deposits.sweep_deposits_use_case import SweepDepositsUseCase
from app.use_cases.deposits.update_deposit_settings_use_case import (
    UpdateDepositSettingsUseCase,
)
from app.use_cases.shared.proactive_letters import ProactiveSender
from app.use_cases.shared.proactive_routes import ProactiveRouting


class DepositUseCasesContainer(containers.DeclarativeContainer):
    """
    Deposits and prepayment links (1190): the assistant's send_payment_link
    tool and the hint of a new booking, the owner's settings (payment pages,
    policies on resources, services and banquets), "Paid" in the cabinet,
    the minute's sweep (holds, reminders, refunds) and the Reports line.
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    authorize = account_use_cases.authorize_business_access_use_case
    wall_clock = time_provider.microsecond_wall_clock
    lines: Factory[PaymentLines] = Factory(
        PaymentLines,
        secret_cipher=adapters.secret_cipher,
        text_resolver=utilities.localized_text_resolver,
    )
    changes: Factory[DepositSettingsChanges] = Factory(
        DepositSettingsChanges,
        authorize_business_access=authorize,
        settings_repo=repositories.deposit_settings_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )

    get_deposit_settings_use_case: Factory[
        UseCaseContract[DepositSettingsQuery, DepositSettingsView]
    ] = Factory(
        GetDepositSettingsUseCase,
        authorize_business_access=authorize,
        deposit_settings_repo=repositories.deposit_settings_repo,
        wall_clock=wall_clock,
    )
    update_deposit_settings_use_case: Factory[
        UseCaseContract[UpdateDepositSettingsCommand, DepositSettingsView]
    ] = Factory(UpdateDepositSettingsUseCase, changes=changes)
    add_payment_link_use_case: Factory[
        UseCaseContract[AddPaymentLinkCommand, DepositSettingsView]
    ] = Factory(
        AddPaymentLinkUseCase, changes=changes, secret_cipher=adapters.secret_cipher
    )
    remove_payment_link_use_case: Factory[
        UseCaseContract[RemovePaymentLinkCommand, DepositSettingsView]
    ] = Factory(RemovePaymentLinkUseCase, changes=changes)
    set_deposit_policy_use_case: Factory[
        UseCaseContract[SetDepositPolicyCommand, DepositSettingsView]
    ] = Factory(
        SetDepositPolicyUseCase,
        changes=changes,
        resource_repo=repositories.resource_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
    )
    quote_deposit_use_case: Factory[
        UseCaseContract[DepositQuoteQuery, DepositQuote]
    ] = Factory(
        QuoteDepositUseCase,
        business_repo=repositories.business_repo,
        deposit_settings_repo=repositories.deposit_settings_repo,
        booking_repo=repositories.booking_repo,
        lead_repo=repositories.lead_repo,
    )
    send_payment_link_use_case: Factory[
        UseCaseContract[SendPaymentLinkCommand, PaymentLinkReceipt]
    ] = Factory(
        SendPaymentLinkUseCase,
        business_repo=repositories.business_repo,
        deposit_settings_repo=repositories.deposit_settings_repo,
        deposit_request_repo=repositories.deposit_request_repo,
        subjects=Factory(
            DepositSubjects,
            booking_repo=repositories.booking_repo,
            lead_repo=repositories.lead_repo,
        ),
        issuing=Factory(
            DepositIssuing,
            request_repo=repositories.deposit_request_repo,
            booking_repo=repositories.booking_repo,
            lead_repo=repositories.lead_repo,
            lines=lines,
        ),
        lock_registry=registries.business_lock_registry,
        live_events=facilitators.event_publisher,
        wall_clock=wall_clock,
    )
    get_deposit_request_use_case: Factory[
        UseCaseContract[DepositRequestQuery, DepositRequestView]
    ] = Factory(
        GetDepositRequestUseCase,
        authorize_business_access=authorize,
        deposit_request_repo=repositories.deposit_request_repo,
        deposit_settings_repo=repositories.deposit_settings_repo,
    )
    mark_deposit_paid_use_case: Factory[
        UseCaseContract[MarkDepositPaidCommand, DepositRequestView]
    ] = Factory(
        MarkDepositPaidUseCase,
        authorize_business_access=authorize,
        deposit_request_repo=repositories.deposit_request_repo,
        deposit_settings_repo=repositories.deposit_settings_repo,
        booking_repo=repositories.booking_repo,
        lead_repo=repositories.lead_repo,
        lock_registry=registries.business_lock_registry,
        audit_log_repo=repositories.audit_log_repo,
        live_events=facilitators.event_publisher,
        wall_clock=wall_clock,
    )
    get_deposit_report_use_case: Factory[
        UseCaseContract[DepositReportQuery, DepositReport]
    ] = Factory(
        GetDepositReportUseCase,
        authorize_business_access=authorize,
        deposit_settings_repo=repositories.deposit_settings_repo,
        deposit_request_repo=repositories.deposit_request_repo,
        booking_outcome_repo=repositories.booking_outcome_repo,
        wall_clock=wall_clock,
    )
    sweep_deposits_use_case: Factory[UseCaseContract[JobTick, JobReport]] = Factory(
        SweepDepositsUseCase,
        business_repo=repositories.business_repo,
        deposit_request_repo=repositories.deposit_request_repo,
        deposit_settings_repo=repositories.deposit_settings_repo,
        booking_repo=repositories.booking_repo,
        hold_release=Factory(
            DepositHoldRelease,
            request_repo=repositories.deposit_request_repo,
            booking_repo=repositories.booking_repo,
            lead_repo=repositories.lead_repo,
            lock_registry=registries.business_lock_registry,
        ),
        notices=Factory(
            DepositNotices,
            routing=Factory(
                ProactiveRouting,
                channel_repo=repositories.channel_repo,
                conversation_repo=repositories.conversation_repo,
                message_repo=repositories.message_repo,
            ),
            sender=Factory(
                ProactiveSender,
                outbound_message_repo=repositories.outbound_message_repo,
                job_queue=facilitators.job_queue_facilitator,
                conversation_repo=repositories.conversation_repo,
                message_repo=repositories.message_repo,
                unit_of_work=adapters.storage_unit_of_work,
            ),
            contact_repo=repositories.contact_repo,
            conversation_repo=repositories.conversation_repo,
            message_repo=repositories.message_repo,
            suppression_list=facilitators.suppression_list,
            live_events=facilitators.event_publisher,
        ),
        notice_texts=Factory(
            DepositNoticeTexts,
            lines=lines,
            text_resolver=utilities.localized_text_resolver,
        ),
        settlement=facilitators.deposit_settlement,
        growth=facilitators.growth_bookings,
        calendar_sync=facilitators.calendar_sync_facilitator,
        live_events=facilitators.event_publisher,
        wall_clock=wall_clock,
    )
