"""Whether the business changed what its assistant knows since the live version."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument


def has_unapplied_changes(
    business: BusinessDocument,
    live_version: AssistantVersionDocument | None,
    profile: BusinessProfileDocument | None,
    knowledge_items: Sequence[KnowledgeItemDocument],
    resources: Sequence[ResourceDocument],
    schedule_exceptions: Sequence[ScheduleExceptionDocument],
) -> bool:
    """
    True when something the assistant is built from changed after the live
    version was built: the profile, a knowledge item, a resource, a special
    day, or the customer languages; and before the first go-live as soon as
    there is a profile to launch. A removed knowledge item leaves no trace,
    so it shows only with the next change.
    """

    if live_version is None:
        return profile is not None

    built_at: Microseconds = live_version.created_at
    return (
        (profile is not None and profile.updated_at > live_version.profile_revision)
        or any(item.updated_at > built_at for item in knowledge_items)
        or any(resource.updated_at > built_at for resource in resources)
        or any(exception.updated_at > built_at for exception in schedule_exceptions)
        or list(business.languages) != list(live_version.languages)
        or business.default_language != live_version.default_language
    )
