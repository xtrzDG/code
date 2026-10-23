# Environment variables

Every variable of the backend with what happens without it (its default).
The owner's step-by-step launch with every account and key is the Russian
[`docs/LAUNCH.md`](../LAUNCH.md); [`.env.example`](../../.env.example) has
every variable with a short explanation; the cabinet's variables
(`BACKEND_URL`, `COOKIE_SECURE`, `TRUSTED_PROXY_HOPS`) are in
[`web/README.md`](../../web/README.md).
`tests/platform/test_environment_variables.py` compares this table with the
code: every variable the settings or an SDK read is in `.env.example` and
here, and nothing else is. A new variable goes to its settings section,
`.env.example`, this table and `docs/LAUNCH.md`.

## Variables

| Variable | Without it (default) |
| --- | --- |
| `APP_ENV` | `development` (the Docker image: `production`); `production` requires `ENCRYPTION_KEY` and never logs login codes |
| `APP_BASE_URL` | the API's public https address (webhooks, the widget, payments); without it a voice version cannot be published, Telegram cannot be connected and no payment can be taken |
| `CABINET_BASE_URL` | outside `production`, `http://localhost:3000`; in `production` the owner sees a plain page after Google consent instead of returning to the cabinet, and the payment page returns the payer only to the addresses of `CORS_ALLOWED_ORIGINS` |
| `CORS_ALLOWED_ORIGINS` | CORS off (the website widget allows any origin by itself); the payment page returns the payer only to the origin of `CABINET_BASE_URL` and `APP_BASE_URL`. Give the cabinet's address (`http://localhost:3000` locally; `docker-compose.yml` sets it) |
| `DATABASE_URL` | data kept in memory. The migration role, owner of the tables: `workshop migrate`, backups and maintenance commands use it; once the two addresses below are set, the application's pools do not |
| `DATABASE_URL_TENANT`, `DATABASE_URL_PLATFORM` | both pools run on `DATABASE_URL` (development only: `production` does not start without them). The two login roles of migration 1200 (`docs/operations/deploys.md`, "Database roles"): the tenant pool (a member of `workshop_tenant`) sees one business whatever the session sets, the platform pool (a member of `workshop_platform`) sees every row; set both or neither. At start the process checks the roles: a tenant role that is a superuser, has `BYPASSRLS`, owns the tables or is a member of `workshop_platform` fails the start in `production` |
| `LIVE_EVENTS_DATABASE_URL` | the cabinet's live updates and the worker's wake-up (a new job in the queue) listen for events (`LISTEN`) through `DATABASE_URL`; set a direct (session) connection to the same database only when `DATABASE_URL` goes through a transaction pooler (PgBouncer, Supavisor on port 6543), where `LISTEN` does not work. Without `DATABASE_URL` events stay inside the process |
| `ENCRYPTION_KEY` | a temporary key: channel tokens do not survive a restart; in `production` the start fails (as with the public default of `docker-compose.yml`). A Fernet key or any random string of 32 characters or more; never replaced in place |
| `ENCRYPTION_KEYS` | only `ENCRYPTION_KEY`. Key rotation: keys separated by commas, the new one first, `ENCRYPTION_KEY` last. The first encrypts and signs everything new; the others only open old values until `rotate_encrypted_secrets` re-encrypts them |
| `BACKUP_S3_ENDPOINT_URL`, `BACKUP_S3_REGION`, `BACKUP_S3_BUCKET`, `BACKUP_S3_ACCESS_KEY_ID`, `BACKUP_S3_SECRET_ACCESS_KEY` | no backups outside Render (`workshop backup` exits with code 2). A versioned bucket of another provider in the EU and a key allowed to write, list and delete in the backup folder; all five or none |
| `BACKUP_S3_PREFIX` | `workshop/`: the backups' folder in the bucket; retention touches nothing outside it |
| `BACKUP_AGE_PUBLIC_KEY` | with a bucket, the start fails: backups are stored only encrypted. age public keys (`age1…`) separated by commas: the drill key and an offline key in custody |
| `BACKUP_AGE_IDENTITY` | `workshop restore-check` cannot open backups. The drill's private key (`AGE-SECRET-KEY-1…`), only where drills run, never on production servers |
| `BACKUP_KEEP_DAILY`, `BACKUP_KEEP_MONTHLY` | 30 and 12: the last backup of each of the last 30 days and the last 12 months |
| `BACKUP_MAX_AGE_HOURS` | 26: the drill fails when the newest backup is older than 26 hours |
| `RESTORE_CHECK_DATABASE_URL` | no drills. A scratch Postgres server and a role that may create databases; never a production server |
| `POSTGRES_CLIENT_BIN_DIRECTORY` | `pg_dump` and `pg_restore` are looked up in `PATH` (the image has Debian's Postgres client) |
| `LLM_PROVIDER`, `LLM_MODEL_ID`, `LLM_JUDGE_MODEL_ID` | `openai` and `gpt-5-mini` (`anthropic`: `claude-opus-5-5`; `scripted`: no model and no keys, a rehearsal in which the Apply changes checks pass, for development, staging and e2e); `LLM_JUDGE_MODEL_ID` is the customer and judge model of autotests and of the nightly scoring of real conversations; by default a model of the other provider, so a model never scores answers of its own family: `claude-sonnet-5-5` with `openai` when `ANTHROPIC_API_KEY` is set, `gpt-5-mini` with `anthropic` when `OPENAI_API_KEY` is set; without the other provider's key, a model of its own |
| `LLM_SUMMARY_MODEL_ID` | the model of call summaries for staff and of the conversation summaries by which the assistant remembers customers (a cheap one, for example `gpt-5-nano`); defaults to `LLM_MODEL_ID` |
| `LLM_CHAT_EFFORT`, `LLM_JUDGE_EFFORT` | reasoning effort: `low` in the chat, `medium` for the autotest judge (`minimal`, `low`, `medium`, `high`) |
| `LLM_MAX_OUTPUT_TOKENS`, `LLM_TOOL_ROUND_LIMIT` | 16000 answer tokens, 8 rounds of tool calls per answer |
| `LLM_CALL_TIMEOUT_SECONDS` | 25: how many seconds one model call in a customer chat may take, then one retry; after a second failure the conversation goes to staff |
| `LLM_MAX_CONCURRENCY` | 32 model calls at once per process (an API instance or a worker); the next waits for a free place at most `LLM_CALL_TIMEOUT_SECONDS`, then the conversation goes to staff. Keep it below `THREADPOOL_SIZE` so a slow model never takes every request thread |
| `OPENAI_API_KEY`, `OPENAI_PROJECT_ID`, `OPENAI_BASE_URL` | model answers fail with 502 at the first call; the OpenAI SDK reads the key; the default address is `https://eu.api.openai.com/v1` (a project with EU data residency) |
| `ANTHROPIC_API_KEY` | needed with `LLM_PROVIDER=anthropic` and for the Anthropic fallback model (the Anthropic SDK reads the key) |
| `LLM_FALLBACK_MODEL_ID` | a fallback model of the other provider: the chat turn is repeated on it when the version's provider does not answer or its circuit breaker is open (5 failures in 60 s, a probe after 30 s). Defaults to `claude-sonnet-5-5` with `LLM_PROVIDER=openai` (needs `ANTHROPIC_API_KEY`) and `gpt-5-mini` with `anthropic` (needs `OPENAI_API_KEY`); `off` means no fallback. Without the other provider's key the fallback simply does not answer and the conversation goes to staff as before |
| `MESSAGE_COALESCE_SECONDS` | 3: the seconds of silence the worker waits after a customer's short fragment ("hi", "and also") before answering, so three quick messages get one answer; the customer sees "typing…" all along. A finished message (longer than 12 characters, ending in `.`, `?` or `!`) is answered at once; in Telegram a fragment waits 1.5 s. 0 answers every message at once |
| `CHAT_TURN_DEADLINE_SECONDS` | 20: when the answer is still being prepared this many seconds after the first unanswered message, the customer gets a short "One moment…" in their language once (through the outbox), then the answer or a handoff |
| `LLM_VERIFIER_MODEL_ID` | a cheap model that checks an answer's claims about rules and availability ("parking is free", "dogs are welcome") against the facts and tool results; asked only when the answer contains such a claim (marker dictionaries in 10 languages). Defaults to `gpt-5-nano` with `LLM_PROVIDER=openai`, `claude-haiku-4-5` with `anthropic`, no check with `scripted`; `off` turns it off. An unconfirmed claim gets one rewrite, then a handoff; a failure of the checking model never delays the answer (the claims are marked "not checked") |
| `INJECTION_FLAG_LIMIT` | 3: how many messages that look like an attempt to override the assistant's instructions (in 10 languages) one contact may send in a day; on the next the assistant answers once with a polite "please write later" and stays silent until the day has passed. Each such message is flagged and counts in the client's health in the admin area ("Spike of answer checks") |
| `LLM_TRANSCRIBE_MODEL` | `gpt-4o-transcribe`: the model that transcribes customers' voice notes in the OpenAI EU project (`OPENAI_API_KEY`, `OPENAI_BASE_URL`), also with `LLM_PROVIDER=anthropic`; the assistant's languages go as a hint, the paid seconds into cost accounting (`transcription_seconds`). With `scripted` voice notes are not transcribed: the customer gets a polite request to write |
| `MEDIA_MAX_VOICE_BYTES`, `MEDIA_MAX_IMAGE_BYTES` | 16 MiB per voice note and 5 MiB per photo: anything bigger is not downloaded from the messenger and the customer is asked to write |
| `MEDIA_MAX_VOICE_SECONDS` | 300: a longer voice note is not transcribed (a request to write instead). Voice notes and photos are stored where and as long as call recordings (`RECORDINGS_STORAGE`, `RECORDING_RETENTION_DAYS`) |
| `MEDIA_MAX_CONCURRENT_UPLOADS` | 3: how many photos and voice notes of website visitors one API process accepts at once (each upload holds its file in memory while it is checked and encrypted; one client network at most two at once); the next gets 429 with `Retry-After` and the widget asks to try a little later. An upload's body must arrive within 120 seconds (otherwise 422 `upload_too_slow`) |
| `AUTOTEST_TURN_LIMIT` | 4 customer messages per autotest scenario |
| `AUTOTEST_CRITICAL_SAMPLES` | 2: how many times each scenario that matters for a launch is played (prices, bookings, owner checks, attacks); it passes only when every run passes (pass^k) |
| `QUALITY_SAMPLE_PERCENT`, `QUALITY_SAMPLE_PER_BUSINESS`, `QUALITY_SAMPLE_BUDGET_CENTS` | 5 %, 20 and 500: the judge's (`LLM_JUDGE_MODEL_ID`) nightly scoring of real conversations: a share of the past day's conversations, at most 20 per business and at most 5 dollars a night; 0 % turns it off. The trend is on the client's admin page and the conversation card; a drop in quality raises the platform alert `quality_drop` |
| `QUALITY_SAMPLING_JUDGE_SAME_PROVIDER` | `true`: the nightly sample is scored by the assistant's own model (`LLM_MODEL_ID`), so real conversations never go to another provider. `false`: a judge of the other provider (`LLM_JUDGE_MODEL_ID`), only once the sub-processor list covers that purpose (its 30-day notice to owners has passed); otherwise production does not start (`app/gateways/startup_checks.py`). Each business may turn the sample off in Settings → Privacy |
| `SCRIPTED_LLM_LATENCY_MS` | 0: how many milliseconds the `scripted` model waits before each answer, like a real provider; set by the load tests (`perf/k6`, `docs/operations/capacity.md`) |
| `OTP_LIFETIME_SECONDS`, `OTP_MAX_FAILED_ATTEMPTS` | a login code is valid 600 seconds; after 5 wrong attempts a new code is needed |
| `OTP_SENDS_PER_DESTINATION_PER_HOUR`, `OTP_SENDS_PER_IP_PER_HOUR`, `OTP_SENDS_PER_HOUR` | 5 codes per number or address, 10 per client address and 300 to new numbers and addresses in total per hour ([`login-codes.md`](login-codes.md)) |
| `OTP_SENDS_PER_COUNTRY_PER_HOUR`, `OTP_SENDS_TO_VERIFIED_USERS_PER_HOUR` | 100 codes an hour to new numbers of one country; 300 an hour to verified people, a separate budget a flood to new numbers cannot use up |
| `OTP_VERIFIES_PER_IP_PER_10_MINUTES` | 20 code checks per client address (an IPv6 /64 network) in 10 minutes, shared by login codes and second factors |
| `OTP_HIGH_RISK_COUNTRIES` | the countries whose numbers need the bot check (small Pacific territories and some African networks); empty means no such signal |
| `OTP_DENIED_PHONE_PREFIXES` | only the built-in denial: premium-rate, shared-cost, personal and satellite numbers never get a code |
| `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY` | the bot check (Cloudflare Turnstile) is off; both or neither |
| `OTP_LOG_CODES` | on outside `production`: channels without a provider write the code to the log; cannot be turned on in `production` |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `TWILIO_MESSAGING_SERVICE_SID` | no login codes by SMS |
| `TELEGRAM_GATEWAY_API_TOKEN` | no login codes in Telegram |
| `WHATSAPP_OTP_PHONE_NUMBER_ID`, `WHATSAPP_OTP_ACCESS_TOKEN`, `WHATSAPP_OTP_TEMPLATE`, `WHATSAPP_OTP_TEMPLATE_LANGUAGES` | no login codes in WhatsApp; the token defaults to `WHATSAPP_SYSTEM_USER_TOKEN`, the template language to `en` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | no sign-in by e-mail; the port defaults to 587 (`starttls`), 465 (`ssl`), 25 (`none`). Without any code provider sign-in works only outside `production` (codes in the log) |
| `SESSION_LIFETIME_SECONDS` | a cabinet session lasts 30 days |
| `SESSION_IDLE_TIMEOUT_SECONDS` | 604800: an owner's or staff member's session unused for 7 days ends by itself (300–31536000) |
| `ADMIN_SESSION_IDLE_TIMEOUT_SECONDS` | 43200: a platform admin's session idle for 12 hours ends (300–31536000) |
| `ADMIN_SESSION_LIFETIME_SECONDS` | 86400: a platform admin's session lasts at most a day |
| `PLATFORM_ADMIN_EMAILS`, `PLATFORM_ADMIN_PHONE_NUMBERS` | no platform admins. The lists only found the team: the first of them to sign in becomes the first SUPER admin and adds the others in Admin → Team (the roles SUPER, SUPPORT_READONLY and BILLING are read from the `platform_admins` collection on every request; the admin area needs a two-factor sign-in) |
| `STEP_UP_MAX_AGE_SECONDS` | 600: exporting and deleting a contact's data, team changes, connecting a channel, an admin entering a client's cabinet and key rotation need a sign-in or confirmation code no older than 10 minutes (60–86400) |
| `MFA_ISSUER_NAME` | `Assistant Workshop`: the name under which the authenticator app shows the account |
| `WEBAUTHN_RP_ID` | the host of `CABINET_BASE_URL`: the domain passkeys are bound to, the cabinet's host or a domain above it (`workshop.example` for `app.workshop.example`). Without a domain (a cabinet on an IP address or without `CABINET_BASE_URL`) passkeys are not offered; changing the value makes the stored passkeys unusable |
| `GEOIP_COUNTRY_DATABASE_PATH` | empty: the device list (Account → Security) shows addresses only. A path to an offline GeoLite2-Country database (`.mmdb`) adds the approximate country; addresses are sent nowhere |
| `RESTRICTED_COUNTRY_CODES` | `CU,IR,KP,SY`: numbers of these countries can neither sign in nor create a business; empty lifts the restriction (check the list with a lawyer) |
| `DEFAULT_DATA_REGION` | `eu`: the data processing region in the country profiles (`eu` or `us`) |
| `RECORDING_RETENTION_DAYS` | 90 days of keeping call recordings and transcripts (a business may change its own period) |
| `SUPPRESSION_LIST_KEY` | empty: the key of the opt-out list (STOP; only HMAC fingerprints of numbers and accounts are kept, and they survive the erasure of a customer's data) is derived from `ENCRYPTION_KEY`, and a key rotation would forget it. In production set a separate random key once and never change it |
| `EXPORT_DOWNLOAD_LINK_MINUTES` | 10: how many minutes the one-time link to a business's full export works (ZIP, Settings → Privacy; 1–10). The link goes to an owner after a recent sign-in and opens once, only in that owner's session; the archive is kept for a day and downloaded at most three times, and every owner hears of each download |
| `SPEND_SOFT_LIMIT_MULTIPLE` | 5: a business's soft daily spending limit, this many times its plan's planned daily cost (`planned_provider_costs.py`; Chat is about $0.72 a day). Beyond it the assistant answers with a cheaper model until the business's midnight; the owners and the platform team get one message |
| `SPEND_HARD_LIMIT_MULTIPLE` | 15: the hard daily limit (not below the soft one). Beyond it the assistant stops answering by itself until midnight: new conversations go to the team's inbox and the voice agent takes no calls; the log records `spend_limit_reached`. An admin sets a client's own limit with `PUT /v1/admin/clients/{business_id}/spend-limits` |
| `SPEND_SOFT_LIMIT_MODEL_ID` | empty: beyond the soft limit, a small model of the same provider (`gpt-5-nano`, `claude-haiku-4-5`); a model of another provider is ignored (the conversation's history is in its provider's format) |
| `PLATFORM_DAILY_SPEND_BUDGET_USD` | empty: no budget. Whole dollars the platform plans to spend on providers per UTC day; at 80 % the alert `spend_budget` fires (`ops/alerts/spend_budget.yaml`) |
| `CALL_MAX_DURATION_SECONDS` | 600: the longest call of the voice agent (60–7200 s); written into the ElevenLabs agent when it is created and updated |
| `CALL_SILENCE_END_SECONDS` | 30: after this many seconds of silence the agent hangs up (5–600) |
| `API_REQUESTS_PER_USER_PER_MINUTE` | 600: requests per sliding minute per signed-in person; beyond it 429 with `Retry-After` |
| `API_EXPORTS_PER_USER_PER_MINUTE` | 30 of them may be exports (CSV, a customer's data, a segment's members, the full export) |
| `PUBLIC_API_REQUESTS_PER_MINUTE` | 120: requests per sliding minute per key of the public API (`/v1/public-api/me` and its other routes); beyond it 429 with `Retry-After` |
| `WEBHOOK_DISABLE_AFTER_FAILURES` | 15: after this many failed deliveries in a row a webhook is turned off (a 410 Gone answer turns it off at once); the owner turns it on again in Settings → Integrations |
| `API_REQUESTS_PER_IP_PER_MINUTE` | 120: requests without a token per client address (IPv4 or an IPv6 /64 network); the website widget, provider webhooks and the landing page's demo have limits of their own |
| `RECORDINGS_DIRECTORY` | `var/recordings` (call recordings on this server with `RECORDINGS_STORAGE=local`) |
| `RECORDINGS_STORAGE` | `local`: recordings the platform keeps itself are files on this server (development; ElevenLabs keeps its own). `s3`: EU object storage; each recording is encrypted with its business's key (HKDF of `ENCRYPTION_KEY`, AES-256-GCM in 64 KiB blocks), and after a call its recording is moved there from ElevenLabs and deleted there; without `RECORDINGS_S3_*` or `ENCRYPTION_KEY` the start fails |
| `RECORDINGS_S3_ENDPOINT_URL`, `RECORDINGS_S3_REGION`, `RECORDINGS_S3_BUCKET` | with `s3`: the address of an S3-compatible store in the EU (AWS `eu-central-1`, Cloudflare R2 with the EU jurisdiction, Hetzner, Scaleway), the signing region (`auto` for R2) and a private bucket without versions |
| `RECORDINGS_S3_ACCESS_KEY_ID`, `RECORDINGS_S3_SECRET_ACCESS_KEY` | with `s3`: a key allowed only to read, write and delete in that bucket; requests are signed (Signature V4, links valid for one minute) |
| `CONTACT_MESSAGE_LIMIT_PER_HOUR` | 60 messages of one customer in the last hour across all channels: at the 60th the assistant warns of the limit, then stays silent |
| `DPA_DOCUMENT_VERSION` | `2026-10-06`: the version of the agreement in force from `docs/legal/`; owners who accepted an earlier version are asked by the cabinet to accept the new one within 30 days |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_WEBHOOK_SECRET`, `ELEVENLABS_API_BASE_URL` | no voice agent is created: in `production` publishing a version with voice is refused (409, reason `voice_configuration`), in `development`/`test` the version goes out without a voice agent (a warning in the log). The default address is `https://api.eu.residency.elevenlabs.io` (EU data residency) |
| `ELEVENLABS_ALLOW_NON_EU_REGION` | `false`: in `production` an ElevenLabs address outside the EU stops the start |
| `ZADARMA_API_KEY` | not used yet: the assistant's number is bought in Zadarma by hand and entered in the cabinet (the Phone channel) |
| `ZADARMA_API_SECRET` | the Zadarma API secret that signs the PBX's call notifications (`POST /v1/telephony/zadarma/notifications`); without it the notifications are refused and missed calls on the line (busy, no answer, hang-up) are not found |
| `META_APP_SECRET`, `META_VERIFY_TOKEN`, `WHATSAPP_SYSTEM_USER_TOKEN` | WhatsApp, Instagram and Messenger accept no webhooks; WhatsApp neither connects nor sends |
| `META_APP_ID` | the expiry of Meta channel tokens is not checked (the hourly job `check_channel_credentials` asks `debug_token` with `META_APP_ID` and `META_APP_SECRET`), and the System page does not show tokens about to expire |
| `TELEGRAM_PLATFORM_BOT_TOKEN`, `WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID`, `WHATSAPP_NOTIFICATION_TEMPLATE` | staff notifications in Telegram and WhatsApp do not go out (the contact shows why). E-mail and SMS to staff go through `SMTP_*` and `TWILIO_*` (like login codes); without them they are logged outside `production` |
| `WEB_PUSH_VAPID_PUBLIC_KEY`, `WEB_PUSH_VAPID_PRIVATE_KEY`, `WEB_PUSH_VAPID_SUBJECT` | no notifications to devices (Web Push): the "Turn on for this device" button is hidden; all three or none, and the key pair is checked at start-up |
| `WHATSAPP_REMINDER_TEMPLATE` | a booking reminder in WhatsApp goes out only when the customer wrote there in the last 24 hours |
| `WHATSAPP_BOOKING_CONFIRMATION_TEMPLATE` | the written booking confirmation with the link to its page goes to the guest in WhatsApp only when they wrote there in the last 24 hours (to the website chat and Telegram it always goes, to Messenger and Instagram also only within 24 hours) |
| `WHATSAPP_WAITLIST_TEMPLATE` | a freed place from the waitlist goes to the customer in WhatsApp only when they wrote there in the last 24 hours (otherwise to another connected messenger such as Telegram, and without one the place is offered to the next person on the list) |
| `WHATSAPP_REBOOKING_TEMPLATE` | a rebooking campaign's invitation goes out in WhatsApp only when the customer wrote there in the last 24 hours (otherwise in Telegram, and when nothing is possible it is skipped with the reason "window closed") |
| `WHATSAPP_OWNER_REPORT_TEMPLATE` | the owner cannot choose WhatsApp for digests and reports (it also needs `WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID`); e-mail, devices and Telegram work |
| `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` | no Google Calendar sync |
| `FLITT_MERCHANT_ID`, `FLITT_SECRET_KEY` | payments unavailable (502), the payment webhook is refused |
| `SUBSCRIPTION_PAUSE_ENABLED` | `false`: no seasonal pause; the pause card in Settings → Plan and invoices says a pause is not available yet, and the cancel dialog offers no pause (it does offer a lower plan and a one-off credit). The pause works from the next release: the `paused` status is still behind the closed release gate `subscription_pause`, and until it opens there is no pause even with `true`. Turn it on once the release that opened the gate is fully deployed (`docs/operations/deploys.md`) |
| `SELLER_LEGAL_NAME`, `SELLER_TAX_ID`, `SELLER_ADDRESS`, `SELLER_EMAIL` | the seller on invoices and receipts (PDF): by default only the name `Assistant Workshop`, without a tax number, address or e-mail. Lines of the address are separated by `\n` |
| `SELLER_COUNTRY_CODE`, `SELLER_TIME_ZONE` | `GE` and `Asia/Tbilisi`: the country whose VAT rules apply, and the time zone of invoice dates and of the year invoice numbers count in |
| `SELLER_INVOICE_SERIES` | `AW`: the invoice number series (`AW-2026-000042`); a new year starts counting at 1 |
| `PLATFORM_VAT_REGISTERED` | `false`: no VAT is charged and the invoice says "VAT not applicable". `true` (needs `SELLER_TAX_ID`, otherwise the start fails): buyers in the seller's country pay its VAT on top (Georgia 18 %), buyers abroad pay none (with a tax number, a reverse-charge note) |
| `PUBLIC_DEMO_BUSINESS_IDS` | no live demo on the landing page: in development the `SEED_DEMO_DATA` businesses answer, in `production` the hero shows a sample conversation. Ids of demo businesses separated by commas (one per main niche): visitors write to them without signing in, every turn is a sandbox (a booking or lead is a test record, nothing reaches staff, nothing is charged); limits of 20 messages an hour per conversation, 60 per network, 600 per demo business |
| `PUBLIC_DEMO_MESSAGES_PER_HOUR` | 300: how many messages all visitors together may send to the demo in an hour (1–100000), the ceiling of the public demo's model cost; beyond it 429 with `Retry-After` |
| `LEGAL_TEXTS_FINAL` | `false`: the public pages `/privacy`, `/terms`, `/dpa`, `/security` and `/contact` show a "draft" banner. `true` once a lawyer reviewed them and every field in square brackets is filled (a text with unfilled fields stays a draft) |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` | no model call log; the default address is `https://cloud.langfuse.com` (EU) |
| `LANGFUSE_CAPTURE_CONTENT` | `false`: message texts are not written to the log |
| `LANGFUSE_RAW_TEXT` | `false`: in the log's texts (with `LANGFUSE_CAPTURE_CONTENT=true`) phone numbers and e-mail addresses are replaced by `[phone]` and `[email]`; `true` keeps them as they are |
| `SENTRY_DSN` | unexpected errors only in the log |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.05`: the share of API requests whose trace goes to Sentry (0 to 1) |
| `PLATFORM_ALERT_TELEGRAM_CHAT_IDS`, `PLATFORM_ALERT_EMAILS` | platform alerts (`docs/operations/slo.md`) only in the log and on the admin System page. Telegram chats (ids separated by commas, the platform bot in the group; needs `TELEGRAM_PLATFORM_BOT_TOKEN`) and e-mail addresses (through `SMTP_*`) get them through the queue with retries |
| `PLATFORM_ALERT_COOLDOWN_MINUTES` | 60: an alert still firing comes again at most once an hour (5–1440) |
| `PIPELINE_WATCHDOG_SECONDS` | 60: once a minute one API process looks at the workers' heartbeats and the customer message queue and, when the workers are silent, sends the alert `worker_down` or `inbound_backlog` to the recipients above itself, without the job queue (0–3600, `0` turns it off; `docs/operations/runbooks/worker-down.md`) |
| `SUPPORT_WHATSAPP`, `SUPPORT_TELEGRAM`, `SUPPORT_EMAIL` | the cabinet's Help and support (the account menu, `GET /v1/support/contacts`) lacks that way to reach the platform's support. WhatsApp: a number in E.164; Telegram: a username (with or without "@"); e-mail: an address. The help center and the status page work without them |
| `APP_RELEASE`, `RENDER_GIT_COMMIT` | the build's version in Sentry reports and in the worker's heartbeat; Render sets `RENDER_GIT_COMMIT` itself, `APP_RELEASE` is for other platforms |
| `LOG_FORMAT` | `json` in `production` (one JSON line with `request_id`, `trace_id`, `business_id`, `conversation_id`, `channel`, `job_name`, `job_id`), `text` elsewhere |
| `METRICS_TOKEN` | no Prometheus metrics. With a token, the API's `GET /metrics` and the worker's port answer only `Authorization: Bearer <token>` (otherwise 401), `docs/operations/observability.md` |
| `WORKER_METRICS_PORT` | the worker exposes no metrics; with a port (for example 9464) and `METRICS_TOKEN`, its own `/metrics`: job pickup delay, queues and their age, dead jobs, model calls, the connection pool |
| `PROMETHEUS_MULTIPROC_DIR` | one uvicorn process keeps its series in memory; a directory for several processes (`WEB_CONCURRENCY` > 1), which `workshop api` creates itself |
| `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS` | no OpenTelemetry traces. With an OTLP/HTTP collector address (EU) and its authorization headers: spans of requests, jobs, SQL statements (name and table, no parameters), provider and model calls |
| `OTEL_SERVICE_NAME` | `workshop-backend`; set `workshop-api` and `workshop-worker` to tell the processes apart |
| `OTEL_TRACES_SAMPLE_RATE` | `0.1`: the share of traces started by this process that is kept (0 to 1); a continued trace follows its parent's decision |
| `THREADPOOL_SIZE` | 64 API request handlers at once (AnyIO threads); keep it above `DB_POOL_SIZE`: a request holds a connection for a moment, and waiting for one is better than a refusal |
| `DB_POOL_SIZE` | half of `THREADPOOL_SIZE`: the tenant pool's connections one process holds (a thread holds at most one). During a deploy old and new instances run together: twice the sum (both pools + 1 `LISTEN`) over API instances and workers, plus the backup and a migration, must stay under the database's limit (`tests/platform/test_connection_budget.py`, `docs/operations/capacity.md`) |
| `DB_PLATFORM_POOL_SIZE` | a quarter of `DB_POOL_SIZE`, at least 2: the platform pool's connections one process holds (sign-in, sessions, request limits, the job queue, the admin pages) |
| `DB_POOL_MIN_SIZE` | 2: the connections a process keeps open without load; the others close after `DB_POOL_MAX_IDLE_SECONDS` |
| `DB_POOL_MAX_IDLE_SECONDS` | 300: after this many idle seconds a spare connection closes (10 to 86400), so a load peak does not stay open |
| `TEST_CHAT_MAX_CONCURRENCY` | 4 owners' test chats at once per API process (1 to 64); the next gets 429 "try again in a few seconds" rather than a request thread |
| `WORKER_POLL_SECONDS` | the background worker looks for jobs every 15 seconds; a new job wakes the workers at once (`NOTIFY` on the channel `workshop_jobs`), polling only catches what was missed |
| `WORKER_INBOUND_POLL_SECONDS` | 2: the same for customer messages (the `inbound` lane), at most `WORKER_POLL_SECONDS`: a missed wake-up delays an answer by at most this many seconds |
| `WORKER_LANE_CONCURRENCY` | `inbound=8,outbound=4,default=2,autotests=2`: how many jobs of each lane one worker process runs at once (lanes not named keep their default, 1 to 64; `ops` defaults to 1, and until the release that opens the `ops_lane` gate it is not named here: otherwise a rollback cannot start the worker) |
| `WORKER_LANES` | empty: a worker process serves every lane. Otherwise only the named ones (separated by commas) and those lanes' periodic jobs: `render.yaml` runs workers that answer customers (`inbound,outbound`, two instances; the release that opens the `ops_lane` gate adds `ops`) and a batch worker (`default,autotests`), so no batch job can bring down the process that answers customers (`docs/operations/capacity.md`, "Worker roles") |
| `EMBEDDED_WORKER` | `auto`: the worker runs as a thread inside the API only with `APP_ENV=development` and an empty `DATABASE_URL`; `true` always (in `production` the start fails), `false` never ([`running.md`](running.md)) |
| `SEED_DEMO_DATA` | `false`: no demo data. `true` (development only; in `production` the start fails): the API creates the demo businesses once at start-up, a restaurant in Tbilisi and a salon in Berlin with a month of conversations, bookings, leads and handoffs; sign in with `+995 555 00 00 01` or `demo@example.com`, the code is in the API log ([`running.md`](running.md)) |
| `PORT`, `FORWARDED_ALLOW_IPS` | read by the image's start-up, not by the application: the uvicorn port (8000) and the trusted proxies' addresses (`127.0.0.1`); `Dockerfile`, `docker-compose.yml` and `render.yaml` set them |

## Webhook addresses

The addresses for the providers' dashboards are `APP_BASE_URL` followed by
a path: the Meta webhook `/v1/channels/meta/webhook`; the ElevenLabs
post-call webhook `/v1/voice/webhooks/post-call`; the Google redirect URI
`/v1/integrations/google-calendar/callback` (the cabinet finishes the
connection, so without `CABINET_BASE_URL` Google Calendar is off); the Flitt
callback `/v1/payments/flitt/webhook`.
