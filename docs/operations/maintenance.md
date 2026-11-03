# Maintenance windows, owner notices and postmortems

When changes that could interrupt service are made, how the businesses are
told, the recurring operational calendar, and how lessons are tracked.
All times are Europe/Rome.

## When customers are busiest

The businesses answer their customers at the busiest moments of
hospitality, so planned work avoids them:

- **Every day**: 11:30-15:00 (lunch) and 18:30-23:30 (dinner, evening
  bookings), when restaurants and salons take most calls and messages.
- **Weekends**: Friday 17:00 to Sunday 23:30.
- **Freeze periods**: 20 December-7 January, the week before Easter to
  Easter Monday, 1-25 August (Ferragosto and the hotels' peak), 14 February.
  Only fixes ship then (the error budget policy of `docs/operations/slo.md`).

## The maintenance window

**Tuesday or Wednesday, 04:30-06:00.** The nightly backup (01:17 UTC) has
finished, no restaurant or salon is open, and hotels' night calls are at
their lowest. Work that may interrupt answering (a database upgrade, a
change of telephony provider, rotating a single webhook secret, a
migration that locks a large table) is done only then.

Deploys that keep the service up (rolling, expand-then-contract,
`docs/operations/deploys.md`) need no window: weekdays before 15:00, never
in a freeze.

## Telling the businesses

| Work | Notice | Channel |
| --- | --- | --- |
| In the window, no expected interruption | none | |
| In the window, answers may pause up to 15 minutes | 3 days ahead | an announcement (Admin → System → Announcements: the cabinet banner and `/status`) |
| A longer interruption, or outside the window | 7 days ahead, again the day before | the announcement, and an e-mail to every owner |
| A new or replaced sub-processor | 30 days ahead (DPA 8.3) | the `send_subprocessor_notices` job, by itself |
| A new DPA or terms version | 30 days to accept (DPA 15.2) | the cabinet |

Planned maintenance announced 24 hours ahead does not count against the
error budgets (`docs/operations/slo.md`). The announcement is resolved
when the work ends; an interruption longer than announced becomes an
incident (`docs/operations/incident.md`).

## The calendar

| When | What | Where |
| --- | --- | --- |
| Every Monday | error budget review, the restore drill's result, on-call handover | `docs/operations/slo.md`, `docs/operations/on-call.md` |
| First Monday of the month | the retention check: the last `succeeded` run of each purge job in `periodic_job_runs`, no Sentry Crons monitor missed | `docs/security/data-classification.md`, "Is the retention job running?" |
| Monthly | the SLO report (every objective of `docs/operations/slo.md`) shared in the ops chat | `docs/operations/slo.md` |
| First week of each quarter | access review | `docs/security/access-review.md` |
| January | tabletop exercise; the audit log's retention check: the daily `purge_expired_audit_log` job (1,095 days, migration 1250) has `succeeded` runs in `periodic_job_runs` and no chain is older than 1,095 days (`workshop purge-audit-log --older-than-days 1095` by hand only if the job was down); the vendor register's yearly review | `docs/operations/tabletop.md`, `docs/operations/vendor-register.md` |
| 12 months after each secret's last rotation | its rotation | `docs/security/secrets-inventory.md` |
| 30 days before `Expires` of security.txt | renew it (a test fails at 30 days) | `web/src/server/securityTxt.ts` |

## Postmortems

Every SEV1 and SEV2, and any incident that spent over 20% of a budget,
gets a written postmortem within 5 working days, with the template of
`docs/operations/incident.md`. It is blameless: it names what made the
mistake possible, not who made it. A tabletop's findings need no
postmortem: they are action items, tracked the same way
(`docs/operations/tabletop.md`).

- Each action item has an owner and a due date, and is a GitHub issue with
  the label `postmortem`; the postmortem links the issues.
- The Monday review goes through the open `postmortem` issues; an item past
  its date is either done, re-dated with a reason, or dropped with a reason
  written in the issue.
- When a postmortem changes a threshold, a runbook or this calendar, the
  pull request links the postmortem.
- Postmortems of breaches are kept with the breach register: the one the
  platform keeps as controller of its own data (accounts, billing,
  security; Art. 33(5)), and the record of each notice it sent a business
  as its processor (Art. 33(2), DPA 12.1), which the business needs for its
  own register.
