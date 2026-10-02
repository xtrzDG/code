"""The account and credential a channel was connected with."""

from collections.abc import Callable
from typing import NamedTuple

from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    ChannelSecret,
)

type AccountCheck = Callable[[ChannelKind, ChannelExternalId], None]


class ChannelConnection(NamedTuple):
    """Account and credential a channel was connected with (technical pair)."""

    external_id: ChannelExternalId | None
    secret: ChannelSecret | None
