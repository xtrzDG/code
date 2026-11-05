"""
Where a customer came from, read back from what their channel carried
(the codes the share links put there, `channel_links.py`):

- the hosted page and the website widget: `?src=<tag>` of the page (the
  widget sends it with the visitor's message);
- Telegram: `t.me/<bot>?start=src_<tag>` makes the customer's first
  message "/start src_<tag>" (Telegram shows them only "/start");
- WhatsApp: `wa.me/<number>?text=<greeting> (#<tag>)` puts the code at the
  end of the greeting the customer sends;
- Messenger and Instagram: `?ref=<tag>` of m.me and ig.me, and the ads a
  customer clicked, arrive as Meta's `referral` object;
- a phone call: the number the caller dialled (`tel-<digits>`), so each
  line of a business (one per campaign) is told apart.

The tags are cut to `AcquisitionSourceTag`; whatever cannot be read is no
source (a message is never refused for it).
"""

import re

from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.sharing.constrained_strings import (
    AcquisitionSourceTag,
    ShareSourceTag,
)
from app.utilities.channels.json_values import (
    JsonObject,
    read_identifier,
    read_text,
)

MAX_TAG_LENGTH: int = 32
# Anything but a tag's own characters becomes one dash.
NOT_TAG_CHARACTERS: re.Pattern[str] = re.compile(r"[^a-z0-9_-]+")
TAG_EDGE_CHARACTERS: str = "-_"
START_COMMAND: str = "/start"
START_SOURCE_PREFIX: str = "src_"
# "(#qr-tables)" at the end of a message: a greeting from a wa.me link.
GREETING_CODE: re.Pattern[str] = re.compile(
    r"\s*\(#([A-Za-z0-9][A-Za-z0-9_-]{0,31})\)\s*$"
)
AD_PREFIX: str = "ad-"
CALLED_NUMBER_PREFIX: str = "tel-"
ADS_SOURCE: str = "ADS"
AD_SOURCE_TYPE: str = "ad"
ANY_AD: AcquisitionSourceTag = AcquisitionSourceTag("ad")


def normalize_source(text: str | None) -> AcquisitionSourceTag | None:
    """Lower case, runs of other characters as one dash, at most 32; or None."""

    if text is None:
        return None

    tag: str = NOT_TAG_CHARACTERS.sub("-", text.strip().lower())
    tag = tag.strip(TAG_EDGE_CHARACTERS)[:MAX_TAG_LENGTH].rstrip(TAG_EDGE_CHARACTERS)
    return AcquisitionSourceTag(tag) if tag else None


def read_start_payload(text: str) -> tuple[AcquisitionSourceTag | None, str]:
    """
    The source of Telegram's "/start src_<tag>" (also "/start@bot ...") and
    the text without it ("/start"); any other text is returned as it is.
    """

    command, _, argument = text.strip().partition(" ")
    if command.split("@", 1)[0] != START_COMMAND:
        return None, text

    payload: str = argument.strip()
    if not payload.startswith(START_SOURCE_PREFIX):
        return None, text

    return normalize_source(payload.removeprefix(START_SOURCE_PREFIX)), command


def read_greeting_code(text: str) -> tuple[AcquisitionSourceTag | None, str]:
    """
    The source of a "(#<tag>)" code at the end of a message (the greeting of
    a tagged wa.me link) and the text without it; a message that is only
    the code keeps its text.
    """

    match: re.Match[str] | None = GREETING_CODE.search(text)
    if match is None:
        return None, text

    rest: str = text[: match.start()].rstrip()
    return normalize_source(match.group(1)), rest or text


def read_referral_source(referral: JsonObject | None) -> AcquisitionSourceTag | None:
    """
    The source of Meta's `referral` object: its `ref` (an m.me or ig.me link
    tag), else the ad a customer clicked (`ad_id`, or WhatsApp's
    `source_id` of `source_type` "ad") as `ad-<id>`, else `ad` for an ad
    without an id.
    """

    if referral is None:
        return None

    tagged: AcquisitionSourceTag | None = normalize_source(read_text(referral, "ref"))
    if tagged is not None:
        return tagged

    ad_id: str | None = read_identifier(referral, "ad_id")
    if ad_id is None and read_text(referral, "source_type") == AD_SOURCE_TYPE:
        ad_id = read_identifier(referral, "source_id")

    if ad_id is not None:
        return normalize_source(AD_PREFIX + ad_id)

    is_ad: bool = (
        read_text(referral, "source") == ADS_SOURCE
        or read_text(referral, "source_type") == AD_SOURCE_TYPE
    )
    return ANY_AD if is_ad else None


def called_number_source(
    number: E164PhoneNumber | None,
) -> AcquisitionSourceTag | None:
    """The line a caller dialled, as `tel-<digits>`; None when not known."""

    if number is None:
        return None

    return normalize_source(CALLED_NUMBER_PREFIX + str(number).removeprefix("+"))


def start_parameter(source: ShareSourceTag) -> str:
    """Telegram's `start` parameter of a tagged link (`src_<tag>`)."""

    return START_SOURCE_PREFIX + str(source)


def greeting_with_code(greeting: str, source: ShareSourceTag) -> str:
    """The prefilled text of a tagged wa.me link: "<greeting> (#<tag>)"."""

    return f"{greeting} (#{source})"
