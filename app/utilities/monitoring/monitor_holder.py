"""The name of this process as a holder of the pipeline watchdog's lease."""

import os
import re
import socket

from app.schemas.typings.monitoring.constrained_strings import MonitorHolderName

UNSAFE_CHARACTERS: re.Pattern[str] = re.compile(r"[^A-Za-z0-9.-]+")
HOST_NAME_LIMIT: int = 200


def this_process_holder() -> MonitorHolderName:
    """ "<host>:<pid>": unique among the processes sharing one database."""

    host: str = UNSAFE_CHARACTERS.sub("-", socket.gethostname()).strip("-.")
    return MonitorHolderName(f"{host[:HOST_NAME_LIMIT] or 'host'}:{os.getpid()}")
