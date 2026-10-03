"""
The growth analytics' storage on the in-memory and the Postgres storage
(migration 1074): product events stored once and read by name and time,
Web Vitals counted per page, device and value bucket and purged after 90
days (audited), accounts read by creation time.
"""

import pytest
from typed_time_provider import Microseconds

from app.repositories.analytics_repositories import (
    ProductEventRepository,
    WebVitalSampleRepository,
)
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.analytics import (
    DeviceClass,
    ProductEventName,
    ProductEventSource,
    WebVitalName,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.domain.users import UserDocument
from app.schemas.domain.web_vitals import WebVitalSampleDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.analytics.constrained_integers import WebVitalValue
from app.schemas.typings.analytics.constrained_strings import CabinetRoutePattern
from app.schemas.typings.analytics.prefixed_id import ProductEventId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.telemetry.purge_web_vitals_use_case import PurgeWebVitalsUseCase
from tests.storage.conftest import CollectionFactory
from tests.storage.storage_testing import FIXED_NANOSECONDS, build_fixed_wall_clock

pytestmark = pytest.mark.usefixtures("platform_scope")

NOW: int = FIXED_NANOSECONDS // 1_000
DAY: int = 24 * 60 * 60 * 1_000_000
OWNER: UserId = UserId()
INBOX = CabinetRoutePattern("/b/[businessId]/inbox")
SETTINGS = CabinetRoutePattern("/b/[businessId]/settings")


def product_event(name: ProductEventName, days_ago: float) -> ProductEventDocument:
    moment = Microseconds(NOW - int(days_ago * DAY))
    return ProductEventDocument(
        id=ProductEventId(),
        name=name,
        occurred_at=moment,
        source=ProductEventSource.SERVER,
        user_id=OWNER,
        created_at=moment,
        updated_at=moment,
    )


def vital(
    value: int,
    days_ago: float,
    route: CabinetRoutePattern = INBOX,
    device: DeviceClass = DeviceClass.MOBILE,
) -> WebVitalSampleDocument:
    moment = Microseconds(NOW - int(days_ago * DAY))
    return WebVitalSampleDocument(
        user_id=OWNER,
        metric=WebVitalName.LCP,
        value=WebVitalValue(value),
        route=route,
        device_class=device,
        created_at=moment,
        updated_at=moment,
    )


def test_product_events_are_stored_once_and_read_by_name_and_time(
    collections: CollectionFactory,
) -> None:
    repo = ProductEventRepository(collections(ProductEventDocument, "product_events"))
    signed_up = product_event(ProductEventName.SIGNED_UP, 10)
    live = product_event(ProductEventName.WENT_LIVE, 3)
    old = product_event(ProductEventName.WENT_LIVE, 40)

    assert repo.record(signed_up) is True
    assert repo.record(signed_up) is False
    for event in (live, old, product_event(ProductEventName.SIGNED_IN, 1)):
        repo.record(event)

    read = repo.list_named(
        [ProductEventName.WENT_LIVE, ProductEventName.SIGNED_UP],
        Microseconds(NOW - 30 * DAY),
        Microseconds(NOW),
    )
    assert [event.id for event in read] == [signed_up.id, live.id]
    every = repo.list_named([ProductEventName.WENT_LIVE], None, Microseconds(NOW))
    assert [event.id for event in every] == [old.id, live.id]


def test_web_vitals_are_counted_per_page_device_and_bucket(
    collections: CollectionFactory,
) -> None:
    repo = WebVitalSampleRepository(
        collections(WebVitalSampleDocument, "web_vital_samples")
    )
    repo.add_many(
        [
            vital(900, 1),
            vital(1100, 1),
            vital(3000, 2),
            vital(800, 1, SETTINGS, DeviceClass.DESKTOP),
            vital(5000, 50),
        ]
    )

    counts = repo.count_buckets(
        WebVitalName.LCP,
        Microseconds(NOW - 7 * DAY),
        Microseconds(NOW + 1),
        [WebVitalValue(0), WebVitalValue(1000), WebVitalValue(2500)],
    )

    assert sorted(
        (str(c.route), c.device_class, int(c.bucket), int(c.count)) for c in counts
    ) == [
        ("/b/[businessId]/inbox", DeviceClass.MOBILE, 0, 1),
        ("/b/[businessId]/inbox", DeviceClass.MOBILE, 1, 1),
        ("/b/[businessId]/inbox", DeviceClass.MOBILE, 2, 1),
        ("/b/[businessId]/settings", DeviceClass.DESKTOP, 0, 1),
    ]
    assert (
        repo.count_buckets(
            WebVitalName.INP,
            Microseconds(NOW - 7 * DAY),
            Microseconds(NOW + 1),
            [WebVitalValue(0)],
        )
        == []
    )


def test_the_purge_deletes_vitals_older_than_90_days_and_is_audited(
    collections: CollectionFactory,
) -> None:
    repo = WebVitalSampleRepository(
        collections(WebVitalSampleDocument, "web_vital_samples")
    )
    audit_collection = collections(AuditLogEntryDocument, "audit_log_entries")
    fresh = vital(1000, 89)
    repo.add_many([vital(1000, 91), vital(2000, 200), fresh])
    purge = PurgeWebVitalsUseCase(
        web_vital_sample_repo=repo,
        audit_log_repo=AuditLogRepository(audit_collection),
        wall_clock=build_fixed_wall_clock(),
    )
    tick = JobTick(job_name=JobName("purge_web_vitals"), scheduled_at=Microseconds(NOW))

    assert int(purge.run(tick).processed_count) == 2
    assert int(purge.run(tick).processed_count) == 0
    left = repo.count_buckets(
        WebVitalName.LCP,
        Microseconds(0),
        Microseconds(NOW + 1),
        [WebVitalValue(0)],
    )
    assert [int(c.count) for c in left] == [1]
    (entry,) = audit_collection.list_all()
    assert (entry.action, str(entry.entity), entry.actor_id) == (
        AuditAction.RETENTION_PURGE,
        "web_vital_sample",
        None,
    )


def test_accounts_are_read_by_creation_time(collections: CollectionFactory) -> None:
    repo = UserRepository(collections(UserDocument, "users"))
    users = [
        UserDocument(
            login_method=LoginMethod.EMAIL,
            locale=LanguageTag("en"),
            created_at=Microseconds(NOW - days * DAY),
            updated_at=Microseconds(NOW - days * DAY),
        )
        for days in (40, 20, 10)
    ]
    for user in users:
        repo.save(user)

    created = repo.list_created_between(Microseconds(NOW - 30 * DAY), Microseconds(NOW))

    assert [user.id for user in created] == [users[1].id, users[2].id]
    assert {user.id for user in repo.get_many([users[0].id, users[2].id])} == {
        users[0].id,
        users[2].id,
    }
