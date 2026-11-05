"""
The owner process of the watchdog test:

    python -m tests.storage.postgres_owner_process

Starts a throwaway Postgres server, prints its directory and the postmaster's
pid on one line, then waits on stdin. The test kills it there (SIGKILL), so
it never reaches its own `stop()`; if stdin closes instead, it stops cleanly.
"""

import sys

from tests.storage.postgres_server import (
    ThrowawayPostgresServer,
    postgres_bin_directory,
)


def main() -> None:
    server = ThrowawayPostgresServer(postgres_bin_directory())
    server.start()
    try:
        pid_file = server.socket_directory / "data" / "postmaster.pid"
        postmaster_pid: str = pid_file.read_text().splitlines()[0]
        print(server.socket_directory, postmaster_pid, flush=True)
        sys.stdin.read()
    finally:
        server.stop()


if __name__ == "__main__":
    main()
