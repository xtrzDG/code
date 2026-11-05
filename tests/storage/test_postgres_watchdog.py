"""
The watchdog of the throwaway test Postgres server: a test process killed
without stopping its server (SIGKILL, an out-of-memory kill, a timed-out run)
leaves no server running and no directory behind; a normal stop leaves the
watchdog nothing to do.
"""

import os
import stat
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.storage.postgres_server import (
    WATCHDOG_SCRIPT,
    is_postgres_available,
    postgres_bin_directory,
)
from tests.storage.storage_testing import PROJECT_ROOT_DIRECTORY

WAIT_SECONDS: float = 30.0
WAIT_STEP_SECONDS: float = 0.05

OWNER_THAT_EXITS: str = """
import os
import subprocess
import sys

watchdog, pg_ctl, root = sys.argv[1:]
subprocess.Popen(
    [sys.executable, watchdog, str(os.getpid()), pg_ctl, root],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True,
)
"""


def wait_until(condition: Callable[[], bool]) -> bool:
    deadline: float = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(WAIT_STEP_SECONDS)

    return condition()


def process_is_running(pid: int) -> bool:
    """False for a pid that is gone or only a zombie waiting to be reaped."""

    try:
        status: str = Path(f"/proc/{pid}/stat").read_text()
    except FileNotFoundError:
        return False

    return status.rsplit(")", 1)[1].split()[0] != "Z"


def fake_pg_ctl(directory: Path) -> tuple[Path, Path]:
    """An executable standing in for pg_ctl that records its arguments."""

    calls: Path = directory / "pg_ctl-calls.txt"
    program: Path = directory / "pg_ctl"
    program.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"with open({str(calls)!r}, 'a') as calls:\n"
        "    calls.write(' '.join(sys.argv[1:]) + '\\n')\n"
    )
    program.chmod(program.stat().st_mode | stat.S_IXUSR)
    return program, calls


def test_a_dead_owner_gets_its_server_stopped_and_directory_deleted(
    tmp_path: Path,
) -> None:
    root: Path = tmp_path / "workshop-pg-owner-died"
    (root / "data").mkdir(parents=True)
    pg_ctl, calls = fake_pg_ctl(tmp_path)

    subprocess.run(
        [
            sys.executable,
            "-c",
            OWNER_THAT_EXITS,
            str(WATCHDOG_SCRIPT),
            str(pg_ctl),
            str(root),
        ],
        check=True,
    )

    assert wait_until(lambda: not root.exists())
    assert calls.read_text().splitlines() == [
        f"--pgdata {root / 'data'} --mode immediate --wait stop"
    ]


def test_a_stopped_server_leaves_the_watchdog_nothing_to_do(tmp_path: Path) -> None:
    root: Path = tmp_path / "workshop-pg-stopped"
    (root / "data").mkdir(parents=True)
    pg_ctl, calls = fake_pg_ctl(tmp_path)
    watchdog = subprocess.Popen(
        [
            sys.executable,
            str(WATCHDOG_SCRIPT),
            str(os.getpid()),
            str(pg_ctl),
            str(root),
        ],
        start_new_session=True,
    )
    try:
        (root / "data").rmdir()
        root.rmdir()
        assert watchdog.wait(timeout=WAIT_SECONDS) == 0
    finally:
        if watchdog.poll() is None:
            watchdog.kill()
            watchdog.wait()

    assert not calls.exists()


def test_a_killed_test_process_leaves_no_postgres_server_behind() -> None:
    if not is_postgres_available(postgres_bin_directory()):
        pytest.skip(f"Postgres binaries not found in {postgres_bin_directory()}.")

    owner = subprocess.Popen(
        [sys.executable, "-m", "tests.storage.postgres_owner_process"],
        cwd=PROJECT_ROOT_DIRECTORY,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    assert owner.stdout is not None
    root_text, postmaster_text = owner.stdout.readline().split()
    root, postmaster_pid = Path(root_text), int(postmaster_text)
    assert process_is_running(postmaster_pid)

    owner.kill()
    owner.wait()

    assert wait_until(lambda: not process_is_running(postmaster_pid))
    assert wait_until(lambda: not root.exists())
