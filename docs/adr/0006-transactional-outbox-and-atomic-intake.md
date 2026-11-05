# 0006. A transactional outbox for everything customers receive, and atomic intake

- Status: Accepted
- Date: 2026-10-22

## Context

The assistant talks to customers through providers that fail in every way a
network can: Meta and Telegram answer 429 and 5xx, time out, revoke tokens;
ElevenLabs and the SMS providers do the same. Early use cases called a
channel's `send` directly in the middle of their work. A provider error then
either failed the whole turn after the database had changed, or was
swallowed, and a customer was left without the booking confirmation or the
staff answer the cabinet showed as sent. Retries were ad hoc, a retry could
send twice, and nothing told the cabinet whether a message arrived.

Intake had the mirror problem. A webhook stored the inbound event and then
queued the job that answers it; a crash between the two writes left an event
nobody would process, and the provider, having received 200, would never
redeliver it.

## Decision

- **Outbox.** Every message to a customer or to staff is a row of the
  outbound collection (`OutboundMessageDocument`) with an idempotency key
  that names its cause (a conversation and reply id, a booking with its kind
  and start, a call id and kind). `queue_outbound_message`
  (`app/use_cases/shared/outbox_queue.py`) stores the row and its
  `deliver_outbound` job in one unit of work; a key queued before is not
  queued again.
- **Delivery.** Only the outbox (`app/use_cases/channels/outbox/`) sends, on
  the `outbound` lane of the worker. Messages to one recipient leave in
  order; parts already sent are never repeated; provider errors are
  classified (429 waits for `Retry-After`, 5xx and network errors retry with
  exponential backoff and jitter up to 8 attempts, a 4xx or a revoked token
  is final and puts the channel in `ERROR`). Each attempt records a delivery
  state the cabinet shows under the message, and an answer that never left
  opens a handoff so the customer is not left alone.
- **Atomic intake.** A webhook stores its inbound event and the job that
  processes it in one unit of work (`store_and_queue`,
  `app/use_cases/shared/inbox_queue.py`): a crash leaves neither, and the
  provider redelivers. A redelivered event is not stored twice; processing
  an event twice is harmless. `sweep_stale_inbound_events` finds the rare
  event whose job was lost anyway (an old release, a job removed by hand).
- **Enforcement.** `tests/architecture_policy/test_customer_messages_go_through_the_outbox.py`
  fails when a use case outside the outbox (and the channel connection
  check) calls a sending contract. Fault-injection tests prove that a crash
  between the writes leaves neither.

## Consequences

- A provider outage delays messages instead of losing them, a retry never
  sends twice, and the cabinet shows honest delivery states.
- Sending is asynchronous: a use case cannot read a provider's answer, and a
  new kind of message needs its key, its job handling and its delivery
  follow-ups. Rows of a new kind are written only by the release that reads
  them, so a rollback waits until they left (`docs/operations/deploys.md`).
- The unit of work is optional in the use case's signature (`None` in memory,
  where there is no transaction to group writes in); the Postgres wiring must
  pass it, which the fault-injection tests check for the paths above.
- One recipient's messages are serialized, so a stuck message holds back the
  next ones until it is delivered or given up; the per-provider circuit
  breakers and bulkheads of the outbound lane keep one failing provider from
  holding back the others.
