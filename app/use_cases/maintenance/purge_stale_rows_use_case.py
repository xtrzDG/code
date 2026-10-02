import logging

from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.channels import ChannelMessageReceiptRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import (
    OtpChallengeRepoContract,
    UserSessionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import DocumentCount

LOGGER: logging.Logger = logging.getLogger(__name__)
SECONDS_PER_HOUR: int = 60 * 60
# A login code is valid for minutes; the hourly send limits look back one
# hour. A day keeps enough history for abuse questions.
OTP_CHALLENGE_RETENTION_SECONDS: int = 24 * SECONDS_PER_HOUR
# Platforms redeliver a webhook for hours (Meta up to 7 days); a month of
# receipts is a wide margin.
CHANNEL_RECEIPT_RETENTION_SECONDS: int = 30 * 24 * SECONDS_PER_HOUR


class PurgeStaleRowsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Daily retention job: delete expired sessions, login codes older than a
    day, and webhook redelivery receipts older than 30 days, so the auth
    and receipt tables stop growing forever.

    Each delete is an indexed range query in small batches. A purge that
    removed rows is audited as RETENTION_PURGE without an actor or business
    (sessions and login codes hold phone numbers, e-mails and addresses).
    Running it twice is harmless.
    """

    def __init__(
        self,
        user_session_repo: UserSessionRepoContract,
        otp_challenge_repo: OtpChallengeRepoContract,
        channel_message_receipt_repo: ChannelMessageReceiptRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._otp_challenge_repo: OtpChallengeRepoContract = otp_challenge_repo
        self._channel_message_receipt_repo: ChannelMessageReceiptRepoContract = (
            channel_message_receipt_repo
        )
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        purged: list[tuple[str, DocumentCount]] = [
            ("user_session", self._user_session_repo.delete_expired(now)),
            (
                "otp_challenge",
                self._otp_challenge_repo.delete_created_before(
                    self._wall_clock.now_unix_with_delta(
                        Seconds(-OTP_CHALLENGE_RETENTION_SECONDS)
                    )
                ),
            ),
            (
                "channel_message_receipt",
                self._channel_message_receipt_repo.delete_created_before(
                    self._wall_clock.now_unix_with_delta(
                        Seconds(-CHANNEL_RECEIPT_RETENTION_SECONDS)
                    )
                ),
            ),
        ]
        for entity, count in purged:
            LOGGER.info("Purged %d stale %s rows", int(count), entity)
            if int(count) > 0:
                self._audit_log_repo.append(
                    AuditLogEntryDocument(
                        action=AuditAction.RETENTION_PURGE,
                        entity=AuditEntityName(entity),
                        created_at=now,
                        updated_at=now,
                    )
                )

        return JobReport(
            processed_count=ProcessedItemCount(sum(int(count) for _, count in purged))
        )
