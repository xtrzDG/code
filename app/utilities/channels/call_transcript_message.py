"""
The transcript a caller asked for during a call (send_call_transcript,
ACC-03), as the text message that brings it to them after the call.

A caller who cannot hear well, or wants the details in writing, gets what
was said: their lines and the business's, in call order. A call whose
caller declined the recording keeps no e-mail, account, card or phone
numbers here either (`redact_call_text`), like its stored transcript. A
long call is cut at whole lines so the message fits every messenger.
"""

from collections.abc import Sequence

from app.schemas.constants.conversations import MessageAuthor
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.voice_webhooks import FinishedCallTranscriptLine
from app.utilities.calls.call_transcript_redaction import redact_call_text
from app.utilities.localization.localized_texts import build_localized_text

# Telegram and WhatsApp carry 4,096 characters; the links of the call and
# the header share the rest.
TRANSCRIPT_MAX_CHARACTERS: int = 3000
SHORTENED_MARK: str = "…"
SPOKEN_AUTHORS: frozenset[MessageAuthor] = frozenset(
    {MessageAuthor.CUSTOMER, MessageAuthor.ASSISTANT, MessageAuthor.STAFF}
)

# The first line of the transcript.
CALL_TRANSCRIPT_TEXT: LocalizedText = build_localized_text(
    en="{business}: the transcript of your call.",
    ru="{business}: расшифровка вашего звонка.",
    ka="{business}: თქვენი ზარის ჩანაწერი ტექსტად.",
    uk="{business}: розшифровка вашого дзвінка.",
    hy="{business}․ ձեր զանգի տեքստը։",
    he="{business}: תמליל השיחה שלך.",
    ar="{business}: نص مكالمتك.",
    tr="{business}: aramanızın dökümü.",
    pl="{business}: zapis Twojej rozmowy.",
    de="{business}: das Transkript Ihres Anrufs.",
    es="{business}: la transcripción de tu llamada.",
    fr="{business} : la transcription de votre appel.",
    it="{business}: la trascrizione della tua chiamata.",
    pt="{business}: a transcrição da sua ligação.",
    kk="{business}: қоңырауыңыздың мәтіні.",
)
# How the caller's own lines start.
CALLER_LABEL_TEXT: LocalizedText = build_localized_text(
    en="You",
    ru="Вы",
    ka="თქვენ",
    uk="Ви",
    hy="Դուք",
    he="את/ה",
    ar="أنت",
    tr="Siz",
    pl="Ty",
    de="Sie",
    es="Tú",
    fr="Vous",
    it="Tu",
    pt="Você",
    kk="Сіз",
)


def build_call_transcript_text(
    header: str,
    caller_label: str,
    business_name: str,
    transcript: Sequence[FinishedCallTranscriptLine],
    is_recording_declined: bool,
) -> str | None:
    """
    The header, then "<caller label>: ..." and "<business>: ..." lines (a
    colleague who took the call speaks for the business); None for a call
    nobody spoke in.
    """

    lines: list[str] = []
    for line in transcript:
        if line.author not in SPOKEN_AUTHORS or not str(line.text).strip():
            continue

        text: str = str(line.text).strip()
        spoken: str = redact_call_text(text) if is_recording_declined else text
        speaker: str = (
            caller_label if line.author is MessageAuthor.CUSTOMER else business_name
        )
        lines.append(f"{speaker}: {spoken}")

    if not lines:
        return None

    return "\n".join([header, *shorten_lines(lines)])


def shorten_lines(lines: Sequence[str]) -> list[str]:
    """The first lines that fit TRANSCRIPT_MAX_CHARACTERS, marked when cut."""

    kept: list[str] = []
    used: int = 0
    for line in lines:
        used += len(line) + 1
        if used > TRANSCRIPT_MAX_CHARACTERS:
            return (
                [*kept, SHORTENED_MARK]
                if kept
                else [line[:TRANSCRIPT_MAX_CHARACTERS] + SHORTENED_MARK]
            )

        kept.append(line)

    return kept
