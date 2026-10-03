"""
A digest goes out once per period through the real worker and outbox, across
a worker restart, a run an hour later and a report whose record was lost.
"""

from app.schemas.constants.value import ValueReportKind
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.platform.constrained_strings import JobName
from tests.value.value_demo import DEMO_OWNER_EMAIL, open_value_demo


def ids(messages: list[OutboundMessageDocument]) -> list[str]:
    return sorted(str(message.id) for message in messages)


def test_a_digest_is_sent_once_across_a_worker_restart() -> None:
    with open_value_demo() as demo:
        container = demo.workshop.container
        first = container.gateways.background_worker().run_once()
        sent = demo.report_messages()

        restarted = container.gateways.background_worker().run_once()
        demo.workshop.clock.advance(60 * 60)
        an_hour_later = container.gateways.background_worker().run_once()

        assert first.failures == 0 and an_hour_later.failures == 0
        # Only the new process's own trace flush: the shared jobs, the
        # reports among them, already ran this hour.
        assert restarted.periodic_runs == 1
        # Delivered meanwhile (the worker sends the outbox), never queued again.
        assert ids(demo.report_messages()) == ids(sent)
        weekly = demo.get("/value-reports?kind=weekly").json()["items"]
        monthly = demo.get("/value-reports").json()["items"]
        assert [report["period_key"] for report in weekly] == ["2026-W40"]
        assert [report["period_key"] for report in monthly] == ["2026-09"]
        assert weekly[0]["delivery"] == "sent"
        owner_mail = [
            message
            for message in sent
            if message.staff_contact is not None
            and str(message.staff_contact.address) == DEMO_OWNER_EMAIL
        ]
        # The weekly digest and the monthly report of each demo business.
        assert len(owner_mail) == len({str(m.business_id) for m in owner_mail}) * 2
        assert len({str(message.id) for message in sent}) == len(sent)


def test_a_lost_report_record_sends_nothing_twice() -> None:
    with open_value_demo() as demo:
        container = demo.workshop.container
        job = container.use_cases.value.send_value_reports_use_case()
        tick = JobTick(
            job_name=JobName("send_value_reports"),
            scheduled_at=demo.workshop.clock.wall_clock.now_unix(),
        )
        scope = container.utilities.storage_scope()
        with scope.platform_wide():
            job.run(tick)
            sent = demo.report_messages()
            # The worker died after queueing and before the record was kept.
            reports = container.value_collections.value_report_collection()
            for report in reports.list_all():
                reports.delete(str(report.id))

            again = job.run(tick)

        assert int(again.processed_count) > 0
        assert ids(demo.report_messages()) == ids(sent)
        assert {
            report["kind"]
            for report in demo.get("/value-reports?kind=weekly").json()["items"]
        } == {ValueReportKind.WEEKLY.value}
