"""
A small platform for the legal tests: owners and staff in two businesses, a
sub-processor list with announced changes, a clock the test moves, and the
notices job over in-memory storage with a recording notifier.
"""

from datetime import UTC, date, datetime

from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.registries.legal.subprocessor_catalog import SUBPROCESSORS
from app.registries.legal.subprocessor_registry import SubprocessorRegistry
from app.registries.legal.subprocessor_texts import ORIGINAL_LIST_DATE, texts
from app.repositories.business_repositories import BusinessRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.legal_repositories import (
    SubprocessorAnnouncementRepository,
    SubprocessorNoticeRepository,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.legal import (
    SubprocessorAnnouncementDocument,
    SubprocessorNoticeDocument,
)
from app.schemas.domain.users import UserDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.legal import SubprocessorEntry
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.legal.constrained_strings import (
    ClientModuleName,
    SubprocessorChangeDate,
    SubprocessorKey,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.use_cases.legal.send_subprocessor_notices_use_case import (
    SendSubprocessorNoticesUseCase,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver

DAY: int = 24 * 60 * 60 * 1_000_000
# The list as the DPA's first version had it: the real catalog without its
# announced changes, so a test adds exactly the change it is about.
ORIGINAL_ENTRIES: tuple[SubprocessorEntry, ...] = tuple(
    entry
    for entry in SUBPROCESSORS
    if entry.addition_announced_on is None and entry.removed_on is None
)


def moment(day: str, hour: int = 9) -> Microseconds:
    """Microseconds of `hour`:00 UTC on an ISO day."""

    start = datetime.combine(date.fromisoformat(day), datetime.min.time(), UTC)
    return Microseconds(int(start.timestamp()) * 1_000_000 + hour * 3_600_000_000)


class Clock:
    """A wall clock the test sets."""

    def __init__(self, day: str) -> None:
        self.now: int = int(moment(day))
        self.wall_clock: WallClock[Microseconds] = WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: self.now * 1_000,
        )

    def set(self, day: str, hour: int = 9) -> None:
        self.now = int(moment(day, hour))


class RecordingNotifier:
    """The outbox: records each notification; fails for `failing_business`."""

    def __init__(self) -> None:
        self.sent: list[StaffNotification] = []
        self.failing_business: BusinessId | None = None

    def notify(self, notification: StaffNotification) -> bool:
        if notification.business_id == self.failing_business:
            raise RuntimeError("The outbox is unavailable.")

        self.sent.append(notification)
        return True


def announced_entry(
    key: str,
    added_on: str,
    announced_on: str,
    removed_on: str | None = None,
    removal_announced_on: str | None = None,
) -> SubprocessorEntry:
    """A sub-processor added after the original list, with its announcement."""

    return SubprocessorEntry(
        key=SubprocessorKey(key),
        name=texts("Mailbox EU", "Почта ЕС", "ფოსტა ევროკავშირი"),
        purpose=texts("E-mail delivery", "Отправка писем", "წერილების გაგზავნა"),
        personal_data=texts(
            "E-mail addresses", "Адреса e-mail", "ელფოსტის მისამართები"
        ),
        location=texts("EU", "ЕС", "ევროკავშირი"),
        client_modules=[ClientModuleName("email")],
        added_on=SubprocessorChangeDate(added_on),
        addition_announced_on=SubprocessorChangeDate(announced_on),
        removed_on=None if removed_on is None else SubprocessorChangeDate(removed_on),
        removal_announced_on=(
            None
            if removal_announced_on is None
            else SubprocessorChangeDate(removal_announced_on)
        ),
    )


def retiring_entry(removed_on: str, announced_on: str) -> SubprocessorEntry:
    """An original sub-processor that leaves the list."""

    original: SubprocessorEntry = SUBPROCESSORS[0]
    return original.model_copy(
        update={
            "removed_on": SubprocessorChangeDate(removed_on),
            "removal_announced_on": SubprocessorChangeDate(announced_on),
        }
    )


def user(
    locale: str, email: str | None = None, phone: str | None = None
) -> UserDocument:
    return UserDocument(
        login_method=LoginMethod.EMAIL if email else LoginMethod.PHONE,
        email=None if email is None else EmailAddress(email),
        phone_number=None if phone is None else E164PhoneNumber(phone),
        locale=LanguageTag(locale),
    )


def business(
    name: str, created_on: str, *members: tuple[UserDocument, BusinessMemberRole]
) -> BusinessDocument:
    created: Microseconds = moment(created_on)
    return BusinessDocument(
        name=BusinessName(name),
        niche_key=NicheKey.RESTAURANT,
        country_code=CountryCode("GE"),
        timezone=TimezoneName("Asia/Tbilisi"),
        currency_code=CurrencyCode("GEL"),
        languages=[LanguageTag("ka"), LanguageTag("en")],
        default_language=LanguageTag("ka"),
        owner_language=LanguageTag("ka"),
        plan_key=PlanKey.VOICE_AND_CHAT,
        data_region=DataRegion.EU,
        members=[
            BusinessMember(user_id=person.id, role=role) for person, role in members
        ],
        created_at=created,
        updated_at=created,
    )


def put[Stored: BaseDocument](
    collection: DocumentCollectionAdapterContract[Stored], *documents: Stored
) -> None:
    for document in documents:
        collection.upsert(str(vars(document)["id"]), document)


class NoticeWorld:
    """Two businesses, their owners and staff, and the notices job."""

    def __init__(self, entries: tuple[SubprocessorEntry, ...], today: str) -> None:
        self.clock = Clock(today)
        self.users = InMemoryDocumentCollectionAdapter[UserDocument](UserDocument)
        self.businesses = InMemoryDocumentCollectionAdapter[BusinessDocument](
            BusinessDocument
        )
        self.audit = InMemoryDocumentCollectionAdapter[AuditLogEntryDocument](
            AuditLogEntryDocument
        )
        self.notices = InMemoryDocumentCollectionAdapter[SubprocessorNoticeDocument](
            SubprocessorNoticeDocument
        )
        self.announcements = InMemoryDocumentCollectionAdapter[
            SubprocessorAnnouncementDocument
        ](SubprocessorAnnouncementDocument)
        self.notifier = RecordingNotifier()
        self.ru_owner = user("ru", email="nino@salon.example")
        self.ka_owner = user("ka", phone="+995555123456")
        self.staff = user("en", email="giorgi@salon.example")
        self.cafe_owner = user("en-GB", email="owner@cafe.example")
        put(self.users, self.ru_owner, self.ka_owner, self.staff, self.cafe_owner)
        self.salon = business(
            "Salon Ia",
            str(ORIGINAL_LIST_DATE),
            (self.ru_owner, BusinessMemberRole.OWNER),
            (self.ka_owner, BusinessMemberRole.OWNER),
            (self.staff, BusinessMemberRole.STAFF),
        )
        self.cafe = business(
            "Café", str(ORIGINAL_LIST_DATE), (self.cafe_owner, BusinessMemberRole.OWNER)
        )
        put(self.businesses, self.salon, self.cafe)
        self.registry = SubprocessorRegistry(entries=entries)
        self.job = SendSubprocessorNoticesUseCase(
            subprocessor_registry=self.registry,
            announcement_repo=SubprocessorAnnouncementRepository(self.announcements),
            notice_repo=SubprocessorNoticeRepository(self.notices),
            business_repo=BusinessRepository(self.businesses),
            user_repo=UserRepository(self.users),
            audit_log_repo=AuditLogRepository(self.audit),
            manager_notifier=self.notifier,
            localized_text_resolver=LocalizedTextResolver(),
            wall_clock=self.clock.wall_clock,
        )
