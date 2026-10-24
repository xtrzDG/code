"""The public API's contacts: `GET /v1/public-api/contacts[/{id}]`."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.integrations import PublicRecordReaderContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.integrations import ApiKeyScope
from app.schemas.dto.public_api.access import PublicContactQuery, PublicListQuery
from app.schemas.dto.public_api.pages import PublicContactPage
from app.schemas.dto.public_api.records import PublicContact
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.integrations.api_key_records import require_scope
from app.use_cases.integrations.public_api.public_access import (
    API_CONTACT_ENTITY,
    key_business,
    record_public_read,
)
from app.utilities.integrations.public_views import public_contact
from app.utilities.paging.keyset_paging import finish_page, read_slice

UNKNOWN_CONTACT_MESSAGE: str = "Contact not found."


class ListPublicContactsUseCase(UseCaseContract[PublicListQuery, PublicContactPage]):
    """
    The key's business's contacts, the newest first, one keyset page at a
    time; customers erased at their request are left out (a page may then
    hold fewer). Needs `contacts:read`; audited with the number read.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        contact_repo: ContactRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PublicListQuery) -> PublicContactPage:
        require_scope(input_data.principal, ApiKeyScope.CONTACTS_READ)
        business = key_business(self._business_repo, input_data.principal)
        contacts, next_cursor = finish_page(
            self._contact_repo.page_by_business(
                business.id, read_slice(input_data.page)
            ),
            input_data.page,
            lambda contact: int(contact.created_at),
            lambda contact: str(contact.id),
        )
        items = [
            public_contact(contact) for contact in contacts if contact.erased_at is None
        ]
        record_public_read(
            self._audit_log_repo,
            input_data.principal,
            API_CONTACT_ENTITY,
            len(items),
            self._wall_clock.now_unix(),
        )
        return PublicContactPage(items=items, next_cursor=next_cursor)


class GetPublicContactUseCase(UseCaseContract[PublicContactQuery, PublicContact]):
    """One contact of the key's business. Needs `contacts:read`; audited."""

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        record_reader: PublicRecordReaderContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._record_reader: PublicRecordReaderContract = record_reader
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PublicContactQuery) -> PublicContact:
        require_scope(input_data.principal, ApiKeyScope.CONTACTS_READ)
        business = key_business(self._business_repo, input_data.principal)
        contact = self._record_reader.contact(business, input_data.contact_id)
        if contact is None:
            raise NotFoundError(UNKNOWN_CONTACT_MESSAGE)

        record_public_read(
            self._audit_log_repo,
            input_data.principal,
            API_CONTACT_ENTITY,
            1,
            self._wall_clock.now_unix(),
        )
        return contact
