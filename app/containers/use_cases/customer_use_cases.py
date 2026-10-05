from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.contacts import ContactPage
from app.schemas.dto.customers.customer_card import (
    ChangeCustomerBlockingCommand,
    ChangeCustomerCardCommand,
    ContactStandingQuery,
    ContactStandingView,
    CustomerCardView,
)
from app.schemas.dto.customers.customer_segments import (
    CreateSegmentCommand,
    SegmentExportPageQuery,
    SegmentList,
    SegmentListQuery,
    SegmentMembersQuery,
    SegmentPreview,
    SegmentPreviewCommand,
    SegmentQuery,
    SegmentView,
    StartSegmentExportCommand,
    UpdateSegmentCommand,
)
from app.schemas.dto.customers.customer_settings import (
    CustomerSettingsQuery,
    CustomerSettingsView,
    UpdateCustomerSettingsCommand,
)
from app.schemas.dto.privacy.csv_exports import CsvExportHeader, CsvExportPage
from app.schemas.dto.search import BusinessSearchQuery, BusinessSearchResults
from app.use_cases.contacts.change_customer_blocking_use_case import (
    ChangeCustomerBlockingUseCase,
)
from app.use_cases.contacts.change_customer_card_use_case import (
    ChangeCustomerCardUseCase,
)
from app.use_cases.contacts.get_contact_standing_use_case import (
    GetContactStandingUseCase,
)
from app.use_cases.contacts.get_customer_settings_use_case import (
    GetCustomerSettingsUseCase,
)
from app.use_cases.contacts.segments.create_segment_use_case import (
    CreateSegmentUseCase,
)
from app.use_cases.contacts.segments.delete_segment_use_case import (
    DeleteSegmentUseCase,
)
from app.use_cases.contacts.segments.list_segment_members_use_case import (
    ListSegmentMembersUseCase,
)
from app.use_cases.contacts.segments.list_segments_use_case import ListSegmentsUseCase
from app.use_cases.contacts.segments.preview_segment_use_case import (
    PreviewSegmentUseCase,
)
from app.use_cases.contacts.segments.read_segment_export_page_use_case import (
    ReadSegmentExportPageUseCase,
)
from app.use_cases.contacts.segments.start_segment_export_use_case import (
    StartSegmentExportUseCase,
)
from app.use_cases.contacts.segments.update_segment_use_case import (
    UpdateSegmentUseCase,
)
from app.use_cases.contacts.update_customer_settings_use_case import (
    UpdateCustomerSettingsUseCase,
)
from app.use_cases.search.search_business_use_case import SearchBusinessUseCase
from app.use_cases.shared.customer_segment_members import SegmentReaders


class CustomerUseCasesContainer(containers.DeclarativeContainer):
    """
    Customers (1140): the team's card on a customer (tags, VIP, block), the
    standing under a conversation, the team's customer settings, saved
    segments with their members and CSV, and the cabinet's search. The
    list and one customer's page are in `ComplianceUseCasesContainer`
    (they began as the owner's data requests).
    """

    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    authorize = account_use_cases.authorize_business_access_use_case
    wall_clock = time_provider.microsecond_wall_clock
    segment_readers: Factory[SegmentReaders] = Factory(
        SegmentReaders,
        card_repo=repositories.contact_repo,
        activity_repo=repositories.contact_activity_repo,
        history_repo=repositories.customer_history_repo,
    )

    change_customer_card_use_case: Factory[
        UseCaseContract[ChangeCustomerCardCommand, CustomerCardView]
    ] = Factory(
        ChangeCustomerCardUseCase,
        authorize_business_access=authorize,
        card_repo=repositories.contact_repo,
        customer_settings_repo=repositories.customer_settings_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
    change_customer_blocking_use_case: Factory[
        UseCaseContract[ChangeCustomerBlockingCommand, CustomerCardView]
    ] = Factory(
        ChangeCustomerBlockingUseCase,
        authorize_business_access=authorize,
        card_repo=repositories.contact_repo,
        customer_settings_repo=repositories.customer_settings_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
    get_contact_standing_use_case: Factory[
        UseCaseContract[ContactStandingQuery, ContactStandingView]
    ] = Factory(
        GetContactStandingUseCase,
        authorize_business_access=authorize,
        contact_repo=repositories.contact_repo,
        contact_activity_repo=repositories.contact_activity_repo,
        customer_history_repo=repositories.customer_history_repo,
        wall_clock=wall_clock,
    )
    get_customer_settings_use_case: Factory[
        UseCaseContract[CustomerSettingsQuery, CustomerSettingsView]
    ] = Factory(
        GetCustomerSettingsUseCase,
        authorize_business_access=authorize,
        customer_settings_repo=repositories.customer_settings_repo,
    )
    update_customer_settings_use_case: Factory[
        UseCaseContract[UpdateCustomerSettingsCommand, CustomerSettingsView]
    ] = Factory(
        UpdateCustomerSettingsUseCase,
        authorize_business_access=authorize,
        customer_settings_repo=repositories.customer_settings_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
    list_segments_use_case: Factory[UseCaseContract[SegmentListQuery, SegmentList]] = (
        Factory(
            ListSegmentsUseCase,
            authorize_business_access=authorize,
            segment_repo=repositories.customer_segment_repo,
            customer_settings_repo=repositories.customer_settings_repo,
        )
    )
    create_segment_use_case: Factory[
        UseCaseContract[CreateSegmentCommand, SegmentView]
    ] = Factory(
        CreateSegmentUseCase,
        authorize_business_access=authorize,
        segment_repo=repositories.customer_segment_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
    update_segment_use_case: Factory[
        UseCaseContract[UpdateSegmentCommand, SegmentView]
    ] = Factory(
        UpdateSegmentUseCase,
        authorize_business_access=authorize,
        segment_repo=repositories.customer_segment_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
    delete_segment_use_case: Factory[UseCaseContract[SegmentQuery, None]] = Factory(
        DeleteSegmentUseCase,
        authorize_business_access=authorize,
        segment_repo=repositories.customer_segment_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
    list_segment_members_use_case: Factory[
        UseCaseContract[SegmentMembersQuery, ContactPage]
    ] = Factory(
        ListSegmentMembersUseCase,
        authorize_business_access=authorize,
        segment_repo=repositories.customer_segment_repo,
        readers=segment_readers,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
    preview_segment_use_case: Factory[
        UseCaseContract[SegmentPreviewCommand, SegmentPreview]
    ] = Factory(
        PreviewSegmentUseCase,
        authorize_business_access=authorize,
        readers=segment_readers,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
    start_segment_export_use_case: Factory[
        UseCaseContract[StartSegmentExportCommand, CsvExportHeader]
    ] = Factory(
        StartSegmentExportUseCase,
        authorize_business_access=authorize,
        segment_repo=repositories.customer_segment_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
        step_up=utilities.step_up_guard,
        text_resolver=utilities.localized_text_resolver,
    )
    read_segment_export_page_use_case: Factory[
        UseCaseContract[SegmentExportPageQuery, CsvExportPage]
    ] = Factory(
        ReadSegmentExportPageUseCase,
        authorize_business_access=authorize,
        segment_repo=repositories.customer_segment_repo,
        readers=segment_readers,
        wall_clock=wall_clock,
    )
    search_business_use_case: Factory[
        UseCaseContract[BusinessSearchQuery, BusinessSearchResults]
    ] = Factory(
        SearchBusinessUseCase,
        authorize_business_access=authorize,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        booking_repo=repositories.booking_repo,
        contact_activity_repo=repositories.contact_activity_repo,
        customer_history_repo=repositories.customer_history_repo,
        customer_settings_repo=repositories.customer_settings_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
        phone_number_parser=utilities.phone_number_parser,
    )
