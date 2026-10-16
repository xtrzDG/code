from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.call_follow_up_repositories import (
    MissedCallRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.calls.call_settings import TextBackPage, TextBackPageQuery
from app.schemas.typings.compliance.strings import AuditEntityName
from app.use_cases.voice.call_settings.call_settings_views import (
    build_text_back_view,
)
from app.utilities.paging.keyset_paging import finish_page, read_slice

MISSED_CALL_ENTITY: AuditEntityName = AuditEntityName("missed_call")


class ListTextBacksUseCase(UseCaseContract[TextBackPageQuery, TextBackPage]):
    """
    The callers who did not get through, newest first, one keyset page at
    a time (Settings → Calls shows the last 20): why, the caller's number,
    and whether the text-back went out, how, or why not. Owners only; the
    numbers are personal data, so the view is audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        missed_call_repo: MissedCallRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._missed_call_repo: MissedCallRepoContract = missed_call_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: TextBackPageQuery) -> TextBackPage:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        fetched: list[MissedCallDocument] = self._missed_call_repo.page_by_business(
            business.id, read_slice(input_data.page)
        )
        items, next_cursor = finish_page(
            fetched,
            input_data.page,
            sort_key=lambda missed: int(missed.created_at),
            item_id=lambda missed: str(missed.id),
        )
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.VIEW,
                entity=MISSED_CALL_ENTITY,
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return TextBackPage(
            items=[build_text_back_view(missed) for missed in items],
            next_cursor=next_cursor,
        )
