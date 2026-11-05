"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class DataTaskErrorText(BaseConstrainedTypedString):
    """
    Why the last batch of a data task failed, one English line from the
    storage (an error class and its message, never document content).

    Example:
        error = DataTaskErrorText("ExternalServiceError: a row stayed locked")
    """

    min_length = 1
    max_length = 500


class DataTaskKey(BaseConstrainedTypedString):
    """
    The name of one post-deploy data task: its kind, the collection and,
    for a lookup column, the field (`app/registries/maintenance/`). Its
    state document is stored under this key.

    Example:
        key = DataTaskKey("backfill_lookup:contacts.last_seen_at")
    """

    min_length = 20
    max_length = 140
    pattern = (
        r"^(migrate_documents:[a-z][a-z0-9_]{1,62}"
        r"|backfill_lookup:[a-z][a-z0-9_]{1,62}\.[a-z][a-z0-9_]{0,58})\Z"
    )


class DataTaskPosition(BaseConstrainedTypedString):
    """
    Where a data task's keyset walk stopped: opaque text that only the
    storage adapter of the task's kind writes and reads back (a document
    key, or a creation time and row number).

    Example:
        position = DataTaskPosition("contact_3f2a...")
    """

    min_length = 1
    max_length = 400


class GatedEnumValue(BaseConstrainedTypedString):
    """
    One value of a stored enum field that the current release knows but
    must not write yet (a release gate, docs/operations/deploys.md).

    Example:
        value = GatedEnumValue("paused")
    """

    min_length = 1
    max_length = 100


class ReleaseGateName(BaseConstrainedTypedString):
    """
    The name of a release gate: the switch, flipped in a later release,
    that lets the code write the enum values it covers.

    Example:
        gate = ReleaseGateName("subscription_pause")
    """

    min_length = 2
    max_length = 63
    pattern = r"^[a-z][a-z0-9_]{1,62}\Z"


class StoredEnumPath(BaseConstrainedTypedString):
    """
    Where an enum field sits in a stored document: field names joined by
    dots, `[]` after a list and `{}` after a mapping (its values).

    Example:
        path = StoredEnumPath("results[].scenario.kind")
    """

    min_length = 1
    max_length = 300
    pattern = r"^[a-z_][a-z0-9_]*(\[\]|\{\})*(\.[a-z_][a-z0-9_]*(\[\]|\{\})*)*\Z"


# Keep abc order for all non example types, if possible.
