"""
Watchdog of one throwaway test Postgres server:

    python tests/storage/postgres_watchdog.py <owner pid> <pg_ctl> <root> [<uid> <gid>]

`ThrowawayPostgresServer.start` runs it as a child of the test process, in
its own session so that killing the test's process group spares it. While
its parent is still `<owner pid>` and `<root>` exists it only waits. When the
owner dies without stopping its server (SIGKILL, an out-of-memory kill, a
timed-out run) the watchdog is re-parented: it stops the server as a crash
does (`pg_ctl stop --mode immediate`, as `<uid>`/`<gid>` when given) and
deletes `<root>`, so no orphaned server keeps its memory and disk. A normal
`stop()` ends the watchdog first.

Standard library only: it must start fast and import nothing of the app.
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

POLL_SECONDS: float = 0.5
STOP_TIMEOUT_SECONDS: int = 60
OWNER_ONLY_ARGUMENT_COUNT: int = 4
RUN_AS_ARGUMENT_COUNT: int = 6


def owner_is_alive(owner_pid: int) -> bool:
    """The owner is alive while it is still this process's parent."""

    return os.getppid() == owner_pid


def stop_server(pg_ctl: str, root: Path, run_as: tuple[int, int] | None) -> None:
    command: list[str] = [
        pg_ctl,
        "--pgdata",
        str(root / "data"),
        "--mode",
        "immediate",
        "--wait",
        "stop",
    ]
    if run_as is None:
        subprocess.run(
            command,
            capture_output=True,
            check=False,
            timeout=STOP_TIMEOUT_SECONDS,
        )
        return

    user_id, group_id = run_as
    subprocess.run(
        command,
        capture_output=True,
        check=False,
        timeout=STOP_TIMEOUT_SECONDS,
        user=user_id,
        group=group_id,
        extra_groups=[],
        cwd=str(root),
    )


def watch(
    owner_pid: int, pg_ctl: str, root: Path, run_as: tuple[int, int] | None
) -> None:
    while owner_is_alive(owner_pid) and root.is_dir():
        time.sleep(POLL_SECONDS)

    if not root.is_dir():
        return

    try:
        stop_server(pg_ctl, root, run_as)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main(arguments: list[str]) -> None:
    if len(arguments) not in (OWNER_ONLY_ARGUMENT_COUNT, RUN_AS_ARGUMENT_COUNT):
        raise SystemExit(__doc__)

    run_as: tuple[int, int] | None = (
        (int(arguments[4]), int(arguments[5]))
        if len(arguments) == RUN_AS_ARGUMENT_COUNT
        else None
    )
    watch(int(arguments[1]), arguments[2], Path(arguments[3]), run_as)


if __name__ == "__main__":
    main(sys.argv)
