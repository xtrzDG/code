# Log inventory

What the platform logs, with which fields, where it goes and how long it
is kept (LOG-01, LOG-03; OWASP ASVS 5.0 V16.1.1). Every record is UTC.
`tests/security/test_log_inventory.py` keeps this list complete: a new
named logger, security event, log context field or audit entry field
fails it until it is listed here.

## Records and where they go

| Record | Written by | Fields | Destination | Retention |
| --- | --- | --- | --- | --- |
| Application lines (every logger, uvicorn's included) | API, workers, jobs (`app/utilities/observability/logging_setup.py`) | `time`, `level`, `logger`, `thread`, `message`, the log context fields, the line's own fields (`log_fields`), `exception`/`stack` | stdout as one JSON object per line (`LOG_FORMAT=json`, production refuses `text`); Render keeps a short tail, a Render Log Stream ships it to the EU log store | 30-90 days |
| Security events, logger `app.security` | `app/utilities/observability/security_events.py` | `security_event`, `path` (route template), `reason`, `client_network` (/24 or /48), `actor`, and where it applies `provider`, `method`, `status`, `job_id` | as the application lines, routed to a separate stream of the log store | 12 months, append-only |
| Payment events, logger `app.payments` | `app/use_cases/billing/payment_state_events.py` | `payment_order_opened`, `payment_state_changed`, `payment_reconciliation_mismatch` with ids, provider, purpose and statuses | as the application lines | 12 months |
| Widget errors, logger `app.widget` | the website widget's error reports without a Sentry DSN (`sentry_error_reporting_facilitator.py`) | message and the log context | as the application lines | 30-90 days |
| Access lines, logger `uvicorn.access` | uvicorn, with session keys redacted (`app/gateways/http/access_log_redaction.py`) | method, path, status, client | as the application lines | 30-90 days |
| Audit log (`audit_logs`, `AuditLogEntryDocument`) | use cases, appended through `AuditLogRepository` | see "Audit entry fields" | Postgres in the EU: append-only (trigger and revoked UPDATE/DELETE/TRUNCATE, migrations 1193 and 1200), hash-chained per business and for the platform, checked daily (`audit_chain_broken` alert) | at least 365 days (`app/utilities/compliance/audit_retention.py`) |
| Error reports | `SentryErrorReportingFacilitator` | scrubbed event (no bodies, headers, cookies, users, local variables), the log context as tags | Sentry, EU region | Sentry's plan retention |
| Model call traces | `LlmGenerationTrace` (Langfuse) | metadata only unless content tracing is on; ids of the log context | Langfuse, EU region | 30 days |

## Log context fields

Every application line, error report and trace carries the fields of the
log context that are set (`app/schemas/dto/observability.py` `LogContext`):

- `request_id`: the request (X-Request-ID, echoed in the response), also on
  the jobs it queued;
- `trace_id`: the distributed trace;
- `business_id`, `conversation_id`, `contact_id`, `channel`: what the line
  is about (ids only, never texts or contact data);
- `job_name`, `job_id`: the background job.

No line carries a client address or a User-Agent: those exist only in the
request origin (`app/utilities/observability/request_origin.py`), which
audit entries and the security lines' `actor` read.

## Security events

`security_event` values (logger `app.security`):

- `webhook_delivery_refused`: a webhook unsigned, badly signed, stale or
  flooding (`provider`, `status`);
- `authorization_denied`: a 401 or 403 (`status`);
- `rate_limit_triggered`: a 429, at most one line a minute per route and
  network;
- `request_body_refused`: a body too large or nested too deep;
- `request_deadline_exceeded`: a request past its deadline (504);
- `outbound_fetch_refused`: a server-side fetch refused by the SSRF guard;
- `job_tenant_mismatch`: a queued job whose payload names another business.

`actor` is the signed-in person's user id (a pseudonym; for an API key,
the owner who made it), `anonymous` for a request without accepted
credentials, `system` for work outside any request.

## Audit entry fields

`id`, `business_id` (none for a person's own security events), `actor_id`,
`action`, `entity`, `entity_id`, `ip_address`, `record_count`, `reason`,
`security_event`, `created_at`; since version 7 `user_agent`,
`request_id` and `outcome` (`success` or `failure`), filled on append from
the request being served where the use case named none
(`app/utilities/compliance/audit_origin.py`): the request id always, the
address and User-Agent only for a person's own action or a security
event; and the chain fields `chain_key`, `chain_position`, `prev_hash`,
`entry_hash`. The hash (format 1) covers the fields of version 6; the
version 7 fields are protected by the append-only table and join the hash
with a later format, once the release before reads them.

## Encoding

Production writes JSON only: `json.dumps` escapes CR, LF and every other
control character, and the formatter escapes NEL, LINE SEPARATOR and
PARAGRAPH SEPARATOR, so a value never starts a line of its own
(`tests/security/test_log_injection.py`). Messages have secrets, card and
account numbers and contact details masked (`redact_log_text`). Stored
User-Agents keep printable ASCII only.

## Owner steps

- Create the Render Log Stream to an EU log store with two retention
  classes: `app.security` and `app.payments` 12 months, append-only or
  immutable; everything else 30-90 days. Access limited to the team; the
  application's credentials cannot delete logs (the app only writes to
  stdout). Add the store to the sub-processor registry.
- Alerts of the log store: a burst of `webhook_delivery_refused` per
  provider and any `job_tenant_mismatch`. The platform's own
  `webhook_signature_failures` alert counts the refusals too
  (`ops/alerts/`).
