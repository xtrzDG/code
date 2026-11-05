# Service Level Agreement (draft)

Draft (needs_review). Prepared by the team for the owner to decide and
the lawyer to review; it is not part of what businesses accept until it
is adopted as a legal text with its own version (`docs/legal/README.md`)
and the terms of service refer to it (today they say there is no
guaranteed level of availability, terms 9.1). The figures are what the
platform can honour with its present setup: they promise less than the
internal objectives (`docs/operations/slo.md`,
`docs/operations/backup-restore.md`), so a normal month keeps a margin.
`tests/legal/test_sla_draft.py` keeps the draft's figures no stricter than
the internal targets.

## 1. Scope

This agreement covers the assistant answering the Client's customers in
chat (the website chat, the hosted chat page and the messaging channels
the Client connected) and on the phone, the booking pages, and the
Client's cabinet. It does not cover the messaging platforms, telephone
networks, payment providers or the Client's own systems, nor features
marked as beta.

## 2. Availability

| Service | Monthly availability |
| --- | --- |
| The assistant answers chats (a reply or a handoff to the team) | **99.5%** |
| The assistant answers calls, or the call is put through to the Client's phone | **99.0%** |
| The cabinet and the booking pages | **99.5%** |

A month's availability is the share of minutes in which the service
worked, measured by the Provider's monitoring and shown on the status
page. Not counted as unavailable: maintenance announced on the status page
at least 3 days ahead (at most [4] hours a month, outside 08:00-23:00
Europe/Rome); outages of the providers named in scope 1 that the Provider
cannot route around; the Client's own settings (a paused assistant, a
channel turned off, an unpaid subscription); misuse or attacks the Client
caused.

## 3. Fallback for calls

When the voice assistant cannot answer, calls to a number rented through
the service are put through to the Client's forwarding phone. The Provider
switches this fallback on **within 15 minutes** of detecting an outage of
the voice assistant, and the status page says so. A Client whose own
operator forwards calls to the assistant is told how to switch that
forwarding off (help article "Call forwarding").

## 4. Data recovery

| Objective | Commitment |
| --- | --- |
| Recovery point (RPO): data that may be lost in a failure of the database | at most **15 minutes** |
| Recovery time (RTO): until the whole service works again after such a failure | at most **4 hours** |
| Loss of the hosting provider's account or region | data of the last **24 hours** at most, restored within **8 hours** |

Backups are encrypted, kept at a second provider in the EU and proven by
a restore test every week.

## 5. Support

| | Commitment |
| --- | --- |
| Support hours | Monday to Friday, 09:00-18:00 Europe/Rome, except Italian public holidays |
| Channels | the cabinet's support page and the support e-mail |
| First response: the service is down for the Client (critical) | **1 hour, every day at any hour** |
| First response: a feature does not work, no workaround (high) | 4 support hours |
| First response: anything else | 1 business day |
| Status updates during a critical incident | at least every hour on the status page |

## 6. Service credits

If a month's availability of the chat or call service falls below its
commitment, the Client receives a credit on the next invoice, on request
within 30 days of the month's end:

| Monthly availability | Credit (of that month's subscription fee) |
| --- | --- |
| below the commitment, at least 99.0% (chat) or 98.0% (calls) | 10% |
| below 99.0% (chat) or 98.0% (calls), at least 95.0% | 25% |
| below 95.0% | 50% |

Credits are the Client's only remedy for unavailability under this
agreement, are capped at 50% of the month's fee, and are not paid out in
cash. [Liability beyond credits: as the terms of service set it.]

## 7. Reporting

The status page shows each component's state and 90 days of history.
On request, the Provider sends the month's availability figures within 10
business days of the month's end.

## Open points for the owner and the lawyer

- Adopt the figures (or lower them) and decide the maintenance allowance
  in section 2.
- Make the SLA a legal text with its own version, accepted with the terms,
  in Italian and English; refer to it from terms 9.1.
- Section 3 relies on the forwarding phone the Client sets; a Client
  without one gets no call fallback.
- Section 5's critical response at any hour needs the paging rota of
  `docs/operations/on-call.md` staffed.
