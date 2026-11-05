from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.campaign_repositories import (
    CampaignMessageChange,
    CampaignMessageRepoContract,
    CampaignSettingsRepoContract,
)
from app.repositories.aggregate_reading import parse_choice
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    ascending,
    field_among,
    field_equals,
    time_range,
)
from app.schemas.constants.campaigns import CampaignMessageStatus
from app.schemas.domain.campaigns import (
    CampaignMessageDocument,
    CampaignSettingsDocument,
)
from app.schemas.dto.growth.growth_counts import CampaignStatusCount
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.campaigns.constrained_integers import CampaignMessageCount
from app.schemas.typings.campaigns.constrained_strings import CampaignMonthKey
from app.schemas.typings.campaigns.prefixed_id import CampaignMessageId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.utilities.campaigns.campaign_keys import campaign_settings_id_of

CONTACT_ID_FIELD: DocumentFieldPath = DocumentFieldPath("contact_id")
IS_ENABLED_FIELD: DocumentFieldPath = DocumentFieldPath("is_enabled")
STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
MONTH_FIELD: DocumentFieldPath = DocumentFieldPath("month")
# What went out: the cap counts these, BOOKED ones included.
OUT_STATUSES: tuple[CampaignMessageStatus, ...] = (
    CampaignMessageStatus.SENT,
    CampaignMessageStatus.BOOKED,
)


class CampaignSettingsRepository(
    BusinessScopedRepository[CampaignSettingsDocument],
    CampaignSettingsRepoContract,
):
    """One settings document per business, keyed by the derived id."""

    def get_by_business(
        self, business_id: BusinessId
    ) -> CampaignSettingsDocument | None:
        return self._load(business_id, str(campaign_settings_id_of(business_id)))

    def save(self, settings: CampaignSettingsDocument) -> None:
        self._store(str(settings.id), settings)

    def list_enabled(self) -> list[CampaignSettingsDocument]:
        return self._collection.list_by_fields((field_equals(IS_ENABLED_FIELD, True),))


class CampaignMessageRepository(
    BusinessScopedRepository[CampaignMessageDocument],
    CampaignMessageRepoContract,
):
    """
    Campaign messages, keyed by the id derived from the business, the rule
    and the booking; counted per month and status, listed by status and
    send time, paged by creation (indexed, migration 1151).
    """

    def insert_if_new(self, message: CampaignMessageDocument) -> IsDocumentInserted:
        return self._collection.insert_if_absent(str(message.id), message)

    def get_many(
        self, business_id: BusinessId, message_ids: Sequence[CampaignMessageId]
    ) -> dict[CampaignMessageId, CampaignMessageDocument]:
        return {
            message.id: message
            for message in self._load_many(
                business_id, [str(message_id) for message_id in message_ids]
            )
        }

    def update(
        self,
        business_id: BusinessId,
        message_id: CampaignMessageId,
        change: CampaignMessageChange,
    ) -> CampaignMessageDocument | None:
        return self._modify_in_business(business_id, str(message_id), change)

    def list_of_contact(
        self, business_id: BusinessId, contact_id: ContactId
    ) -> list[CampaignMessageDocument]:
        return self._list_in_business(
            business_id,
            [field_equals(CONTACT_ID_FIELD, contact_id)],
            order=ascending(CREATED_AT_FIELD),
        )

    def count_sent_in_month(
        self, business_id: BusinessId, month: CampaignMonthKey
    ) -> CampaignMessageCount:
        groups: list[DocumentGroupCount] = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    matches=(field_equals(MONTH_FIELD, month),),
                    among=(field_among(STATUS_FIELD, OUT_STATUSES),),
                )
            ),
        )
        return CampaignMessageCount(sum(int(group.count) for group in groups))

    def page_latest(
        self, business_id: BusinessId, window: KeysetSlice
    ) -> list[CampaignMessageDocument]:
        return self._page_in_business(business_id, (CREATED_AT_FIELD,), window)

    def count_by_status(
        self, business_id: BusinessId, created_from: Microseconds
    ) -> list[CampaignStatusCount]:
        groups: list[DocumentGroupCount] = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    ranges=(time_range(CREATED_AT_FIELD, starting_at=created_from),)
                ),
                group_by=(STATUS_FIELD,),
            ),
        )
        return [
            CampaignStatusCount(
                status=status, count=CampaignMessageCount(int(group.count))
            )
            for group in groups
            if (status := parse_choice(CampaignMessageStatus, group.values[0]))
            is not None
        ]
