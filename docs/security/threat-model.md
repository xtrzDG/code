# Threat model

Assistant Workshop answers the customers of small businesses on their
behalf and keeps their conversations, contacts, bookings and call
recordings. This document names what we protect, where data crosses a trust
boundary, and, threat by threat (STRIDE), the mitigation with the code that
implements it and the test that proves it. Every path below is checked to
exist by `tests/legal/test_security_documents.py`, so a moved file breaks
the build instead of silently breaking the model.

Reviewed: 2026-10-05. Review it with every new external integration, every
new kind of personal data and at least once a quarter, together with the
access review (`docs/security/access-review.md`).

## Assets

| Asset | Why it matters |
| --- | --- |
| Customers' conversations, contacts, bookings and call recordings | Personal data of people who never signed up with us (DPA section 3) |
| Owner and staff accounts, sessions and authenticators | They open every tenant's data and settings |
| Channel credentials (WhatsApp, Telegram, Instagram, Messenger, calendar tokens) | They let an attacker speak as the business |
| Platform admin and support access | Read access across tenants |
| The language model's instructions and tools | They decide what the assistant says and books |
| Billing records and invoices | Money and tax obligations |
| Backups and the encryption keys | A copy of everything |

## Trust boundaries

```
 Customers ──(messengers, widget, phone)──▶ [B1 webhooks & widget API] ──┐
                                                                          ▼
 Owners/staff ─▶ [B2 cabinet: Next.js BFF] ─▶ [B3 API] ─▶ [B5 Postgres, RLS per business]
                                                │   │
 Platform admins ─▶ [B8 admin & support access]─┘   ├─▶ [B6 sub-processors: LLM, voice, e-mail, SMS, S3]
                                                    └─▶ [B7 model output ▶ tools]
 Source code ─▶ [B9 CI/CD and dependencies] ─▶ images on Render
```

| Boundary | What crosses it | Who is on the other side |
| --- | --- | --- |
| B1 Webhooks and the widget API | Customer messages, call events, payment results | Anyone on the internet, messaging platforms, Flitt, ElevenLabs, Zadarma |
| B2 Cabinet (BFF) | Owners' and staff's clicks, the session cookie | Browsers, including hostile pages in other tabs |
| B3 API | Bearer tokens, JSON bodies | The BFF, the widget, scripts |
| B5 Database | Every tenant's rows | The API and the worker, scoped per business |
| B6 Sub-processors | Messages to the model, audio, e-mail and SMS, recordings | The providers listed in DPA section 8 |
| B7 Model output | Replies and tool calls written by a language model | Prompt-injected customer text |
| B8 Platform administration | Cross-tenant reads, support sessions | The platform team |
| B9 Supply chain | Dependencies, actions, images | Package registries, GitHub Actions |

## STRIDE

| # | Threat | STRIDE | Boundary | Mitigation | Code | Tests |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Someone guesses a sign-in code | S | B3 | Each check takes one of the challenge's attempts atomically before comparing; checks limited per network and per challenge; one session per right code | `app/use_cases/users/otp_login/login_challenge_consumption.py`, `app/use_cases/users/otp_login/login_check_limits.py` | `tests/users/test_otp_attempt_race.py`, `tests/users/test_otp_check_limits.py` |
| 2 | SMS pumping or code flooding to premium numbers | S, D | B3, B6 | Premium and satellite prefixes refused, per-country caps, budgets for verified users, Turnstile on risky requests, alerts | `app/use_cases/users/otp_login/login_code_limits.py`, `app/use_cases/users/otp_login/login_risk_signals.py`, `app/clients/turnstile/turnstile_verification_client.py` | `tests/users/test_login_code_caps.py`, `tests/users/test_login_bot_check.py` |
| 3 | A stolen session or one-factor admin takes over tenants | S, E | B2, B8 | __Host- session cookie, idle and absolute expiry, device list with revoke, authenticator mandatory for platform admins, step-up for sensitive actions | `web/src/server/sessionCookie.ts`, `app/utilities/security/session_expiry.py`, `app/utilities/security/require_recent_authentication.py`, `app/utilities/security/two_factor_policy.py` | `web/src/server/sessionCookie.test.ts`, `tests/users/access/test_device_sessions.py`, `tests/users/mfa/test_mfa_sign_in.py`, `tests/users/mfa/test_admin_access.py` |
| 4 | A forged webhook injects messages or payments | S, T | B1 | Telegram secret token, Meta X-Hub-Signature-256, ElevenLabs HMAC and Flitt signatures checked before parsing; the business comes from the server-side channel lookup | `app/utilities/channels/webhook_signatures.py`, `app/utilities/channels/voice_webhook_auth.py`, `app/clients/flitt/flitt_protocol.py` | `tests/channels/test_webhook_signatures.py`, `tests/channels/test_webhook_isolation.py` |
| 5 | One tenant reads or changes another tenant's data | I, E | B3, B5 | Every business route authorizes the member; repositories read by business id; Postgres row-level security keyed by business; storage scope fails closed | `app/use_cases/authorize_business_access_use_case.py`, `app/repositories/business_scoped_repository.py`, `app/utilities/storage/storage_scoping.py` | `tests/platform/test_authorization_matrix.py`, `tests/storage/test_row_level_security.py`, `tests/storage/test_fail_closed_scope.py` |
| 6 | Platform support reads a client's data without reason or trace | I, R | B8 | Time-boxed, reasoned, read-only support grants the owner sees in a banner; every admin access audited | `app/use_cases/admin/access/`, `app/use_cases/shared/support_access.py` | `tests/users/access/test_support_access.py`, `tests/compliance/test_audit_log.py` |
| 7 | An export, erasure or view of personal data cannot be traced to a person | R | B3 | Audit log of views (the same view within 5 minutes counted on one entry), exports, erasures, team and admin actions, with actor and address; a full export opens only through a one-time link of the owner who asked, at most three times, and every owner is told of each download. The log is a trace kept by the platform, not non-repudiation: its rows live in the application's own database and are neither signed nor append-only (see accepted risks) | `app/repositories/compliance_repositories.py`, `app/use_cases/exports/download_business_export_use_case.py` | `tests/compliance/test_audit_log.py`, `tests/compliance/test_audit_view_counts.py`, `tests/privacy/test_export_download_links.py`, `tests/privacy/test_contact_trace_erasure.py` |
| 8 | Prompt injection makes the assistant leak data or act | T, I, E | B7 | Customer text is untrusted input; injection brake; reply guard checks claims against the business's knowledge; tools validate inputs and take the business from the conversation, never from model output | `app/utilities/reply_guard/`, `app/use_cases/conversations/tools/` | `tests/brain/test_injection_brake.py`, `tests/brain/test_injection_signals.py`, `tests/brain/test_tool_runner_inputs.py` |
| 9 | The website import is used to reach internal hosts (SSRF) | I, E | B6 | Only public addresses after DNS resolution, re-checked on redirects, size and time limits | `app/clients/http/url_vetting.py`, `app/clients/http/safe_http_fetcher.py` | `tests/web_fetching/test_ssrf_guard.py`, `tests/web_fetching/test_safe_fetch_limits.py` |
| 10 | Stolen database dump reveals channel tokens or recordings | I | B5, B6 | Channel and calendar tokens sealed with the key ring; recordings encrypted per business in object storage; key rotation | `app/adapters/security/secret_cipher_adapter.py`, `app/utilities/security/recording_encryption.py`, `app/utilities/security/key_ring.py` | `tests/security/test_key_ring.py`, `tests/compliance/test_recording_encryption.py` |
| 11 | Backups leak or cannot be restored | I, D | B6 | Backups encrypted with age before leaving Render, private key held only by the restore drill and escrow, retention 30 days / 12 months | `app/use_cases/maintenance/backups/` | `tests/backups/test_backup_keys_and_retention.py`, `tests/backups/test_age_format.py` |
| 12 | Cross-site attacks on the cabinet (XSS, clickjacking) | T, I | B2 | Nonce-based CSP, frame-ancestors none, COOP and CORP, HSTS; Markdown rendered as text | `web/src/server/contentSecurityPolicy.ts`, `app/gateways/http/middleware/security_headers_middleware.py` | `web/src/server/contentSecurityPolicy.test.ts`, `web/e2e/security.spec.ts`, `tests/security/test_api_security_headers.py` |
| 13 | Oversized bodies, floods or a copied widget run up the service and its bills | D | B1, B3, B6 | Per-route body limits; shared rate limits for the widget and sign-in; generic limits per person and per address (429 with Retry-After); owner action limits (test chat, menu import, autotests); allowed websites per business for the website chat; daily spend limits per business (cheaper model, then requests only) and the platform's spend alerts; call length and silence caps; bounded model concurrency and turn slots | `app/gateways/http/middleware/body_size_limit_middleware.py`, `web/src/server/bodyLimits.ts`, `app/registries/limits/request_rate_limit_registry.py`, `app/gateways/http/middleware/anonymous_request_limit_middleware.py`, `app/use_cases/spend_guard/check_business_spend_use_case.py`, `app/use_cases/spend_guard/check_widget_origin_use_case.py` | `tests/security/test_api_body_limits.py`, `web/src/server/bodyLimits.test.ts`, `tests/channels/test_widget_rate_limits.py`, `tests/platform/test_turn_slots.py`, `tests/spend_guard/test_request_limits.py`, `tests/spend_guard/test_spend_limits.py`, `tests/spend_guard/test_widget_origins.py` |
| 14 | Personal data ends up in logs | I | B3 | Access log redaction of tokens and query values | `app/gateways/http/access_log_redaction.py` | `tests/platform/test_access_log_redaction.py` |
| 15 | A new provider receives data the DPA does not name | I | B6 | Every client package maps to a sub-processor entry; changes announced 30 days ahead and audited | `app/registries/legal/subprocessor_catalog.py`, `app/use_cases/legal/send_subprocessor_notices_use_case.py` | `tests/legal/test_client_modules.py`, `tests/legal/test_subprocessor_notices.py` |
| 16 | A compromised dependency or action ships in an image | T, E | B9 | Actions pinned to SHAs; pip-audit, npm audit, gitleaks, bandit, CodeQL, Trivy in CI; Dependabot | `.github/workflows/ci.yml`, `SECURITY.md` | `tests/platform/test_ci_workflows.py` |

## Accepted risks and follow-ups

- Single region: the service, its database and the language model run in the
  EU only; a regional outage stops the service (docs/operations/slo.md).
- Sub-processors outside the EEA (Telegram, Twilio, Anthropic when selected)
  rely on transfer mechanisms still to be confirmed (docs/LAUNCH.md, legal
  blocker).
- No external penetration test yet: commission one before the first paying
  clients outside the pilot, and after every major change of the trust
  boundaries above.
- Row-level security can be switched off by the application itself: the
  policies let any session that sets the `app.bypass_rls` setting read every
  tenant (the platform-wide jobs use it), and the application's database role
  may set it. RLS therefore guards against query mistakes, not against a
  compromised application or a leaked database password. Closed by
  W18-DB-ROLES-PASSKEYS (separate roles; the bypass only for the jobs' role).
- The audit log is mutable: its rows sit in the same database the application
  writes, the application role can change or delete them, and repeated views
  are counted by updating an entry. It is a trace, not evidence a person
  cannot dispute (row 7). Closed by R13-AUDIT-TRAIL (append-only, hash-chained
  log shipped outside the application's database).
- The website chat's allowed sites are opt-in: a business without a list
  still serves its chat on any site, and the check reads `Origin` (else
  `Referer`), which only browsers set honestly. A script without either
  header passes; the widget's limits per visitor, network and business and
  the business's daily spend limit bound it (row 13).
- Spend limits are checked before each model turn and call against the
  business's day: a turn or call already under way finishes past the
  limit, and a cost a provider reports late is counted at the planned
  price until it arrives. The platform's budget only alerts (80%); the
  stop is each business's hard limit and the providers' own spend limits
  (docs/operations/runbooks/spend-spike.md).
- No account deletion in the cabinet: a person cannot delete their account,
  nor an owner the business with all its data; it is done by the platform
  team on request (DPA section 13). Closed by R15-ACCOUNT-DELETION.
