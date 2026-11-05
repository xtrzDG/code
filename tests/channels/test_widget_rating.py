"""
The thumbs under the website chat's answers: the visitor rates their own
chat only (an answer of theirs, or their latest one), a bad rating joins
the owner's "Answers worth improving", the team's rating always stands,
and ratings are limited per visitor.
"""

import threading

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelStatus
from app.schemas.constants.conversations import (
    ConversationRating,
    ConversationRatingBy,
    ConversationRatingReason,
)
from app.schemas.dto.conversation_feed.answer_reviews import ConversationRatingChange
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.users.prefixed_id import UserId
from tests.channels.test_widget import SESSION_KEY, enable_widget
from tests.channels.widget_rating_bed import WidgetRatingBed
from tests.channels.widget_upload_bed import OTHER_VISITOR

PAGE: KeysetSlice = KeysetSlice(limit=KeysetReadLimit(10))


def team_rating(bed: WidgetRatingBed, rating: ConversationRating | None) -> None:
    bed.testbed.conversation_repo.set_rating(
        bed.business.id,
        bed.conversation().id,
        ConversationRatingChange(
            rating=rating,
            rated_by=UserId(),
            at=bed.testbed.wall_clock.now_unix(),
        ),
    )


class TestTheVisitorsRating:
    def test_a_thumbs_up_is_the_customers_rating(self) -> None:
        bed = WidgetRatingBed()
        bed.chat("Do you have a table for two?")

        response = bed.rate("good")

        assert response.status_code == 200, response.text
        assert response.json() == {"rating": "good", "reason": None}
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        stored = bed.conversation()
        assert stored.rating is ConversationRating.GOOD
        assert stored.rating_by is ConversationRatingBy.CUSTOMER
        assert stored.rated_by is None
        assert stored.rated_at == bed.testbed.wall_clock.now_unix()
        assert stored.awaits_improvement is False

    def test_a_thumbs_down_joins_the_answers_worth_improving(self) -> None:
        bed = WidgetRatingBed()
        bed.chat("Is there parking?")
        bed.chat("And for a van?")
        latest = bed.answers()[-1]

        response = bed.rate("bad", reason="wrong_info")

        assert response.json() == {"rating": "bad", "reason": "wrong_info"}
        stored = bed.conversation()
        assert stored.rating_by is ConversationRatingBy.CUSTOMER
        assert stored.rating_reason is ConversationRatingReason.WRONG_INFO
        assert stored.rated_message_id == latest.id
        repo = bed.testbed.conversation_repo
        [waiting] = repo.page_awaiting_improvement(bed.business.id, PAGE)
        assert waiting.id == stored.id
        assert int(repo.count_awaiting_improvement(bed.business.id)) == 1

    def test_the_answer_named_is_the_one_rated(self) -> None:
        bed = WidgetRatingBed()
        bed.chat("Is there parking?")
        bed.chat("Thanks!")
        first = bed.answers()[0]

        response = bed.rate("bad", message_id=first.id)

        assert response.status_code == 200
        assert bed.conversation().rated_message_id == first.id

    def test_a_visitor_changes_their_mind(self) -> None:
        bed = WidgetRatingBed()
        bed.chat("Is there parking?")
        bed.rate("bad", reason="tone")
        bed.testbed.clock.advance(5)

        assert bed.rate("good").status_code == 200

        stored = bed.conversation()
        assert stored.rating is ConversationRating.GOOD
        assert (stored.rating_reason, stored.rated_message_id) == (None, None)
        assert stored.awaits_improvement is False

    def test_only_a_thumbs_down_says_what_was_wrong(self) -> None:
        bed = WidgetRatingBed()
        bed.chat("Hi")

        good_with_reason = bed.rate("good", reason="tone")
        unknown_reason = bed.rate("bad", reason="rude")
        unknown_rating = bed.rate("meh")

        assert good_with_reason.status_code == 422
        assert unknown_reason.status_code == 422
        assert unknown_rating.status_code == 422
        assert bed.conversation().rating is None


class TestTheTeamsVerdictStands:
    def test_a_visitor_does_not_override_the_team(self) -> None:
        bed = WidgetRatingBed()
        bed.chat("Hi")
        team_rating(bed, ConversationRating.GOOD)

        response = bed.rate("bad", reason="wrong_info")

        # The visitor is not told whose rating stands.
        assert response.status_code == 200
        stored = bed.conversation()
        assert stored.rating is ConversationRating.GOOD
        assert stored.rating_by is ConversationRatingBy.TEAM
        assert stored.awaits_improvement is False

    def test_the_team_overrides_a_visitor_and_clearing_clears_who(self) -> None:
        bed = WidgetRatingBed()
        bed.chat("Hi")
        bed.rate("bad")

        team_rating(bed, ConversationRating.GOOD)
        rated = bed.conversation()
        team_rating(bed, None)

        assert rated.rating_by is ConversationRatingBy.TEAM
        assert rated.rated_by is not None
        assert bed.conversation().rating_by is None

    def test_a_visitor_racing_the_team_never_wins(self) -> None:
        bed = WidgetRatingBed()
        bed.chat("Hi")
        start = threading.Barrier(2)
        codes: list[int] = []
        lock = threading.Lock()

        def visitor() -> None:
            start.wait()
            code = bed.rate("bad").status_code
            with lock:
                codes.append(code)

        def team() -> None:
            start.wait()
            team_rating(bed, ConversationRating.GOOD)

        threads = [threading.Thread(target=visitor), threading.Thread(target=team)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert codes == [200]
        stored = bed.conversation()
        assert (stored.rating, stored.rating_by) == (
            ConversationRating.GOOD,
            ConversationRatingBy.TEAM,
        )


class TestNoOtherConversation:
    def test_another_visitors_answer_is_not_found(self) -> None:
        bed = WidgetRatingBed()
        bed.chat("Hi")
        bed.chat("Hello", session_key=OTHER_VISITOR)
        theirs = bed.answers(OTHER_VISITOR)[0]

        response = bed.rate("bad", message_id=theirs.id)

        assert response.status_code == 404
        assert bed.conversation(OTHER_VISITOR).rating is None
        assert bed.conversation().rating is None

    def test_my_own_words_or_an_unknown_answer_are_not_found(self) -> None:
        bed = WidgetRatingBed()
        bed.chat("Hi")
        [mine] = [message for message in bed.messages() if message not in bed.answers()]

        own_words = bed.rate("bad", message_id=mine.id)
        unknown = bed.rate("bad", message_id=MessageId())

        assert (own_words.status_code, unknown.status_code) == (404, 404)
        assert bed.conversation().rating is None

    def test_an_answer_of_another_business_is_not_found(self) -> None:
        bed = WidgetRatingBed()
        bed.chat("Hi")
        other_business = enable_widget(bed.testbed)
        mine = bed.answers()[0]

        response = bed.rate("bad", message_id=mine.id, business_id=other_business.id)

        assert response.status_code == 404
        assert bed.conversation().rating is None

    def test_nothing_to_rate_before_the_first_message(self) -> None:
        bed = WidgetRatingBed()

        assert bed.rate("good").status_code == 404

    def test_a_chat_switched_off_takes_no_rating(self) -> None:
        bed = WidgetRatingBed()
        bed.chat("Hi")
        [channel] = bed.testbed.channel_repo.list_by_business(bed.business.id)
        channel.status = ChannelStatus.DISABLED
        bed.testbed.channel_repo.save(channel)

        assert bed.rate("good").status_code == 404
        assert bed.rate("good", business_id="business_x").status_code == 404
        assert bed.conversation().rating is None


class TestLimitsAndInvitations:
    def test_ratings_are_limited_per_visitor(self) -> None:
        bed = WidgetRatingBed()
        bed.chat("Hi")
        bed.chat("Hello", session_key=OTHER_VISITOR)

        codes = [bed.rate("good").status_code for _ in range(6)]
        limited = bed.rate("bad")
        other = bed.rate("good", session_key=OTHER_VISITOR)

        assert codes == [200] * 6
        assert limited.status_code == 429
        assert int(limited.headers["Retry-After"]) > 0
        assert other.status_code == 200
        assert bed.conversation().rating is ConversationRating.GOOD

    def test_the_preflight_allows_the_widget(self) -> None:
        bed = WidgetRatingBed()

        response = bed.client.options(f"/v1/widget/{bed.business.id}/rating")

        assert response.status_code == 204
        assert response.headers["Access-Control-Allow-Origin"] == "*"

    def test_a_booking_or_a_lead_invites_a_rating_under_its_answer(self) -> None:
        bed = WidgetRatingBed()
        bed.chat("A table for two on Friday?")
        booked = bed.store_booking_answer(AssistantToolName.CREATE_BOOKING)
        lead = bed.store_booking_answer(AssistantToolName.CREATE_LEAD)
        other = bed.store_booking_answer(AssistantToolName.CHECK_AVAILABILITY)

        page = bed.client.get(
            f"/v1/widget/{bed.business.id}/messages",
            headers={"X-Widget-Session-Key": SESSION_KEY},
            params={"after": str(bed.messages()[0].id)},
        ).json()

        invited = {item["id"]: item["invites_rating"] for item in page["items"]}
        assert invited[str(booked.id)] is True
        assert invited[str(lead.id)] is True
        assert invited[str(other.id)] is False
        assert invited[str(bed.answers()[0].id)] is False
