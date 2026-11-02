# Secrets inventory

Every secret the platform holds: what it opens, who owns it, where it is
stored, how often it is rotated and how. `tests/legal/test_secrets_inventory.py`
reads the tables below: every secret the backend's settings, the cabinet,
`render.yaml` or the workflows read must have a row, and every row must name
a variable that still exists.

**Owner.** The *platform owner* (the founder, `@xtrzDG` in
`.github/CODEOWNERS`) holds the Render workspace, the GitHub organisation and
every provider console, and is accountable for each row; the *deputy* (the
second maintainer, `docs/operations/contacts.md`) can rotate any of them.
Nobody else reads production secrets (`docs/security/access-review.md`).

**Rotation.** At most every 12 months, and at once when a secret may have
been exposed or someone who could read it leaves
(`docs/operations/offboarding.md`). The rows marked "on exposure" are the
exception: rotating them breaks what they protect (the suppression list's
digests, every push subscription) or they are public by design (the
Sentry DSN), so a departure alone does not rotate them; a suspected leak
does, as an incident. Each rotation is a line in the
log at the end. The checks of the quarterly access review include the dates.

**Never** in git (gitleaks in CI, `SECURITY.md`), chat, e-mail, tickets or
the browser bundle (`NEXT_PUBLIC_*` holds no secret). In production the
API and the worker refuse to start on an unset, test or development
setting and on a missing, public or short `ENCRYPTION_KEY`
(`app/gateways/startup_checks.py`).

## Where they live

| Store | What | Who can read |
| --- | --- | --- |
| Render env group `workshop-backend` | the encryption ring and keys every backend service shares | the platform owner and deputy (Render workspace) |
| Render service variables (`sync: false` in `render.yaml`) | provider keys of `workshop-api` (the workers read them `fromService`), the backup bucket of `workshop-backup` and `workshop-batch-worker` | same |
| Render database `workshop-db` | `DATABASE_URL` (`fromDatabase`) | same |
| GitHub repository and environment secrets | CI, the promotion to `release` (`production-release`), the restore drill (`backup-drill`), the live contract tests, the nightly evals | repository admins |
| Postgres, sealed with `ENCRYPTION_KEYS` | the businesses' own credentials (last table) | the application only; a leaked key alone opens nothing |
| The founders' password manager vault | escrow copies of `ENCRYPTION_KEYS` and the age escrow identity | two named people |

## Platform secrets on Render

| Secret | Purpose | Owner | Stored in | Rotate | Procedure |
| --- | --- | --- | --- | --- | --- |
| `ENCRYPTION_KEY`, `ENCRYPTION_KEYS` | seals channel, calendar and TOTP secrets; signs booking, notification and chat-stream links; derives Telegram webhook secrets and recording keys | platform owner | env group `workshop-backend`, escrow in the vault | 12 months | `docs/operations/backup-restore.md`, "Key rotation": new key first in the ring, re-seal from `/admin/security`, retire after links and recordings aged out; dual-key throughout |
| `SUPPRESSION_LIST_KEY` | HMAC key of the suppression list digests | platform owner | env group `workshop-backend` (generated once, `render.yaml`) | on exposure | A new key makes every stored digest unmatchable, and the customers who said STOP could be written to again; there is no re-keying job, so it is never rotated on a schedule or on a departure. A leak reveals no identity by itself (a digest can only be tested against a known identity). On exposure: incident first (`docs/operations/incident.md`), where the founder weighs keeping the key against starting the list again and records the decision |
| `DATABASE_URL` | the migration role (tables' owner): migrations, backups, audit purges | platform owner | `workshop-db` (`fromDatabase`) | 12 months | Render's database credentials; every service reads it through `fromDatabase` and picks it up on redeploy |
| `DATABASE_URL_TENANT`, `DATABASE_URL_PLATFORM` | the API's and workers' row-level-security roles | platform owner | `workshop-api`, read by the workers `fromService` | 12 months | `\password workshop_tenant_app` (and `_platform_app`) as the migration role, then the new URL on `workshop-api` in the maintenance window (`docs/operations/deploys.md`, "Database roles") |
| `LIVE_EVENTS_DATABASE_URL` | a direct connection for `LISTEN` | platform owner | `workshop-api` when set | with its role | as `DATABASE_URL_TENANT` |
| `RESTORE_CHECK_DATABASE_URL` | scratch server of the restore drill (never production) | platform owner | the drill's throwaway Postgres in CI (no secret); a scratch server's role when run by hand | 12 months | new password of the scratch server's role, set where the drill runs |
| `METRICS_TOKEN` | reads `/metrics` of the API and workers | platform owner | `workshop-api` (Render `generateValue`) | 12 months | generate a new value on Render, update the scraper (Grafana) right after the redeploy |
| `OPENAI_API_KEY`, `EMBEDDINGS_API_KEY` | the language model and embeddings (EU project) | platform owner | `workshop-api`; a separate key for the nightly evals in GitHub (`evals-nightly.yml`) | 12 months | create a key in the EU project, set it, redeploy, delete the old key after `llm_errors` stays quiet for an hour; the evals' key the same way in GitHub |
| `ANTHROPIC_API_KEY` | the second model provider | platform owner | `workshop-api`; a separate key for the evals in GitHub | 12 months | as OpenAI (a key per environment, never shared) |
| `ELEVENLABS_API_KEY` | the voice platform's API (agents, calls) | platform owner | `workshop-api` | 12 months | new scoped key in the console, set, redeploy, revoke the old one; `voice_health` must stay quiet |
| `ELEVENLABS_WEBHOOK_SECRET` | HMAC of post-call and initiation webhooks | platform owner | `workshop-api` | 12 months | single secret: change it in the console and on Render together in the maintenance window; deliveries in between are refused (`docs/operations/runbooks/voice-outage.md`) |
| `META_APP_SECRET` | Meta webhook signatures and token checks | platform owner | `workshop-api` | 12 months | reset in the Meta app dashboard, set at once, redeploy (single secret: maintenance window) |
| `META_VERIFY_TOKEN` | Meta's webhook subscription handshake | platform owner | `workshop-api` | 12 months | new random value on Render, then in the app's webhook settings |
| `WHATSAPP_SYSTEM_USER_TOKEN`, `WHATSAPP_OTP_ACCESS_TOKEN` | the platform's WhatsApp sender (notifications, login codes) | platform owner | `workshop-api` | 12 months (Meta's maximum when shorter) | new system-user token in Business Manager, set, redeploy, revoke the old one |
| `TELEGRAM_PLATFORM_BOT_TOKEN` | the platform bot (alerts, owner notifications) | platform owner | `workshop-api` | 12 months | `/revoke` in BotFather, set the new token; the webhook is registered again at the API's start |
| `TELEGRAM_GATEWAY_API_TOKEN` | login codes through Telegram | platform owner | `workshop-api` | 12 months | new token in the Gateway account, set, redeploy |
| `TWILIO_AUTH_TOKEN` | SMS and the voice fallback; signs Twilio's callbacks | platform owner | `workshop-api` | 12 months | in the maintenance window: create Twilio's secondary auth token, set it, redeploy, and promote it as soon as the deploy is live. API calls accept both tokens until the promotion, but Twilio signs its callbacks with the primary one only, so the voice fallback's callbacks are refused between the deploy and the promotion |
| `ZADARMA_API_KEY`, `ZADARMA_API_SECRET` | telephony API and its notification signatures | platform owner | `workshop-api` | 12 months | regenerate in the Zadarma cabinet and set both in the maintenance window |
| `FLITT_SECRET_KEY` | Flitt payments and their signatures | platform owner | `workshop-api` | 12 months | new key in the Flitt merchant portal, set at once (single secret: maintenance window) |
| `STRIPE_SECRET_KEY` | Stripe API (restricted key) | platform owner | `workshop-api` | 12 months | roll the restricted key in the dashboard with an expiry of 24 hours, set, redeploy |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signatures | platform owner | `workshop-api` | 12 months | roll the endpoint secret with a 24-hour overlap (Stripe signs with both), set, redeploy |
| `GOOGLE_OAUTH_CLIENT_SECRET` | the Google Calendar connection | platform owner | `workshop-api` | 12 months | add a second client secret in Google Cloud, set, redeploy, disable the old one |
| `SMTP_PASSWORD` | the e-mail provider | platform owner | `workshop-api` | 12 months | new SMTP credential at the provider, set, redeploy, delete the old one; `outbound_failures` must stay quiet |
| `TURNSTILE_SECRET_KEY` | server-side bot checks of risky login requests | platform owner | `workshop-api` | 12 months | rotate in Cloudflare (it keeps the old secret valid for a grace period), set, redeploy |
| `WEB_PUSH_VAPID_PRIVATE_KEY` | signs push notifications to owners' devices | platform owner | `workshop-api` | on exposure | a new pair invalidates every subscription: the cabinet subscribes again at the next visit; replace both keys together |
| `LANGFUSE_SECRET_KEY` | the quality journal (EU) | platform owner | `workshop-api` | 12 months | new key pair in the Langfuse project, set both, redeploy |
| `OTEL_EXPORTER_OTLP_HEADERS` | the trace collector's authorization | platform owner | `workshop-api` | 12 months | new ingest token at the collector, set, redeploy |
| `SENTRY_DSN` | error reports (sending only; the cabinet's DSN is public by design) | platform owner | `workshop-api`, `workshop-cabinet`, GitHub (restore drill) | on exposure | a new client key in the Sentry project, set, disable the old one |
| `RECORDINGS_S3_SECRET_ACCESS_KEY` | the recordings bucket (EU) | platform owner | `workshop-api` | 12 months | second access key at the storage provider, set with its `RECORDINGS_S3_ACCESS_KEY_ID`, redeploy, delete the old key |
| `BACKUP_S3_SECRET_ACCESS_KEY` | the off-site backup bucket (write for the cron, read for the drill) | platform owner | `workshop-backup`, `workshop-batch-worker`, GitHub `backup-drill` | 12 months | as the recordings bucket, in each store; the next night's backup and the weekly drill prove it |

## Secrets that exist only in GitHub

| Secret | Purpose | Owner | Stored in | Rotate | Procedure |
| --- | --- | --- | --- | --- | --- |
| `BACKUP_AGE_IDENTITY` | opens backups in the restore drill | platform owner (escrow holder for the second identity) | GitHub environment `backup-drill` | 12 months | `docs/operations/backup-restore.md`, "Keys and custody": add the new public key, keep the old private key until every kept archive is newer |
| `RELEASE_DEPLOY_KEY` | the SSH deploy key that moves `release` (what production deploys) after the approved promotion | platform owner | GitHub environment `production-release` (reviewers, branch `main` only) | 12 months | `ssh-keygen -t ed25519`, the new `.pub` as a write deploy key, the private key as the secret, then delete the old deploy key and both local files (`docs/operations/deploys.md`, "One-time setup") |
| `MONITORING_API_KEY` | the hourly synthetic booking of production's monitoring business (`synthetics.yml`) | platform owner | repository secret | 12 months | a new API key of the monitoring business with `bookings:write` only (Settings → Integrations → API keys), set the secret, revoke the old key after the next green run |
| `STAGING_SCAN_API_KEY` | the weekly active ZAP scan of staging's public API (`zap-staging.yml`) | platform owner | repository secret | 12 months | a new API key of staging's scan business, set the secret, revoke the old key; never a production key |
| `REPO_SETTINGS_TOKEN` | reads branch protection for the daily settings check | platform owner | repository secret | 12 months (fine-grained token expiry) | new fine-grained token, *Administration: Read-only*, this repository only (`SECURITY.md`, "Repository settings") |
| `SENTRY_AUTH_TOKEN` | uploads the cabinet's source maps from CI | platform owner | repository secret | 12 months | new organisation token with the release scope only |
| `CONTRACTS_OPENAI_API_KEY`, `CONTRACTS_ANTHROPIC_API_KEY`, `CONTRACTS_ELEVENLABS_API_KEY` | live contract tests against the providers | platform owner | repository secrets | 12 months | separate low-limit keys, never production's |
| `CONTRACTS_GOOGLE_CLIENT_SECRET`, `CONTRACTS_GOOGLE_REFRESH_TOKEN` | the calendar contract test's own Google project | platform owner | repository secrets | 12 months | new client secret and a fresh consent of the test account |
| `CONTRACTS_META_ACCESS_TOKEN`, `CONTRACTS_TELEGRAM_BOT_TOKEN`, `CONTRACTS_TWILIO_TEST_AUTH_TOKEN` | test accounts of Meta, Telegram and Twilio | platform owner | repository secrets | 12 months | new token of the test app, bot or test account |

The workflows' own `GITHUB_TOKEN` is issued per run with the permissions
each workflow declares; it needs no rotation.

## The businesses' credentials (in the database)

| Credential | Sealed how | Who rotates |
| --- | --- | --- |
| Telegram bot tokens, Meta (WhatsApp, Instagram, Messenger) tokens | Fernet with the first key of `ENCRYPTION_KEYS` (`app/adapters/security/secret_cipher_adapter.py`) | the owner, by reconnecting; Meta tokens nearing expiry are flagged daily (`check_channel_credentials`) |
| Google Calendar refresh tokens | same | the owner, by reconnecting (or disconnecting in the cabinet) |
| TOTP seeds of owners, staff and admins | same (`app/use_cases/admin/security/totp_secret_resealer.py`) | the person, by enrolling again; re-sealed with every key rotation |
| Public API keys | only a hash is stored (`app/use_cases/integrations/authenticate_api_key_use_case.py`) | the owner: create a new key, then revoke the old one |
| Outbound webhook signing secrets | shown once, stored sealed | the owner (`app/use_cases/integrations/rotate_webhook_secret_use_case.py`) |

## Rotation log

| Date | Secret | By | Why |
| --- | --- | --- | --- |
| [first entry at launch] | every secret above | [name] | set for production (`docs/operations/go-live.md`) |
