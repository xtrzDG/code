"""
What the world's processes sent to people (the platform bot, e-mail, SMS
of the staff providers): one JSON line per message part, appended by the
process that sent it, read by the test. Nothing leaves the machine.
"""

import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.contracts.facilitators import StaffNotificationSenderContract
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.outbound_messages import OutboundTemplate
from app.schemas.dto.messaging import EmailAttachment
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.strings import MessageText

SENDS_FILE_VARIABLE: str = "CHAOS_SENDS_FILE"


@dataclass(frozen=True)
class Sent:
    """One message part as a process sent it."""

    pid: int
    channel: str
    headline: str


class RecordingStaffSender(StaffNotificationSenderContract):
    """The staff providers of a game day's process: they write to a file."""

    def __init__(self, path: Path) -> None:
        self._path: Path = path

    def split(self, contact: ManagerContact, text: MessageText) -> list[MessageText]:
        del contact
        return [text]

    def send(
        self,
        contact: ManagerContact,
        text: MessageText,
        template: OutboundTemplate | None,
    ) -> ProviderMessageId | None:
        del template
        line = json.dumps(
            {
                "pid": os.getpid(),
                "channel": contact.channel.value,
                "headline": str(text).splitlines()[0],
            }
        )
        # One short append per part: whole lines between processes.
        with self._path.open("a", encoding="utf-8") as sends:
            sends.write(line + "\n")
        return None

    def send_with_files(
        self,
        contact: ManagerContact,
        text: MessageText,
        attachments: Sequence[EmailAttachment],
    ) -> None:
        del attachments
        self.send(contact, text, None)


def read_sends(path: Path) -> list[Sent]:
    if not path.exists():
        return []

    sends: list[Sent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        sends.append(
            Sent(
                pid=int(record["pid"]),
                channel=str(record["channel"]),
                headline=str(record["headline"]),
            )
        )
    return sends


def headlines(path: Path, containing: str) -> list[Sent]:
    """The parts whose first line names `containing` (an alert's title)."""

    return [sent for sent in read_sends(path) if containing in sent.headline]
