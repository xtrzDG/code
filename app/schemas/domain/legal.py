from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.schemas.constants.legal import SubprocessorChangeKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.legal.booleans import IsLateSubprocessorNotice
from app.schemas.typings.legal.constrained_integers import (
    NoticeRecipientCount,
    NotifiedBusinessCount,
)
from app.schemas.typings.legal.constrained_strings import (
    SubprocessorChangeDate,
    SubprocessorChangeKey,
    SubprocessorKey,
)
from app.schemas.typings.legal.prefixed_id import (
    SubprocessorAnnouncementId,
    SubprocessorNoticeId,
)


class SubprocessorNoticeDocument(BaseDocument):
    """
    The notice one business got about one change of the sub-processor
    list (`subprocessor_notices`, DPA section 8.3): its id derives from the
    business and the change, so a business is told once however often the
    job runs. `recipient_count` is how many owners' addresses it was queued
    for; `is_late` marks a notice sent after the change took effect.
    """

    id: SubprocessorNoticeId
    business_id: BusinessId
    change_key: SubprocessorChangeKey
    kind: SubprocessorChangeKind
    subprocessor: SubprocessorKey
    effective_on: SubprocessorChangeDate
    recipient_count: NoticeRecipientCount
    is_late: IsLateSubprocessorNotice = False
    notified_at: Microseconds


class SubprocessorAnnouncementDocument(BaseDocument):
    """
    The announcement of one change to every business
    (`subprocessor_announcements`, a platform collection): started when the
    notice period opened, completed once every business that existed then
    was told. A completed change is not walked again; a business created
    later reads the change in the DPA's sub-processor table instead.
    """

    id: SubprocessorAnnouncementId
    change_key: SubprocessorChangeKey
    kind: SubprocessorChangeKind
    subprocessor: SubprocessorKey
    effective_on: SubprocessorChangeDate
    started_at: Microseconds
    completed_at: Microseconds | None = None
    notified_business_count: NotifiedBusinessCount = NotifiedBusinessCount(0)
    recipient_count: NoticeRecipientCount = NoticeRecipientCount(0)
