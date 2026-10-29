# AGENTS.md instructions

To work in this local environment, first call `uv run prompt_forge agent_help`
and follow its loading rules. If `prompt_forge` is not installed (for example in
a cloud session), skip this step.

Project documents to read before changing code:

- `docs/concept.md` — the product (AI front-line assistant for businesses).
- `docs/architecture.md` — roles, bounded contexts, flows, i18n approach.
- `docs/conventions.md` — implementation rules every module follows.
- `docs/PLAN.md` — the working checklist.

## Domain primitives

Do not use raw `str`, `int`, `float`, or `uuid.UUID` for domain/business-owned
values. Use the project primitives from `app/schemas/typings/` instead.

- IDs must use primitives from `app/schemas/typings/ids.py`.
- Unconstrained domain strings must use primitives from
  `app/schemas/typings/strings.py`.
- Domain strings with reusable value invariants must use
  `BaseConstrainedTypedString` primitives from
  `app/schemas/typings/constrained_strings.py`.
- Unconstrained domain integers must use primitives from
  `app/schemas/typings/integers.py`.
- Domain integers with reusable value invariants must use
  `BaseConstrainedTypedInt` primitives from
  `app/schemas/typings/constrained_integers.py`.
- Unconstrained domain finite floats must use primitives from
  `app/schemas/typings/floats.py`.
- Domain finite floats with reusable range invariants must use
  `BaseConstrainedTypedFloat` primitives from
  `app/schemas/typings/constrained_floats.py`.
- Declare reusable string, integer, and float constraints as class attributes on
  their constrained primitive. Float constraints support only exact finite
  `float` bounds with `gt`, `ge`, `lt`, or `le`; do not invent `multiple_of`
  semantics for binary floating point. Do not compose reusable domain
  primitives from `Annotated`, `AfterValidator`, or `StringConstraints`.
- If the required primitive does not exist yet, add a clearly named primitive to
  the owning `app/schemas/typings/` module before using it in DTOs, documents,
  contracts, use cases, or other business code.
- Raw `str`, `int`, `float`, and `uuid.UUID` are allowed only at external
  boundaries before validation/parsing, or for purely technical values that are
  not domain data.
- Architecture policy tests may contain explicit exception lists. Do not expand
  those exception lists by default. Architecture principles forbid adding
  exceptions unless the author explicitly confirms that the field cannot use a
  typed primitive.

After boundary validation, business code must receive typed primitives, not raw
Python primitives.

## Primitive semantic identity

A typed primitive represents exactly one domain meaning. Treat every operation
on it as a semantic boundary:

- Never reconstruct the original typed primitive after validation,
  transformation, string processing, or arithmetic. Those operations no longer
  guarantee the original meaning.
- A plain `str`, `int`, or `float` result from an operation deliberately signals
  that the source semantic guarantee has been lost.
- If the result has a domain meaning, validate it and construct a different,
  explicitly named primitive for that meaning.
- Semantic stages must be sibling types, not an inheritance chain. For example,
  `RawUserInput(BaseTypedString)` becomes
  `ValidatedUserInput(BaseTypedString)` after validation; do not make
  `ValidatedUserInput` inherit from `RawUserInput`.
- Arithmetic destroys the source meaning. Adding a delta to
  `CurrentTimeInSeconds(BaseTypedInt)` must produce a separately named and
  validated destination type, never another `CurrentTimeInSeconds`.

Multiple inheritance is forbidden for domain primitives. Do not use inheritance
to combine meanings or constraints.

Bad:

```python
class DivisibleByTwo(BaseTypedInt): ...


class DivisibleByThree(BaseTypedInt): ...


class DivisibleBySix(DivisibleByTwo, DivisibleByThree): ...
```

Good:

```python
class DivisibleByTwo(BaseTypedInt): ...


class DivisibleByThree(BaseTypedInt): ...


class DivisibleBySix(BaseTypedInt): ...
```
