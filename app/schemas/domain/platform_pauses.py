from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.schemas.typings.spend.booleans import IsPlatformPaused
from app.schemas.typings.spend.constrained_strings import PlatformPauseReason
from app.schemas.typings.users.prefixed_id import UserId


class PlatformPauseDocument(BaseDocument):
    """
    The platform's global pause (a platform collection holding one row,
    stored under `platform`, migration 1230): whether every assistant
    hands its customers to the team (`is_paused`), and who paused or
    resumed them last, when and why. While paused, the spend guard holds
    every model turn back (customers hear in their language that a
    colleague takes over) and the voice platform refuses calls, so the
    carrier forwards them to the business's staff phone. Resuming restores
    everything at once; the business's own settings never change.
    """

    is_paused: IsPlatformPaused
    reason: PlatformPauseReason
    changed_by: UserId
    changed_at: Microseconds
