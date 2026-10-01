# AGENTS.md instructions

This directory intentionally contains example domain and persistence schemas.

Before writing, changing, or reviewing any domain or persistence schema in this
directory, read `example_document.py` first and follow its document/mixin
patterns.

Never delete `example_document.py` during cleanup, simplification, or generated
project maintenance. It documents how to use:

- `BaseDocument`
- `PersistentDocument`
- `UnixMicrosecondTimestampedMixin`
- `UnixMillisecondTimestampedMixin`
- `UnixNanosecondTimestampedMixin`
- `VersionedMixin`

If the examples become outdated, update them in place so the generated project
continues to show the supported document patterns.
