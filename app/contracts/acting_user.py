"""An input made by one signed-in person, whose role may shape the answer."""

from typing import Protocol

from app.schemas.typings.users.prefixed_id import UserId


class ActingUserInputContract(Protocol):
    """A command or query that names the person making it (`user_id`)."""

    @property
    def user_id(self) -> UserId:
        raise NotImplementedError
