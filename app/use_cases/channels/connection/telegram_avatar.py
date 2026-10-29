"""
A Telegram bot's profile photo as a small data URL for the cabinet: its
address at Telegram holds the bot token, so the cabinet never gets it, and
only the bytes of a real JPEG, PNG or WebP image are passed on.
"""

import base64
import logging

from app.contracts.channel_clients import TelegramBotApiClientContract
from app.contracts.media_clients import TelegramFileClientContract
from app.schemas.dto.channels.provider_profiles import TelegramBotProfile
from app.schemas.dto.media import FetchedMedia, TelegramFileInfo
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.channels.constrained_strings import TelegramBotAvatarDataUrl
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.media.strings import ProviderMediaId

logger: logging.Logger = logging.getLogger(__name__)

# A 160 px profile photo is 5 to 15 KB; anything far bigger is not one.
MAX_AVATAR_BYTES: int = 96 * 1024
JPEG_SIGNATURE: bytes = b"\xff\xd8\xff"
PNG_SIGNATURE: bytes = b"\x89PNG\r\n\x1a\n"
RIFF_SIGNATURE: bytes = b"RIFF"
WEBP_SIGNATURE: bytes = b"WEBP"


def fetch_bot_avatar(
    telegram_client: TelegramBotApiClientContract,
    file_client: TelegramFileClientContract,
    bot_token: ChannelSecret,
    profile: TelegramBotProfile,
) -> TelegramBotAvatarDataUrl | None:
    """
    The bot's photo, or None without one: a photo that cannot be fetched
    never stops the check, the cabinet then shows the bot's initial.
    """

    if profile.bot_user_id is None:
        return None

    try:
        file_id: ProviderMediaId | None = telegram_client.get_profile_photo_file_id(
            bot_token, profile.bot_user_id
        )
        if file_id is None:
            return None

        info: TelegramFileInfo = file_client.get_file(bot_token, file_id)
        media: FetchedMedia = file_client.download_file(
            bot_token, info.file_path, MAX_AVATAR_BYTES
        )
    except ApplicationError as error:
        logger.info("No profile photo of the Telegram bot: %s", type(error).__name__)
        return None

    return as_data_url(media.content)


def as_data_url(content: bytes) -> TelegramBotAvatarDataUrl | None:
    """`data:image/...;base64,...` of an image's bytes; None for anything else."""

    media_type: str | None = detect_image_type(content)
    if media_type is None or len(content) > MAX_AVATAR_BYTES:
        return None

    encoded: str = base64.b64encode(content).decode("ascii")
    return TelegramBotAvatarDataUrl(f"data:{media_type};base64,{encoded}")


def detect_image_type(content: bytes) -> str | None:
    """The image type its first bytes declare (never the platform's header)."""

    if content.startswith(JPEG_SIGNATURE):
        return "image/jpeg"

    if content.startswith(PNG_SIGNATURE):
        return "image/png"

    if content.startswith(RIFF_SIGNATURE) and content[8:12] == WEBP_SIGNATURE:
        return "image/webp"

    return None
