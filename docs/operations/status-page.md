# Status page, announcements and the help center

What owners and their customers see about the platform's own health, and
how the team speaks to every owner during an incident
(`docs/operations/incident.md` is the response itself).

## The public status page

`/status` (cabinet, public, `ka`/`ru`/`en`) reads `GET /v1/platform/status`:

- **Components**: website chat (`chat`), WhatsApp/Instagram/Messenger
  (`meta`), Telegram, phone calls (`voice`) and the cabinet with its
  sign-in (`cabinet`).
- **Level now**: the worst of
  - the platform alerts that fire (`ops/alerts/*.yaml`, checked every five
    minutes by `platform_alerts`), mapped in
    `app/use_cases/platform_status/component_levels.py`: model errors,
    an inbound backlog and a stale worker degrade every chat channel
    (an outage from half the model calls failing or a 15-minute backlog);
    delivery failures degrade the messengers (an outage from half failing);
    tool errors degrade the chat channels and calls; login-code cap trips
    degrade the cabinet. Dead jobs and handoff spikes are internal and not
    shown;
  - the announcements in effect (below).
- **90-day history**: the `record_platform_status` job (every five minutes)
  folds every component's level into the day's row of
  `platform_status_days`; a bar is the worst level of that UTC day, grey
  when nothing was recorded (the job did not run).
- When the API itself does not answer, the page says it cannot reach the
  platform and shows the cabinet as down: the page is served by the
  cabinet, not by the API.

An external uptime monitor (Better Stack, UptimeRobot) is not wired here:
point one at `GET /readyz` and at the cabinet's `/status`, and link its
public page from the status page footer when the account exists.

## Announcements (the banner)

The card **Status page announcements** on the admin page **System**
(`/admin/system`, platform admins with `MANAGE_OPERATIONS`, step-up) writes
`POST /v1/admin/announcements`:

1. Choose the level: a notice (`info`), planned maintenance, degraded
   service or an outage, and the components it affects.
2. Write the text in English (required) and in Georgian and Russian: each
   owner reads it in the cabinet's language, else English.
3. Planned maintenance gets its start (up to 60 days ahead) and expected
   end; it shows as scheduled until it starts.
4. Update it as you learn (`PATCH`), and resolve it when service is back:
   the banner disappears at once and the status page lists it under past
   incidents for 90 days.

Every create and change is an audit entry (`platform_announcement`, no
business, the admin and their address). The banner shows over every page
of a business's cabinet and of the admin pages, polls the status every
minute (past the browser's cache), and a notice, maintenance or a slowdown
can be hidden on a device until the announcement changes; an outage cannot
be hidden.

## Help center and support contacts

- Articles: `docs/help/<language>/<slug>.md` (format in
  `docs/help/README.md`), the same slugs in `en`, `ru` and `ka`
  (`tests/help/test_help_articles.py`). The image copies them (Dockerfile).
- The "?" beside a page's title opens the page's article in a drawer
  (`web/src/lib/help/helpTopics.ts`); `/help` lists and searches them.
- **Help and support** in the account menu links WhatsApp, Telegram and
  e-mail from `SUPPORT_WHATSAPP`, `SUPPORT_TELEGRAM` and `SUPPORT_EMAIL`,
  the help center, "What's new" and this status page.
