"""
How long a voice note is, measured on the server from the file itself.

For the formats browsers record (WebM and Ogg with Opus, MP4 with AAC or
Opus) the readers count the audio a decoder plays as well as every
duration the container claims, and take the longest: a forged header
does not make a long recording short. Other formats (WAV, a platform's
Ogg) only have their container's word (`audio_duration`).
"""

from collections.abc import Callable

from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.utilities.media.audio_duration import read_audio_duration_seconds
from app.utilities.media.mp4_audio import read_mp4_audio_seconds
from app.utilities.media.ogg_opus_audio import read_ogg_opus_seconds
from app.utilities.media.webm_audio import read_webm_audio_seconds

VOICE_NOTE_READERS: dict[MessageMediaType, Callable[[bytes], int | None]] = {
    MessageMediaType("audio/webm"): read_webm_audio_seconds,
    MessageMediaType("audio/ogg"): read_ogg_opus_seconds,
    MessageMediaType("audio/mp4"): read_mp4_audio_seconds,
}


def measure_voice_note(content: bytes, media_type: MessageMediaType) -> int | None:
    """
    Whole seconds of a browser recording with only audio in it, the longest
    of what its container claims and what its packets or frames play; None
    for another format, video, another codec, or a structure that does not
    add up.
    """

    reader: Callable[[bytes], int | None] | None = VOICE_NOTE_READERS.get(media_type)
    return None if reader is None else reader(content)


def measure_audio_seconds(content: bytes, media_type: MessageMediaType) -> int | None:
    """
    The longest length any reader finds in a stored audio file (whole
    seconds); None when none of them can tell.
    """

    readings: list[int] = [
        seconds
        for seconds in (
            read_audio_duration_seconds(content),
            measure_voice_note(content, media_type),
        )
        if seconds is not None
    ]
    return max(readings, default=None)
