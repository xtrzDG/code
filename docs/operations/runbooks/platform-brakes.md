# Platform brakes: the global pause and the daily budget stop

**Alerts:** `spend_budget_stop` (SEV1): the providers' spend of the
current UTC day reached `PLATFORM_DAILY_SPEND_STOP_PERCENT` (100 by
default) of `PLATFORM_DAILY_SPEND_BUDGET_USD`. The warning comes earlier
from `spend_budget` (80%, [spend-spike](spend-spike.md)). A global pause
raises no alert: a SUPER admin set it, and the audit log says who and why.

**Where:** Admin → System, the "Platform brakes" card: whether every
assistant is paused (by whom, when, why), today's share of the budget and
the share it stops at. API: `GET /v1/admin/platform/pause`,
`PUT /v1/admin/platform/pause` (`{"is_paused": true, "reason": "..."}`).

## What a brake does

Both brakes act through the spend guard, which every model turn, every
round of a tool loop and every call start consults:

- chat channels, the widget and messengers: the assistant does not call
  the model; the customer reads, in their language, that a colleague
  takes over, and the team gets a handoff in the inbox;
- calls: the voice platform's call start is refused, so the carrier's
  fallback puts the caller through to the business's staff phone (the
  handoff phone, else the first manager with a phone); with none, the call
  is a missed call with its text-back;
- background model work holds too: quality sampling and topic grouping
  skip their run, conversation summaries wait an hour, knowledge indexing
  retries, a finished call's summary is skipped (staff get the call report
  without it, and no caller memory is written), and an autotest run queued
  before the brake is skipped when the worker starts it (it reads as
  ERRORED and the version goes back to its previous status; an "Apply
  changes" whose checks were skipped stays at the checking stage, and the
  owner applies again once the brake lifts);
- owners' costly actions (menu import, starting a website import,
  starting autotests, alias suggestions, renting a number) get 409
  `platform_brake` with the detail `paused` or `budget_stop`, which the
  cabinet words in English and Italian; a number rental is refused before
  the carrier is asked, and one the carrier already sold when a brake
  starts is recorded and counted as usual; the test chat is not refused
  (its turns go to the team like customers'), and searching numbers and
  asking the team for one still work;
- nothing of a business changes: resuming (or UTC midnight, for the
  budget stop) restores every assistant at once.

The budget stop reads the platform's spend once a minute per process, so
it may let up to a minute of spend through after the stop.

## Pause every assistant (SUPER admins only)

Use it when the assistants must stop answering everywhere now: a model
answering wrongly or in the wrong language, a prompt injection wave, a
provider incident that makes answers unsafe, a legal hold.

1. Admin → System → Platform brakes → "Pause every assistant", with the
   reason (8 to 300 characters; it goes to the audit log). The action
   asks for a recent sign-in (step-up).
2. Record an incident on the same page and, if owners must know, an
   announcement on the status page.
3. Resume with a reason once the cause is fixed. The audit log
   (Admin → Audit, platform log) keeps both entries (`platform_pause`,
   `paused` / `resumed`).

## The budget stop fired

1. Admin → System → the spend tile: which provider, which businesses (the
   braked list). A single business far above the others is abuse or a
   loop: give it a hard limit of 0 (`PUT
   /v1/admin/clients/{business_id}/spend-limits`) instead.
2. When the spend is legitimate (growth), raise
   `PLATFORM_DAILY_SPEND_BUDGET_USD` (or the stop percent) in the
   environment and redeploy; the assistants answer again within a minute
   of the new release.
3. Otherwise the stop lifts by itself at UTC midnight. Tell owners through
   an incident announcement while it holds.
