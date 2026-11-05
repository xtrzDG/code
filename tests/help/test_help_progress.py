"""What a person has seen: coach marks once, the changelog only forward."""

import threading

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.help_progress_repository import HelpProgressRepository
from app.schemas.domain.help_progress import HelpProgressDocument
from app.schemas.dto.help_progress import (
    ChangelogReadBody,
    ChangelogReadCommand,
    CoachMarkSeenCommand,
    HelpProgressQuery,
)
from app.schemas.typings.help.constrained_strings import (
    ChangelogEntryKey,
    CoachMarkKey,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.help.get_help_progress_use_case import GetHelpProgressUseCase
from app.use_cases.help.help_progress_views import MAX_SEEN_COACH_MARKS
from app.use_cases.help.mark_coach_mark_seen_use_case import (
    MarkCoachMarkSeenUseCase,
)
from app.use_cases.help.read_changelog_use_case import ReadChangelogUseCase
from app.use_cases.help.reset_coach_marks_use_case import ResetCoachMarksUseCase
from tests.help.help_fixtures import Clock

USER = UserId()
OTHER = UserId()


class ProgressWorld:
    def __init__(self) -> None:
        self.clock = Clock()
        self.collection = InMemoryDocumentCollectionAdapter[HelpProgressDocument](
            HelpProgressDocument
        )
        self.repo = HelpProgressRepository(self.collection)
        self.get = GetHelpProgressUseCase(self.repo)
        self.mark = MarkCoachMarkSeenUseCase(self.repo, self.clock.wall_clock)
        self.reset = ResetCoachMarksUseCase(self.repo, self.clock.wall_clock)
        self.read = ReadChangelogUseCase(self.repo, self.clock.wall_clock)

    def seen(self, key: str, user: UserId = USER) -> list[str]:
        view = self.mark.run(CoachMarkSeenCommand(user_id=user, key=CoachMarkKey(key)))
        return [str(mark) for mark in view.seen_coach_marks]

    def read_up_to(self, key: str) -> str | None:
        view = self.read.run(
            ChangelogReadCommand(
                user_id=USER, body=ChangelogReadBody(read_key=ChangelogEntryKey(key))
            )
        )
        return None if view.changelog_read_key is None else str(view.changelog_read_key)


def test_a_new_person_has_seen_nothing() -> None:
    world = ProgressWorld()

    view = world.get.run(HelpProgressQuery(user_id=USER))

    assert view.seen_coach_marks == []
    assert view.changelog_read_key is None


def test_a_coach_mark_is_remembered_once_and_per_person() -> None:
    world = ProgressWorld()

    assert world.seen("inbox") == ["inbox"]
    assert world.seen("inbox") == ["inbox"]
    assert world.seen("channels") == ["inbox", "channels"]
    assert world.seen("inbox", OTHER) == ["inbox"]
    stored = world.repo.find(USER)
    assert stored is not None and stored.updated_at == world.clock.now


def test_only_the_newest_coach_marks_are_kept() -> None:
    world = ProgressWorld()
    for index in range(MAX_SEEN_COACH_MARKS + 3):
        world.seen(f"hint_{index}")

    seen = world.get.run(HelpProgressQuery(user_id=USER)).seen_coach_marks

    assert len(seen) == MAX_SEEN_COACH_MARKS
    assert seen[0] == "hint_3"


def test_show_the_tips_again_forgets_the_marks_but_not_the_changelog() -> None:
    world = ProgressWorld()
    world.seen("inbox")
    world.read_up_to("2026-10-04-help-center")

    world.reset.run(HelpProgressQuery(user_id=USER))
    world.reset.run(HelpProgressQuery(user_id=OTHER))

    view = world.get.run(HelpProgressQuery(user_id=USER))
    assert view.seen_coach_marks == []
    assert view.changelog_read_key == "2026-10-04-help-center"
    assert world.get.run(HelpProgressQuery(user_id=OTHER)).seen_coach_marks == []


def test_the_changelog_only_moves_forward() -> None:
    world = ProgressWorld()

    assert world.read_up_to("2026-09-20-reports") == "2026-09-20-reports"
    assert world.read_up_to("2026-10-04-help-center") == "2026-10-04-help-center"
    assert world.read_up_to("2026-09-20-reports") == "2026-10-04-help-center"


def test_two_tabs_closing_different_hints_both_count() -> None:
    world = ProgressWorld()
    keys = [f"hint_{index}" for index in range(12)]
    threads = [threading.Thread(target=world.seen, args=(key,)) for key in keys]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    seen = world.get.run(HelpProgressQuery(user_id=USER)).seen_coach_marks

    assert sorted(seen) == sorted(keys)
