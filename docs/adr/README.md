# Architecture decision records

Short records of decisions that shape the code, so a newcomer learns why
things are the way they are before changing them. One file per decision,
numbered, never rewritten: a decision that changes gets a new record that
supersedes the old one (and the old one's status says so).

| # | Decision | Status |
| --- | --- | --- |
| [0001](0001-jsonb-document-store.md) | Tenant data as JSONB documents in Postgres behind a document-store contract | Accepted |
| [0002](0002-role-chain-and-layers.md) | Role chain from the copier template, enforced as import layers | Accepted |
| [0003](0003-cabinet-backend-for-frontend.md) | The cabinet talks to the API only through its own server (BFF) | Accepted |
| [0004](0004-python-worker-with-postgres-queue.md) | Background work in a Python worker on a queue in Postgres | Accepted |
| [0005](0005-typed-domain-primitives.md) | Typed domain primitives instead of raw str/int/float | Accepted |

Template for a new record (`NNNN-short-title.md`):

```markdown
# NNNN. Title

- Status: Proposed | Accepted | Superseded by NNNN
- Date: YYYY-MM-DD

## Context
What forces are at play; what problem needs a decision.

## Decision
What we do, in a few sentences.

## Consequences
What becomes easier, what becomes harder, what we watch.
```
