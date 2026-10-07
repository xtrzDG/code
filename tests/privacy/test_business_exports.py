"""
The full export of a business: owners ask (stepped up, audited, one at a
time), the worker writes an encrypted ZIP of every collection and the CSV
tables, one-time links download it during its day, then the archive is
purged.
"""

import json
from typing import BinaryIO

import pytest

from app.contracts.export_archives import ExportArchiveStorageContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.privacy import BusinessExportStatus
from app.schemas.dto.privacy.business_exports import BusinessExportListQuery
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    NotFoundError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.strings import ExportArchivePath
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.business_export_queue import BUILD_BUSINESS_EXPORT_JOB
from app.utilities.privacy.csv_writing import UTF8_BOM
from tests.compliance.two_tenants import command, seed_two_tenants
from tests.privacy.business_export_bed import BusinessExportBed, read_zip

DAY_SECONDS: int = 24 * 3600


def audit_entries(bed: BusinessExportBed, entity: str) -> list[str]:
    return [
        str(entry.entity_id)
        for entry in bed.tenants.testbed.audit_log_repo.list_by_business(
            bed.tenants.business.id
        )
        if entry.action is AuditAction.EXPORT and str(entry.entity) == entity
    ]


def test_the_owner_asks_once_and_the_worker_writes_the_archive() -> None:
    bed = BusinessExportBed(seed_two_tenants())

    queued = bed.ask()
    again = bed.ask()

    assert queued.status is BusinessExportStatus.QUEUED
    assert again.id == queued.id
    assert [job.name for job in bed.queue.jobs] == [BUILD_BUSINESS_EXPORT_JOB]
    assert audit_entries(bed, "business") == [str(queued.id)]

    report = bed.run_job()

    assert int(report.processed_count) == 1
    [ready] = bed.list.run(_list_query(bed)).items
    assert ready.status is BusinessExportStatus.READY
    assert ready.model_dump()["download_path"] is None
    assert int(ready.downloads_left) == 3
    assert ready.archive_bytes is not None and int(ready.archive_bytes) > 0
    [sealed] = bed.objects.objects.values()
    assert sealed.startswith(b"AWX2")  # sealed in segments as it was read
    assert b"Giorgi" not in sealed

    download = bed.download(str(bed.link(ready.id).download_path))

    assert str(download.file_name).startswith("business-export-")
    archive = b"".join(download.pieces)
    files = read_zip(archive)
    assert {"README.txt", "contacts.json", "messages.json", "csv/bookings.csv"} <= set(
        files
    )
    contacts = json.loads(files["contacts.json"])
    assert {contact["name"] for contact in contacts} == {"Giorgi", "Nino"}
    assert "Noa" not in archive.decode("latin-1")
    assert files["csv/bookings.csv"].startswith(UTF8_BOM + "Booking ID,")
    assert all(
        "review_token" not in request
        for request in json.loads(files["feedback_requests.json"])
    )
    assert audit_entries(bed, "business_export") == [str(ready.id)]


def test_staff_may_not_ask_or_see_the_links() -> None:
    tenants = seed_two_tenants()
    bed = BusinessExportBed(tenants)

    with pytest.raises(AccessDeniedError):
        bed.ask(user_id=tenants.staff_id)
    with pytest.raises(AccessDeniedError):
        bed.list.run(_list_query(bed, tenants.staff_id))

    assert bed.queue.jobs == []


def test_an_erased_customer_is_not_in_the_archive() -> None:
    tenants = seed_two_tenants()
    bed = BusinessExportBed(tenants)
    tenants.testbed.delete_contact_data.run(
        command(tenants, tenants.visitor.contact.id)
    )
    bed.ask()
    bed.run_job()
    [ready] = bed.list.run(_list_query(bed)).items

    files = read_zip(
        b"".join(bed.download(str(bed.link(ready.id).download_path)).pieces)
    )

    contacts = json.loads(files["contacts.json"])
    assert [contact["name"] for contact in contacts] == ["Nino"]
    assert "Giorgi" not in "".join(files.values())
    assert str(tenants.visitor.booking.id) not in files["csv/bookings.csv"]


def test_the_archive_is_purged_after_its_day() -> None:
    bed = BusinessExportBed(seed_two_tenants())
    ready = bed.ready_export()
    path = str(bed.link(ready.id).download_path)

    bed.clock.advance(DAY_SECONDS + 1)
    with pytest.raises(NotFoundError):
        bed.download(path)
    with pytest.raises(NotFoundError):
        bed.link(ready.id)

    assert int(bed.run_purge().processed_count) == 1
    assert int(bed.run_purge().processed_count) == 0
    assert bed.objects.objects == {}
    [expired] = bed.list.run(_list_query(bed)).items
    assert expired.status is BusinessExportStatus.EXPIRED
    assert int(expired.downloads_left) == 0


def test_a_failure_is_retried_then_left_failed() -> None:
    class BrokenStorage(ExportArchiveStorageContract):
        def store(
            self, business_id: BusinessId, path: ExportArchivePath, archive: BinaryIO
        ) -> None:
            raise OSError("disk full")

        def read(self, business_id: BusinessId, path: ExportArchivePath) -> None:
            return None

        def delete(self, business_id: BusinessId, path: ExportArchivePath) -> None:
            return None

    bed = BusinessExportBed(seed_two_tenants(), archive_storage=BrokenStorage())
    bed.ask()

    with pytest.raises(OSError):
        bed.run_job(is_final_attempt=False)
    bed.run_job(is_final_attempt=True)

    [failed] = bed.list.run(_list_query(bed)).items
    assert failed.status is BusinessExportStatus.FAILED
    assert failed.last_error is not None
    assert failed.model_dump()["download_path"] is None
    assert bed.ask().id != failed.id  # a failed export does not block a new one


def _list_query(
    bed: BusinessExportBed, user_id: UserId | None = None
) -> BusinessExportListQuery:
    return BusinessExportListQuery(
        user_id=bed.tenants.owner_id if user_id is None else user_id,
        business_id=bed.tenants.business.id,
    )
