# Provider circuits: one provider browns out

**Shows on:** the "Provider circuits" card of `/admin/system` (a circuit
open or trying again), `outbound_failures`, owners noticing slow replies in
one channel only.

Every provider the workers send through has a circuit breaker in each
worker process (`CircuitBreakerFacilitator`, the same rule as the language
models in [llm-outage](llm-outage.md)):

| Circuit | Guards |
| --- | --- |
| `provider:meta` | WhatsApp, Messenger, Instagram replies; WhatsApp templates (staff and customers) |
| `provider:telegram` | the businesses' Telegram bots |
| `provider:platform_bot` | the platform bot: staff notifications and platform alerts by Telegram |
| `provider:twilio_sms` | staff SMS and missed-call text-backs |
| `provider:smtp` | e-mail: staff notifications, invoices, platform alerts by e-mail |
| `provider:flitt` | creating a checkout, stopping automatic charges |

Web push has none: it reaches many push services, and one being down is not
the others'. Login codes do not go through the circuits.

## How it works

- **5 failures within 60 s open a circuit.** A failure is a timeout, a
  connection error or a 5xx. A refusal (4xx), a rate limit, a revoked token
  or a business's own missing setting is an answer, not an outage: it never
  opens a circuit.
- **Open:** a send fails at once without a network call. The outbox keeps
  the message and tries again when the circuit lets a trial through
  (`Retry-After` = the circuit's remaining wait, at least the usual
  backoff); the attempt counts, so a provider down for longer than the
  outbox's 8 attempts (about 21 minutes) still ends in a dead letter and
  the usual handoff.
- **After 30 s one trial goes through (half-open).** It closes the circuit
  when the provider answers, opens it for another 30 s when it fails.
- **Bulkheads:** each provider may hold at most half of a worker's
  `outbound` threads (2 of the default 4). A send that finds its provider's
  slots taken does not wait: its job comes back in about 4 s without
  spending an attempt. A provider that hangs for its whole read timeout
  (10 s; 3 s to connect) therefore holds two threads, and the other
  providers' sends keep going on the other two.
- **Platform alerts** run in their own `ops` lane (1 thread per worker),
  so the alert about an outage never waits behind the sends it holds up.
  The lane is behind the release gate `ops_lane`: until the release after
  this one opens it, alerts use the `outbound` lane and rely on the
  bulkheads.

Each worker reports its circuits with every pulse; the card sums them up
over the live workers (stale pulses left out): the worst state, in how many
workers a circuit is not closed, the failures of the last minute and since
when the earliest is open. Grafana's "Resilience" row has the same per
process (`workshop_circuit_breaker_state`).

## Check

1. Which provider: the card, then that provider's status page
   (metastatus.com, status.twilio.com, Telegram's
   [@BotNews](https://t.me/BotNews), the mail host, Flitt).
2. All workers or one? An open circuit in one worker of two points at that
   worker's network (egress, DNS) rather than the provider.
3. The logs: `Circuit provider:<name> opened (5 failures within 60 s)`, then
   `Circuit provider:<name> closed: its trial call succeeded.`

## Mitigate

- **The provider is down:** nothing to switch. Messages wait in the outbox
  and go out once the trial succeeds. Owners: the incident template in
  `../incident.md` (messages are kept, nothing is lost). Meta and Telegram
  specifics: [meta-outage](meta-outage.md), [telegram-outage](telegram-outage.md).
- **One worker only:** restart that worker (`workshop-worker`); its
  circuits start closed, and its jobs move to the other worker meanwhile.
- **Platform alerts stuck:** they need the platform bot or SMTP; while
  `provider:platform_bot` is open, alerts by e-mail still go out, and the
  other way round. Keep `/admin/system` open.

## Fix and recover

- Circuits close by themselves after a successful trial; no restart.
- Dead letters of `deliver_outbound` from the outage: retry them on
  `/admin/system` once the circuit is closed; each message is sent once.

## Afterwards

- Postmortem for SEV2 if owners noticed; note how long the circuit stayed
  open and whether the 2-of-4 share held the other providers' replies.
- Test: `tests/resilience/test_send_bulkheads.py` (Meta hanging 10 s:
  Telegram replies and platform alerts out within 2 s; five timeouts open
  the circuit, a trial follows 30 s later; every message delivered once).
