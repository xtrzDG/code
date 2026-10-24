# 0005. Typed domain primitives instead of raw str/int/float

- Status: Accepted
- Date: 2026-10-02

## Context

The domain is full of values that look alike to Python: a business id and
a user id, minor units and major units of money, microseconds and seconds,
a language tag and a country code, a raw phone number and an E.164 number.
Mixing them up compiles, passes most tests and corrupts data quietly, often
across tenants or currencies.

## Decision

- Business code does not use raw `str`, `int`, `float` or `uuid.UUID` for
  domain values. Each meaning has its own primitive in
  `app/schemas/typings/` (ids, strings, constrained strings, integers,
  constrained integers, floats), as `AGENTS.md` describes.
- A primitive means exactly one thing. Validation or arithmetic produces a
  value of a different, explicitly named primitive (`RawUserInput` becomes
  `ValidatedUserInput`); semantic stages are sibling types, never an
  inheritance chain, and multiple inheritance is forbidden.
- Raw values are allowed only at external boundaries before parsing (path
  and query strings, provider payloads) and for technical values.
- `tests/architecture_policy/test_schema_domain_primitives.py` checks the
  documents and DTOs; mypy and pyright in strict mode check the rest.

## Consequences

- Wrong-unit and wrong-id bugs become type errors, and signatures document
  themselves.
- More types to name and import; boundary code converts explicitly. The
  conversion points are where validation happens, which is the point.
