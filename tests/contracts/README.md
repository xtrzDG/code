# Provider contracts

A renamed field or a new webhook shape at Meta, Telegram, ElevenLabs, Flitt,
Google, OpenAI, Anthropic or any other provider should fail CI, not
production. This tree holds what the providers send and answer, the
providers' own specifications, and the tests that push both through the
platform's real clients and adapters.

```
tests/contracts/
  <client package>/fixtures/   what the provider sends or answers (JSON, XML)
  <client package>/test_*.py   fixtures through the real adapters
  specs/                       vendored specifications (JSON Schema 2020-12)
  live/                        nightly smoke against the providers' sandboxes
  contract_files.py            loading fixtures
  vendor_schemas.py            assert_inbound / assert_outbound
  schema_closure.py            closing every object for outbound checks
  test_contract_coverage.py    the rules of this tree
  test_vendor_specs.py         the refresh pipeline, offline
```

## The rules (`test_contract_coverage.py`)

- Every package in `app/clients` has `tests/contracts/<package>/fixtures/`
  with at least one file. A new client package starts with its fixtures.
- Every fixture parses and is read by a test (by its file name).
- Every spec in `specs/` names its provider (a client package), its kind
  (`generated` or `documented`) and where it comes from; its roots exist and
  the file is valid JSON Schema.
- The generated specs are exactly the ones `scripts/vendor_specs/spec_registry.py`
  builds, with the same source and roots.

## Two directions, two strictnesses

`assert_inbound(body, spec, root)` checks what a provider sends or answers.
Vendors add fields freely, so the schema stays open: a missing required
field, a renamed field the platform reads, or a wrong type fails.

`assert_outbound(body, spec, root)` checks what the platform sends, with
every object closed (`unevaluatedProperties: false`): a field the vendor
does not define fails. Outbound bodies are captured where they leave the
client (httpx `MockTransport`, `RecordingTransport`, `ScriptedHttp`), never
rebuilt by the test.

An unknown variant (a new webhook field, an event type the platform does not
handle) must be ignored and logged by kind, never answered with a 500; each
channel has a fixture for that (`*_unknown_*`).

## Fixtures

Fixtures start from the vendors' documentation examples, adapted to the
platform's cases (Georgian, Russian, Hebrew texts; the 131047 and 131026
WhatsApp failures; a Flitt callback signed with the test merchant's secret).
Values are low-entropy test values (`test-token-0000`, `AC000...`), never
real credentials or real people's data. Replace them with recorded sandbox
payloads once sandbox credentials exist (below).

Packages without a published machine-readable specification are held to
their RFCs or documented replies instead: Web Push (RFC 8030, 8291, 8292),
SMTP (RFC 5321, 5322, 6152), HTTP (RFC 9110, 9112), S3 (botocore's service
model, which every AWS SDK is generated from), Postgres (SQLSTATE codes of
Appendix A), ECB and NBG (their published feeds, read by
`tests/billing/rate_feed_fakes.py`).

## Specifications

### Generated

`scripts/refresh_vendor_specs.py` reads each vendor's published document,
keeps only the schemas the platform exchanges (the roots in
`spec_registry.py` and `sdk_specs.py`), drops annotations, translates
OpenAPI 3.0 keywords and Google discovery types into JSON Schema 2020-12, and
writes `specs/<file>.json`:

```
uv run python -m scripts.refresh_vendor_specs                # every provider
uv run python -m scripts.refresh_vendor_specs --only meta    # one provider
uv run python -m scripts.refresh_vendor_specs --check        # drift only, exit 1
uv run python -m scripts.refresh_vendor_specs --cache DIR    # keep/reuse downloads
```

| Provider | Source |
| --- | --- |
| telegram | Telegram Bot API OpenAPI (community-maintained from core.telegram.org) |
| meta | Meta's WhatsApp Business Platform OpenAPI |
| openai | OpenAI's OpenAPI |
| anthropic, elevenlabs | the types of the installed SDK (`anthropic`, `elevenlabs`) |
| google | Google Calendar API v3 discovery document |
| twilio | twilio-oai |
| langfuse | Langfuse's public API OpenAPI |
| cal_com | Cal.com API v2 OpenAPI |

A vendor document that is wrong where the platform depends on it gets a
patch in the registry (`DropRequired`, `AddProperty`, `DropProperty`,
`DropPropertyKeyword`, `RetypeProperty`, `RepairSectionReferences`). Every
patch states its reason, which is written into the file's `x-vendor.patches`.
A patch the vendor made unnecessary stops the refresh (`StalePatchError`):
remove it then.

The SDK-based specs (Anthropic, ElevenLabs) are checked against the
installed SDKs on every run (`test_vendor_specs.py`), so a Dependabot bump
that changes a type fails until the spec is refreshed and the platform
adapted.

### Documented

Where a vendor publishes no machine-readable specification (Meta Messenger
Platform, ElevenLabs webhooks, Flitt, Cloudflare Turnstile, Web Push), the
spec is written by hand from the pages listed in `x-vendor.docs`, with
`"kind": "documented"`. The refresh script never touches these; review them
against the pages when the vendor announces changes.

## When the nightly run fails

`.github/workflows/contracts-live.yml` runs every night and on demand:

- **drift**: `refresh_vendor_specs --check` against the published
  documents. The run summary lists the changed definitions.
- **smoke**: `tests/contracts/live` against the providers' sandboxes.

A scheduled failure opens one "Provider drift" issue (or comments on the
open one). To act on it: run the refresh for that provider, run
`uv run pytest tests/contracts`, and let the failing contract tests show
what the platform must change. Commit the refreshed spec with the fix.

## Switching the live smoke on

The smoke runs only with `CONTRACTS_LIVE=1` (the workflow sets it). Each
provider is skipped until its secrets exist in the repository's Actions
secrets. Use sandbox or test accounts only, never production credentials.

| Provider | Secrets | Sandbox |
| --- | --- | --- |
| Telegram | `CONTRACTS_TELEGRAM_BOT_TOKEN` | a bot made with @BotFather for tests only (`getMe`) |
| Meta (WhatsApp) | `CONTRACTS_META_ACCESS_TOKEN`, `CONTRACTS_META_PHONE_NUMBER_ID`, `CONTRACTS_META_TEST_RECIPIENT` | the test WhatsApp number of a developer app and one of its allowed recipients |
| Twilio | `CONTRACTS_TWILIO_TEST_ACCOUNT_SID`, `CONTRACTS_TWILIO_TEST_AUTH_TOKEN` | the account's test credentials (nothing is sent; the magic sender +15005550006 always succeeds) |
| Google | `CONTRACTS_GOOGLE_CLIENT_ID`, `CONTRACTS_GOOGLE_CLIENT_SECRET`, `CONTRACTS_GOOGLE_REFRESH_TOKEN` | an OAuth client and a refresh token of a test Google account |
| OpenAI | `CONTRACTS_OPENAI_API_KEY` | a project key with a small budget |
| Anthropic | `CONTRACTS_ANTHROPIC_API_KEY` | a workspace key with a small spend limit |
| ElevenLabs | `CONTRACTS_ELEVENLABS_API_KEY` | a test workspace with at least one conversation |
| Flitt | none | Flitt's documented test merchant 1549901 |

Run it locally the same way:

```
CONTRACTS_LIVE=1 CONTRACTS_TELEGRAM_BOT_TOKEN=... uv run pytest tests/contracts/live -rs
```

## Recording sandbox payloads

Once a provider's sandbox works, replace its documentation examples with
real answers:

1. Run the smoke locally with `CONTRACTS_RECORD_DIR=/tmp/contracts` (never
   in CI): every JSON answer is written there as `<test>-<n>.json`.
2. For webhooks, point the sandbox's webhook at a request bin you control
   and save the bodies the same way.
3. Replace ids, phone numbers, names, tokens and signatures with
   low-entropy test values (and re-sign signed bodies with the test secret),
   then overwrite the fixture and run `uv run pytest tests/contracts`.
4. gitleaks scans the whole history: if a reviewed fixture still trips it,
   add the fingerprint to `.gitleaksignore` in the same pull request.
