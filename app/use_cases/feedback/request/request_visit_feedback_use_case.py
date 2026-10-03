"""Background job: ask customers how their visit went."""

import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.repositories.feedback_repositories import (
    FeedbackRequestRepoContract,
    ReviewSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.feedback import ReviewSettingsDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.feedback.prefixed_id import FeedbackRequestId
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.feedback.request.feedback_asking import FeedbackAsker
from app.use_cases.feedback.request.feedback_routes import FeedbackRouting
from app.use_cases.feedback.request.feedback_sending import FeedbackSender
from app.use_cases.feedback.request.visit_windows import (
    asks_for_feedback,
    due_visits_window,
    is_visit_to_ask_about,
)
from app.utilities.feedback.feedback_keys import feedback_request_id_of

LOGGER: logging.Logger = logging.getLogger(__name__)


class RequestVisitFeedbackUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Periodic job: every business with feedback on asks each customer whose
    visit ended `delay_minutes` ago how it went (1 to 5), once per visit,
    in the customer's messenger and language, through the outbox.

    A visit is a booking that was completed, or is still confirmed after
    its end (a no-show or a cancellation is never asked about), and not a
    test. Visits that ended more than six hours before they became due are
    left alone (the job was down; a late question is worse than none). A
    customer who opted out of unrequested messages, cannot be reached in a
    connected messenger, can be reached only where the 24-hour window is
    closed without an approved template, was already asked today, or hits
    a daily cap is not asked; the request keeps why (SKIPPED). Businesses
    that are not live (paused, still setting up) ask nobody.
    """

    def __init__(
        self,
        review_settings_repo: ReviewSettingsRepoContract,
        feedback_request_repo: FeedbackRequestRepoContract,
        business_repo: BusinessRepoContract,
        booking_repo: BookingRepoContract,
        contact_repo: ContactRepoContract,
        channel_repo: ChannelRepoContract,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        outbound_message_repo: OutboundMessageRepoContract,
        job_queue: JobQueueFacilitatorContract,
        rate_limits: RequestRateLimitRegistryContract,
        text_resolver: LocalizedTextResolverContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._review_settings_repo: ReviewSettingsRepoContract = review_settings_repo
        self._feedback_request_repo: FeedbackRequestRepoContract = feedback_request_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._asker: FeedbackAsker = FeedbackAsker(
            feedback_request_repo=feedback_request_repo,
            contact_repo=contact_repo,
            rate_limits=rate_limits,
            routing=FeedbackRouting(channel_repo, conversation_repo, message_repo),
            sender=FeedbackSender(
                outbound_message_repo,
                job_queue,
                conversation_repo,
                message_repo,
                text_resolver,
            ),
            live_events=live_events,
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        asked: int = 0
        for settings in self._review_settings_repo.list_enabled():
            business: BusinessDocument | None = self._business_repo.get(
                settings.business_id
            )
            if business is None or not asks_for_feedback(business, settings):
                continue

            asked += self._ask_business(business, settings)

        return JobReport(processed_count=ProcessedItemCount(asked))

    def _ask_business(
        self, business: BusinessDocument, settings: ReviewSettingsDocument
    ) -> int:
        now: Microseconds = self._wall_clock.now_unix()
        ended_after, ended_by = due_visits_window(settings, now)
        visits: list[BookingDocument] = [
            booking
            for booking in self._booking_repo.list_ending_between(
                business.id, ended_after, ended_by
            )
            if is_visit_to_ask_about(booking)
        ]
        if not visits:
            return 0

        decided: set[FeedbackRequestId] = set(
            self._feedback_request_repo.get_many(
                business.id,
                [feedback_request_id_of(business.id, visit.id) for visit in visits],
            )
        )
        asked: int = 0
        for visit in visits:
            if feedback_request_id_of(business.id, visit.id) in decided:
                continue

            if self._asker.ask(business, settings, visit, now):
                asked += 1

        if asked:
            LOGGER.info(
                "Asked %d customers of %s about their visit.", asked, business.id
            )

        return asked
