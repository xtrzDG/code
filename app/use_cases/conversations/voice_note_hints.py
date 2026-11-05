"""What helps the speech-to-text of a business's voice notes."""

import math
from typing import TypedDict

from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.media.constrained_integers import (
    AudioDurationSeconds,
    MediaByteCount,
)

# Voice notes are Opus at about 16 kbit/s (2 000 bytes a second); a file
# whose container does not tell its length is counted at that rate.
ESTIMATED_BYTES_PER_SECOND: int = 2000


class LanguageHints(TypedDict):
    language_hints: list[LanguageTag]
    keywords: list[BusinessName]


def read_language_hints(
    business_repo: BusinessRepoContract,
    assistant_version_repo: AssistantVersionRepoContract,
    business_id: BusinessId,
) -> LanguageHints:
    """
    The published assistant version's languages, its default first (the
    business's languages before a version is published), and the business
    name, which customers say and recognizers rarely know.
    """

    business: BusinessDocument | None = business_repo.get(business_id)
    if business is None:
        return LanguageHints(language_hints=[], keywords=[])

    version: AssistantVersionDocument | None = (
        None
        if business.published_assistant_version_id is None
        else assistant_version_repo.get(
            business.id, business.published_assistant_version_id
        )
    )
    languages: list[LanguageTag] = (
        [version.default_language, *version.languages]
        if version is not None
        else [business.default_language, *business.languages]
    )
    return LanguageHints(
        language_hints=list(dict.fromkeys(languages)),
        keywords=[business.name],
    )


def estimate_duration_seconds(byte_count: MediaByteCount) -> AudioDurationSeconds:
    return AudioDurationSeconds(
        max(1, math.ceil(int(byte_count) / ESTIMATED_BYTES_PER_SECOND))
    )
