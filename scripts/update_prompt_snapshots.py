"""
Rewrite the golden snapshots of the niche instructions (chat and phone):

    uv run python -m scripts.update_prompt_snapshots

Run it after an intended change to a niche template, an instruction
section or the fact table, then review the diff of
tests/assembly/snapshots/ like any other code change.
"""

from pathlib import Path

from tests.assembly.niche_prompt_samples import write_prompt_snapshots


def main() -> None:
    written: list[Path] = write_prompt_snapshots()
    print(f"Wrote {len(written)} prompt snapshots to {written[0].parent}.")


if __name__ == "__main__":
    main()
