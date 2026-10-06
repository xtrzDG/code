"""
The resident memory (RSS) of this process, for the worker's job log lines:
a job that grows the process by hundreds of megabytes shows up in the logs
before it takes the process down.
"""

import os
from pathlib import Path

from app.schemas.typings.platform.constrained_integers import ResidentMemoryBytes

# Linux: "size resident shared text lib data dt", in pages.
STATM_PATH: Path = Path("/proc/self/statm")
BYTES_PER_MEGABYTE: int = 1024 * 1024


def resident_memory_bytes(statm_path: Path = STATM_PATH) -> ResidentMemoryBytes | None:
    """
    The process's resident set now, in bytes; None where the kernel does
    not report it (not Linux) or the report cannot be read.
    """

    try:
        fields: list[str] = statm_path.read_text(encoding="ascii").split()
        resident_pages: int = int(fields[1])
        page_size: int = os.sysconf("SC_PAGE_SIZE")
    except OSError, ValueError, IndexError:
        return None

    return ResidentMemoryBytes(resident_pages * page_size)


def megabytes(memory: ResidentMemoryBytes | None) -> int | None:
    """Whole megabytes of a reading, for a log line (None stays None)."""

    return None if memory is None else int(memory) // BYTES_PER_MEGABYTE
