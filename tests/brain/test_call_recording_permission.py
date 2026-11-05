"""
Who may play a call recording (AUTHZ-03): owners always; staff only when
the owner allows it (`staff_may_play_recordings`, off by default). The
permission is read at every request, so a change takes effect at the next
playback, and a refused playback reads no audio and leaves no view in the
audit log.
"""

from tests.brain.brain_world import build_world
from tests.brain.scripted_turns import say, scripted
from tests.brain.test_call_recording_playback import AUDIO, RECORDING_PATH, Playback


def playback_with_recording(staff_may_play: bool) -> Playback:
    playback = Playback(build_world(scripted(say("Hello!"))), staff_may_play)
    playback.storage.recording_storage.recordings[RECORDING_PATH] = AUDIO
    return playback


def test_by_default_staff_may_not_play_a_recording() -> None:
    playback = playback_with_recording(staff_may_play=False)
    call = playback.add_call()

    by_staff = playback.play(call.id, token="staff")
    reads_after_staff = list(playback.storage.recording_storage.reads)
    by_owner = playback.play(call.id, token="owner")

    assert by_staff.status_code == 403
    assert by_staff.json()["error"] == "access_denied"
    assert reads_after_staff == []
    assert by_owner.status_code == 200, by_owner.text
    assert by_owner.content == AUDIO
    assert [entry.actor_id for entry in playback.recording_views()] == [
        playback.world.owner_id
    ]


def test_staff_play_once_the_owner_allows_it_and_stop_when_taken_back() -> None:
    playback = playback_with_recording(staff_may_play=False)
    call = playback.add_call()

    before = playback.play(call.id, token="staff")
    playback.allow_staff(True)
    allowed = playback.play(call.id, token="staff")
    playback.allow_staff(False)
    taken_back = playback.play(call.id, token="staff", byte_range="bytes=4-")

    assert before.status_code == 403
    assert allowed.status_code == 200, allowed.text
    assert allowed.content == AUDIO
    # A later part of a playback is checked again, like the first one.
    assert taken_back.status_code == 403
    assert [entry.actor_id for entry in playback.recording_views()] == [
        playback.world.staff_id
    ]


def test_a_stranger_still_finds_nothing_either_way() -> None:
    for staff_may_play in (False, True):
        playback = playback_with_recording(staff_may_play)
        call = playback.add_call()

        response = playback.play(call.id, token="stranger")

        assert response.status_code == 404
        assert playback.storage.recording_storage.reads == []
