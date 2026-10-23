"""Background job: rented numbers given back, kept with their agent, requests closed."""

import logging
from collections.abc import Iterator

from typed_time_provider import Microseconds, WallClock

from app.contracts.phone_numbers import (
    PhoneLineLockRegistryContract,
    PhoneNumberProvisionerAdapterContract,
    PhoneNumberRepoContract,
    PhoneNumberRequestRepoContract,
)
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.phone_numbers import (
    PhoneNumberReleaseReason,
    PhoneNumberRequestStatus,
    PhoneNumberStatus,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.phone_numbers import (
    PhoneNumberDocument,
    PhoneNumberRequestDocument,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.phone_numbers.provisioning import PhoneNumberRelease
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.channels.phone_numbers.phone_line_lookups import (
    find_answering_agent,
)
from app.use_cases.channels.phone_numbers.rental_checks import label_of
from app.use_cases.channels.phone_numbers.rented_line_channel import (
    connected_number,
    disconnect_rented_line,
    find_phone_channel,
)
from app.use_cases.channels.phone_numbers.voice_attachment import attach_to_agent

logger: logging.Logger = logging.getLogger(__name__)
BATCH: DocumentQueryLimit = DocumentQueryLimit(100)


class MaintainPhoneNumbersUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Every five minutes, across businesses (`maintain_phone_numbers`):

    - a number being given back (RELEASING) is removed from the voice
      platform and returned to the carrier, then RELEASED; one given back
      for want of payment also turns off the phone channel that still
      carries it. A carrier that refuses leaves it RELEASING for the next
      run, so a number is never forgotten while the platform pays for it;
    - an ACTIVE number answers with the business's live voice agent: one
      the voice platform has not imported yet is imported, one whose
      business went live (or changed or lost its agent) is assigned anew;
    - an open request for a number is DONE once the business's phone
      channel is connected (the team connected the number it arranged).

    Each number is handled under its business's phone line lock, so the
    job never races an owner taking or giving back a number.
    """

    def __init__(
        self,
        phone_number_repo: PhoneNumberRepoContract,
        phone_number_request_repo: PhoneNumberRequestRepoContract,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        phone_number_provisioner: PhoneNumberProvisionerAdapterContract,
        phone_line_lock: PhoneLineLockRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._phone_number_repo: PhoneNumberRepoContract = phone_number_repo
        self._request_repo: PhoneNumberRequestRepoContract = phone_number_request_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._provisioner: PhoneNumberProvisionerAdapterContract = (
            phone_number_provisioner
        )
        self._phone_line_lock: PhoneLineLockRegistryContract = phone_line_lock
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        processed: int = sum(
            1
            for number in self._walk(PhoneNumberStatus.RELEASING)
            if self._give_back(number)
        )
        processed += sum(
            1
            for number in self._walk(PhoneNumberStatus.ACTIVE)
            if self._keep_attached(number)
        )
        processed += self._close_fulfilled_requests()
        return JobReport(processed_count=ProcessedItemCount(processed))

    def _walk(self, status: PhoneNumberStatus) -> Iterator[PhoneNumberDocument]:
        after: PhoneNumberDocument | None = None
        while True:
            page: list[PhoneNumberDocument] = self._phone_number_repo.page_in_status(
                status, after, BATCH
            )
            yield from page
            if len(page) < int(BATCH):
                return

            after = page[-1]

    def _give_back(self, number: PhoneNumberDocument) -> bool:
        with self._phone_line_lock.lock_for(number.business_id):
            stored: PhoneNumberDocument | None = self._phone_number_repo.get(
                number.business_id, number.id
            )
            if stored is None or stored.status is not PhoneNumberStatus.RELEASING:
                return False

            try:
                self._provisioner.release_number(
                    PhoneNumberRelease(
                        provider_number_id=stored.provider_number_id,
                        voice_platform_number_id=stored.voice_platform_number_id,
                    )
                )
            except ExternalServiceError as error:
                logger.warning(
                    "Rented number %s of business %s is not given back yet: %s",
                    stored.id,
                    stored.business_id,
                    error,
                )
                return False

            now: Microseconds = self._wall_clock.now_unix()
            if stored.release_reason is PhoneNumberReleaseReason.UNPAID:
                disconnect_rented_line(
                    self._channel_repo, stored.business_id, stored.phone_number, now
                )

            self._phone_number_repo.modify(
                stored.business_id,
                stored.id,
                lambda current: (
                    current.model_copy(
                        update={
                            "status": PhoneNumberStatus.RELEASED,
                            "released_at": now,
                            "updated_at": now,
                        }
                    )
                    if current.status is PhoneNumberStatus.RELEASING
                    else None
                ),
            )
            return True

    def _keep_attached(self, number: PhoneNumberDocument) -> bool:
        agent_id: VoiceAgentId | None = find_answering_agent(
            self._assistant_version_repo, number.business_id
        )
        if (
            number.voice_platform_number_id is not None
            and number.attached_agent_id == agent_id
        ):
            return False

        business: BusinessDocument | None = self._business_repo.get(number.business_id)
        if business is None:
            return False

        with self._phone_line_lock.lock_for(number.business_id):
            stored: PhoneNumberDocument | None = self._phone_number_repo.get(
                number.business_id, number.id
            )
            if stored is None:
                return False

            attached: PhoneNumberDocument = attach_to_agent(
                self._provisioner,
                self._phone_number_repo,
                stored,
                agent_id,
                label_of(business),
                self._wall_clock.now_unix(),
            )
            return attached is not stored

    def _close_fulfilled_requests(self) -> int:
        closed: int = 0
        for request in self._open_requests():
            if (
                connected_number(
                    find_phone_channel(self._channel_repo, request.business_id)
                )
                is None
            ):
                continue

            now: Microseconds = self._wall_clock.now_unix()
            request.status = PhoneNumberRequestStatus.DONE
            request.closed_at = now
            request.updated_at = now
            self._request_repo.save(request)
            closed += 1

        return closed

    def _open_requests(self) -> Iterator[PhoneNumberRequestDocument]:
        """Every open request, page by page (however many wait)."""

        after: PhoneNumberRequestDocument | None = None
        while True:
            page: list[PhoneNumberRequestDocument] = self._request_repo.page_open(
                after, BATCH
            )
            yield from page
            if len(page) < int(BATCH):
                return

            after = page[-1]
