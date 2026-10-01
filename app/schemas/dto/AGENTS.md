# AGENTS.md instructions

This directory intentionally contains example DTO schemas.

Before writing, changing, or reviewing any DTO in this directory, read
`example_dto.py` first and follow its base-class patterns.

Never delete `example_dto.py` during cleanup, simplification, or generated
project maintenance. It documents how to use:

- `MutableDTO`
- `ImmutableDTO`
- `ArbitraryMutableDTO`
- `ArbitraryImmutableDTO`

If the examples become outdated, update them in place so the generated project
continues to show the supported DTO patterns.
