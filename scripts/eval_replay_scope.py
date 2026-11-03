"""
Whether a change touches what the assistant's model sees or how its
answers are scored, so CI's evals job must replay every recorded
conversation (AI-12):

    uv run --no-project python -m scripts.eval_replay_scope --base <commit>
    git diff --name-only main | uv run python -m scripts.eval_replay_scope

What the model sees is the instruction (its sections, the niche templates,
the fact table, the owner texts it quotes, the golden prompt snapshots
every prompt change updates), the tool definitions and their input
schemas, the pinned model ids, the conversation engine and the reply
guard; how it is scored is the evaluation harness and its datasets,
cassettes and baselines. The script prints the matching paths and, under
GitHub Actions, writes `replay=true|false` to $GITHUB_OUTPUT. It needs only
the standard library, so the job decides before it installs the
dependencies. When git cannot list the changed files (a base commit a
force-push removed, a shallow clone) it replays everything: the gate is
never skipped for want of a diff.
"""

import argparse
import os
import subprocess  # nosec B404 - git, with fixed arguments
import sys
from collections.abc import Iterable, Sequence
from fnmatch import fnmatchcase

MODEL_FACING_PATTERNS: tuple[str, ...] = (
    # The instruction, its sections, scorers and the golden prompt snapshots.
    "app/utilities/assembly/*",
    "app/registries/niches/*",
    "app/registries/localization/texts/en.json",
    "tests/assembly/snapshots/*",
    # Tool definitions and their input schemas.
    "app/registries/tools/*",
    "app/schemas/dto/assistant_tools.py",
    "app/schemas/dto/*_tool_inputs.py",
    "app/schemas/constants/assistants.py",
    # Pinned model ids and the provider adapters.
    "app/utilities/conversations/llm_model_pins.py",
    "app/adapters/llm/*",
    # The conversation engine, what it hands the model (tool payloads, the
    # fenced customer and owner texts, memory, knowledge search results)
    # and the guard on its replies; how a recorded call is matched.
    "app/use_cases/conversations/*",
    "app/utilities/conversations/*",
    "app/utilities/memory/*",
    "app/utilities/knowledge/*",
    "app/utilities/reply_guard/*",
    "app/utilities/llm_cassettes/*",
    # The harness itself.
    "app/schemas/constants/evaluations.py",
    "evals/*",
    "scripts/eval_harness/*",
    "scripts/run_evals.py",
    "scripts/eval_replay_scope.py",
)
OUTPUT_KEY: str = "replay"
# The commit GitHub reports before a branch's first push.
NULL_COMMIT: str = "0" * 40


def matching_paths(paths: Iterable[str]) -> list[str]:
    """The changed paths a replay must cover, in the order given."""

    return [
        path
        for path in (raw.strip() for raw in paths)
        if path and any(fnmatchcase(path, pattern) for pattern in MODEL_FACING_PATTERNS)
    ]


def changed_paths(base: str) -> list[str]:
    """Files changed between `base` and HEAD (git diff --name-only)."""

    completed = subprocess.run(  # nosec B603 B607 - fixed git arguments
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git diff failed")

    return completed.stdout.splitlines()


def write_output(replay: bool) -> None:
    target: str | None = os.environ.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a", encoding="utf-8") as output:
            output.write(f"{OUTPUT_KEY}={'true' if replay else 'false'}\n")


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--base", help="compare HEAD with this commit")
    parser.add_argument(
        "--all", action="store_true", help="replay whatever changed (manual runs)"
    )
    parsed = parser.parse_args(arguments)
    if parsed.all or parsed.base in ("", NULL_COMMIT):
        print("No base to compare with; replay every recorded conversation.")
        write_output(True)
        return 0

    try:
        paths: list[str] = (
            changed_paths(parsed.base) if parsed.base else sys.stdin.read().splitlines()
        )
    except RuntimeError as error:
        print(f"Cannot list the changed files ({error}); replay everything.")
        write_output(True)
        return 0

    matched: list[str] = matching_paths(paths)
    for path in matched:
        print(f"model-facing: {path}")

    print(
        "Replay every recorded conversation."
        if matched
        else "Nothing the model sees changed; the replay gate is skipped."
    )
    write_output(bool(matched))
    return 0


if __name__ == "__main__":
    sys.exit(main())
