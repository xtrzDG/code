# Login codes and sign-in protection

Owners and staff sign in with a one-time code sent to their phone number or
e-mail address; platform admins add an authenticator app. The use cases are
in `app/use_cases/users/` (`otp_login/`, `mfa/`), the providers in
`app/clients/` and `app/adapters/`.

## Delivery

A code goes out through the first channel of the phone number's country list
(SMS, WhatsApp, Telegram) that has a configured provider; the channel the
person asked for goes first. If a provider refuses, the same code goes out
through the next channel, and the answer names the channel that worked.
Sign-in by e-mail needs SMTP. `GET /v1/auth/login-options?country_code=GE`
tells the sign-in page which of the country's channels work right now (the
country's list intersected with the configured providers) and whether
e-mail sign-in works: the cabinet offers only those and explains when there
is no way in.

| Channel | Provider | Variables |
| --- | --- | --- |
| SMS | Twilio Programmable Messaging | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` or `TWILIO_MESSAGING_SERVICE_SID` |
| Telegram | Telegram Gateway API (`sendVerificationMessage`, paid per delivered code) | `TELEGRAM_GATEWAY_API_TOKEN` |
| WhatsApp | an "authentication" template of the WhatsApp Cloud API (the code in the text and a copy button) | `WHATSAPP_OTP_PHONE_NUMBER_ID`, `WHATSAPP_OTP_TEMPLATE`, `WHATSAPP_OTP_TEMPLATE_LANGUAGES`, `WHATSAPP_OTP_ACCESS_TOKEN` (defaults to `WHATSAPP_SYSTEM_USER_TOKEN`) |
| E-mail | any SMTP server (STARTTLS or TLS) | `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` |

SMS and e-mail texts are in the person's language (English, Russian,
Georgian, Ukrainian, Turkish, Hebrew, Arabic, German, French, Spanish;
English otherwise), always name the service (Assistant Workshop), and an SMS
fits one part. Telegram and WhatsApp write their messages themselves. A
provider is configured completely or not at all: incomplete settings stop
the start-up.

Every code is a paid message, so sending is limited: the same number and
channel again only after 30 seconds (switching channel, "no code? send it by
SMS", works at once), and at most `OTP_SENDS_PER_DESTINATION_PER_HOUR` (5)
codes per number or address, `OTP_SENDS_PER_IP_PER_HOUR` (10) per client
address and `OTP_SENDS_PER_HOUR` (300) in total per hour; beyond a limit the
answer is 429. The check and the reservation of a send happen under one lock
before the provider is called, so parallel requests cannot pass a limit
together (with a database, a platform-wide `pg_advisory_xact_lock` in the
same transaction as the reservation, shared by every API instance). When
every provider refuses, the details go to the log and the person gets a
general answer that names no provider or setting.

In `development` and `test`, channels without a provider write the code to
the log (`OTP_LOG_CODES`, on by default): the newest line `Login code NNNNNN
via <channel>` of the API log is the code to type. In `production` codes are
never logged (`OTP_LOG_CODES=true` stops the start-up), a channel without a
provider is not offered, and without any provider the API logs an error at
start-up and sign-in answers 502 with an explanation.

## Protection

- **Guessing a code.** Every check first takes one of the
  `OTP_MAX_FAILED_ATTEMPTS` attempts atomically (a row lock in Postgres, a
  collection lock in memory) and only then compares the code, so even 40
  parallel guesses are compared at most five times; the right code closes
  the challenge by compare-and-swap and opens one session. Checks are
  limited by one policy for every kind of code
  (`app/use_cases/users/check_limit_policy.py`):
  `OTP_VERIFIES_PER_IP_PER_10_MINUTES` (20) per client network, shared by
  login codes and second factors, and 10 per challenge or sign-in step in 10
  minutes (429 with `Retry-After`).
- **SMS pumping.** Premium-rate, shared-cost, personal and universal numbers
  (by libphonenumber's metadata), satellite and international networks and
  the ranges of `OTP_DENIED_PHONE_PREFIXES` get no code. New numbers of one
  country get at most `OTP_SENDS_PER_COUNTRY_PER_HOUR` (100) codes an hour.
  Verified people spend a separate budget,
  `OTP_SENDS_TO_VERIFIED_USERS_PER_HOUR` (300), so a flood of codes to new
  numbers never locks returning owners out. When any shared limit trips, the
  platform admins (`PLATFORM_ADMIN_EMAILS`, with SMTP configured) get an
  e-mail and Sentry an event, at most once an hour per limit.
- **Bot check.** With `TURNSTILE_SITE_KEY` and `TURNSTILE_SECRET_KEY`
  (Cloudflare Turnstile) a risky code request (a new number or address, an
  address that already asked for 3 codes this hour, half of the shared
  budget used, a country of `OTP_HIGH_RISK_COUNTRIES`) gets 403 with the
  reason `challenge_required` and the widget's key; the sign-in page shows
  the check and repeats the request with its token. A returning owner on a
  quiet day never sees it. When Cloudflare does not answer, a risky request
  is refused (fail closed). Without the keys the check is off (development,
  tests).
- **Second factor.** An authenticator app (TOTP, RFC 6238) is set up in
  Account → Security; its secret is encrypted with `ENCRYPTION_KEYS`. A code
  works once; recovery codes are stored only as HMACs and work once too; the
  second sign-in step lives 5 minutes and allows 5 attempts. A platform admin
  signs in only with the app, and the admin's role (SUPER, SUPPORT_READONLY,
  BILLING) is read from the admin team (`platform_admins`) on every request;
  the `PLATFORM_ADMIN_*` lists only create the first SUPER admin. Exporting
  and deleting a contact's data, team changes, connecting a channel (except
  the website chat), entering a client's cabinet and rotating the key need a
  sign-in or confirmation no older than `STEP_UP_MAX_AGE_SECONDS` (401 with
  the reason `step_up_required`; the cabinet asks for a code and repeats the
  action).
- **Sessions and devices.** A session idle for 7 days ends
  (`SESSION_IDLE_TIMEOUT_SECONDS`); an admin's after 12 idle hours and at
  most a day after sign-in. The time and address of last use are written at
  most every 5 minutes. Account → Security lists the devices and ends one or
  all the others; a sign-in from a new device sends a personal notice.
- **Support in a client's cabinet.** An admin enters a cabinet only with a
  reason: 60 minutes, read-only; the owner sees a banner and gets a notice;
  the start and end (`support_access_start`, `support_access_end`) are in the
  audit log with the address. Changes need the owner's permission, which ends
  by itself, and a SUPER admin; exporting a contact's data counts as a
  change.

The threat model behind these rules is
[`docs/security/threat-model.md`](../security/threat-model.md).
