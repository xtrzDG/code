"""
Building AppContainer fits in half of the recursion headroom it gets.

dependency-injector deep-copies the whole provider graph when AppContainer is
built. The deepest copy path grows with the graph and follows the copy order,
which string hashing changes from process to process, so a graph that has
outgrown CONTAINER_BUILD_RECURSION_LIMIT (app/containers/app.py) fails only
now and then: in the worker of a chaos game day, in a test process that
builds the container under its own frames. This test builds the container in
fresh processes, under the hash seeds whose copy paths were the deepest of 30
measured, with half the limit; a graph that needs more fails here every run.
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
# The deepest copy paths of 30 seeds measured (about 2,850 to 2,900 frames).
DEEPEST_HASH_SEEDS: tuple[str, ...] = ("4", "8", "16")
BUILD_TIMEOUT_SECONDS: float = 120.0
BUILD_WITH_HALF_THE_HEADROOM: str = (
    "import sys\n"
    "from app.containers.app import AppContainer, CONTAINER_BUILD_RECURSION_LIMIT\n"
    "sys.setrecursionlimit(CONTAINER_BUILD_RECURSION_LIMIT // 2)\n"
    "AppContainer()\n"
)


def test_the_container_builds_with_half_its_recursion_headroom() -> None:
    # One process per seed, side by side: each one imports the whole app.
    builds: dict[str, subprocess.Popen[str]] = {
        hash_seed: subprocess.Popen(
            [sys.executable, "-c", BUILD_WITH_HALF_THE_HEADROOM],
            cwd=PROJECT_ROOT,
            env={**os.environ, "PYTHONHASHSEED": hash_seed},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        for hash_seed in DEEPEST_HASH_SEEDS
    }
    failures: dict[str, str] = {}
    for hash_seed, build in builds.items():
        _, stderr = build.communicate(timeout=BUILD_TIMEOUT_SECONDS)
        if build.returncode != 0:
            failures[hash_seed] = stderr[-2000:]

    assert not failures, (
        "Building AppContainer needs more than half of "
        "CONTAINER_BUILD_RECURSION_LIMIT (app/containers/app.py): measure the "
        "deepest copy path again and give the composition root its headroom "
        f"back. Failed under hash seeds {sorted(failures)}:\n"
        + "\n".join(failures.values())
    )
