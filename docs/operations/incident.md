# Incidents: severity, roles, communication and postmortems

What counts as an incident, who does what while it lasts, what owners are
told and when, how a personal data breach is reported (GDPR articles 33
and 34, DPA section 12), and how the team learns from it. The objectives and alerts are in
`docs/operations/slo.md`; each failure has its runbook in
`docs/operations/runbooks/`.

## Severity

| Severity | What it means | Examples | Respond | Owners told |
| --- | --- | --- | --- | --- |
| **SEV1** | Customers of many businesses get no answers, data is exposed, or money moves wrongly | the model provider is down (`llm_errors`), no worker runs, the database is lost, a personal data breach, double charges | at once, day or night; all hands | within 1 hour, then every 2 hours until resolved |
| **SEV2** | A channel, a feature or some businesses are broken, or answers are slow | Meta or Telegram outage, dead jobs piling up, the inbound backlog over 2 minutes, a stuck worker, SMS pumping, a bad deploy | within 30 minutes, 08:00-23:00 Europe/Rome every day (`docs/operations/on-call.md`), first thing otherwise | when it lasts over 30 minutes or an owner noticed |
| **SEV3** | Degraded, with a workaround, or one business | tool errors of one calendar, a slow admin page, one channel's token expiring | next working day | the affected owner, if they need to act |

When unsure, pick the higher severity; lowering it later costs nothing.
A breach is always SEV1, even when it looks small. Picking a severity in
the first minute: the decision tree of `docs/operations/on-call.md`
("Picking a severity").

## Roles

One person can hold several roles in a small team; the roles still exist.

- **Incident lead** (the incident commander): decides, assigns, sets the
  next check-in. Says "I am the lead" in the ops chat. Hands over
  explicitly.
- **Scribe**: keeps the timeline in the incident's thread as it happens
  (UTC time, who, what was seen, what was decided and why, every command
  run against production), collects links to logs, Sentry events and
  audit entries for the evidence, and starts the postmortem draft from it.
  The lead is the scribe only while nobody else is there; the second
  person to join takes it over.
- **Fixer**: works the runbook; tells the lead before any risky step
  (rollback, restore, key rotation).
- **Communicator**: owner notices (templates below), the status page
  (`docs/operations/status-page.md`), the founder for SEV1.
- **Privacy lead** (a breach only; the founder unless
  `docs/operations/contacts.md` names another person): judges the risk to
  people, files the notification to the Garante, decides whether people
  are told, keeps the breach register.

## Timeline of an incident

1. **Detect**: a platform alert in the ops chat, Sentry, the uptime
   monitor, or an owner. Open `/admin/system` first: alerts, lanes, dead
   letters, workers, channels.
2. **Declare**: post in the ops chat `INCIDENT <SEV> <one line>`, name the
   lead and the scribe, start the timeline (UTC times).
3. **Record**: Admin → System → Incidents → "Record incident" (or `POST
   /v1/admin/incidents`) with the businesses affected, or "All businesses"
   (`scope: all_businesses`) when the whole platform was hit. Each of them
   gets an audit entry; a data breach also sends the DPA 12.1 notice to
   every owner of those businesses (below). For all businesses the worker
   walks them in batches of 200 after the incident is stored (the log
   shows "reaching businesses…" with the count so far). Tick "Publish a
   status announcement" in the same dialog to put the banner and the
   `/status` notice up at once (`announcement`; it is linked to the
   incident; resolve it from the announcements card).
4. **Mitigate** before you fix: roll back, pause a channel, switch the model
   provider, discard a poison job. Customers getting answers again comes
   first.
5. **Communicate** on the schedule of the severity table.
6. **Resolve** when the alert resolved and the SLO is no longer being
   spent; post `RESOLVED` with the duration.
7. **Postmortem** within 5 working days for SEV1 and SEV2 (template below).

## Personal data breach (GDPR articles 33 and 34)

A breach is any accidental or unlawful destruction, loss, alteration,
disclosure of or access to personal data: a misdirected export, a leaked
key or backup, a bug that showed one business's data to another, a
compromised admin account. It is always SEV1. Write down the moment the
platform became **aware** of it (reasonably certain that personal data
was affected): every clock below starts there, and it is the incident's
`detected_at`.

### Whose data: processor or controller

| Data concerned | Platform's role | Who tells the Garante (72 h) | Who tells the people (art. 34) |
| --- | --- | --- | --- |
| A business's customers: conversations, transcripts, call recordings, voice notes and photos, contacts and their marketing consent, bookings and requests | **processor** (the DPA, `docs/legal/dpa-*.md`); the business is the controller | the business, within 72 hours of *its* awareness (art. 33(1)); the platform tells it first and helps (DPA 12.2) | the business decides and writes; the platform helps word it and never contacts a business's customers on its own |
| The platform's own: owners' and staff accounts (sign-in phone or e-mail, sign-in codes, sessions, passkeys), billing profiles and invoices, the public site's visitors, support | **controller** | the platform, within 72 hours of awareness, unless the breach is unlikely to result in a risk to people (art. 33(1)) | the platform, without undue delay, when the risk is high (art. 34) |

Both at once is common (a leaked database copy): run both rows.

### Steps and who does what

| By (from awareness) | Step | Who |
| --- | --- | --- |
| at once | Declare SEV1 in the ops chat, name the lead, tell the founder; record the awareness time in UTC | whoever detects; the **incident lead** |
| 1 hour | Contain without destroying evidence and preserve logs, Sentry events and audit entries ([runbooks/data-breach.md](runbooks/data-breach.md)) | the **fixer**, told by the lead |
| 24 hours | Scope: which role (table above), which businesses, categories and rough numbers of people and records, likely consequences; assess the risk: none, a risk, or a high risk (criteria below) | the lead with the **privacy lead** (the founder unless another person is named in `docs/operations/contacts.md`) |
| 48 hours | Processor data: notify every owner of each affected business (DPA 12.1, "without undue delay and in any case within 48 hours") through `POST /v1/admin/incidents` with `kind: data_breach` (below) | the **communicator** |
| 72 hours | Controller data with a risk: notify the Garante per la protezione dei dati personali through its online breach notification procedure (garanteprivacy.it, "Notifica di una violazione dei dati personali"). Facts still missing go in later phases (art. 33(4)); a late notice says why it is late | the **privacy lead** |
| without undue delay | High risk: tell the people concerned in plain language (art. 34(2): what happened, a contact point, the likely consequences, the measures, what they can do themselves); for processor data, give the owners the facts and the template below | controller data: the communicator; processor data: the owner, helped by the communicator |
| 24 hours | A payment provider's key, webhook secret or account is (or may be) compromised, or card data may have been exposed: tell the PSP through its security contact (Stripe: the Dashboard's support and security@stripe.com; Flitt: its support desk and the contact of the merchant agreement), rotate the key and webhook secret ([runbooks/secret-rotation.md](runbooks/secret-rotation.md)), and check `docs/security/payments.md`. The contracts' own deadlines win where shorter: record each PSP's in `docs/operations/contacts.md` (owner action) | the **incident lead**, with the communicator |
| always | Enter the breach in the breach register (art. 33(5)) with the facts, the effects, the decision on each notice and why, and the remedial action, also when nothing was notified; keep it at least 5 years | the privacy lead |
| 5 working days | Postmortem (template below) | the lead |

**Risk** (EDPB Guidelines 9/2022 on breach notification): weigh the kind
of data, how many people, how easily they are identified, how severe and
how lasting the consequences are, and whether they belong to vulnerable
groups. Usually **high**: call recordings or transcripts that reveal
health (a clinic's), names with phone numbers of many customers made
public, sign-in sessions or codes that let someone act as an owner.
Usually **no risk**: an archive or a field that stayed unintelligible
(the age-encrypted backups, `docs/operations/backup-restore.md`, with the
keys safe; the channel secrets sealed with `ENCRYPTION_KEY`), a file sent
to a known recipient who confirmed in writing that they deleted it unread.

**Telling the people** is not needed when (art. 34(3)): the data was
unintelligible to anyone not authorized (encryption with uncompromised
keys); the measures taken since make the high risk no longer likely; or
it would take disproportionate effort, in which case a public notice (the
status announcement and `/status`, `docs/operations/status-page.md`)
replaces it. The Garante may still require it (art. 34(4)).

### The notice to the businesses (DPA 12.1)

The notice goes out through `POST /v1/admin/incidents` (Admin → System →
Incidents, "Record incident"; it needs a recent sign-in) with `kind:
data_breach`:

- `title`, `severity` (SEV1), `started_at`, `detected_at` (the moment of
  awareness);
- `affected_business_ids`: only businesses whose data was concerned (at
  most 1,000), or `scope: all_businesses` with none named when every
  business's data was (the `expand_incident` job then reaches each one a
  keyset batch at a time: the batch's notices, audit entries and progress
  commit together, so a worker that dies mid-walk resumes without telling
  anyone twice);
- `approximate_subject_count`, `approximate_record_count`;
- `notice_texts`: for each language (English is required; add Italian, the
  other cabinet language), the five DPA 12.1 texts: what happened
  (`nature`), the categories of people (`subject_categories`) and of
  records (`record_categories`), the likely consequences, and the measures
  taken or proposed (`measures`).

Every owner (not staff) of each affected business gets the notice in the
cabinet language (Italian or English; the frame is
`app/use_cases/admin/incidents/incident_notices.py`), by e-mail to the
sign-in address or else by SMS, through the outbox (retried; idempotent
per incident), and an audit entry in the business's log names the
incident and the admin. Check on `/admin/system` that the
`deliver_outbound` jobs went out and call owners whose notice failed.
Owners may then ask for the details of their own art. 33 form (the
nature, categories and numbers, a contact point, the consequences, the
measures): answer within a working day. Record later facts as a new
incident note in the postmortem; a second notice goes out only for new
facts.

## Communication templates

Fill the parts in angle brackets; keep times in the business's time zone
for owners and UTC in the ops chat. Never name other businesses, customers
or internal hosts. Owners read the cabinet's languages, English and
Italian.

### Outage or degradation: started

**English**

> Subject: Assistant Workshop: <channel or feature> disrupted
>
> Since <time>, <what owners see: replies in WhatsApp are delayed / calls
> are not answered>. Your customers' messages are kept and will be
> answered once it is fixed; nothing is lost. We are working on it and
> will update you by <time>. If a customer needs you urgently, the
> conversation is in your inbox: <link>.

**Italiano**

> Oggetto: Assistant Workshop: disservizio su <canale o funzione>
>
> Dalle <ora> <cosa vede il titolare: le risposte su WhatsApp arrivano in
> ritardo / le chiamate non ricevono risposta>. I messaggi dei tuoi
> clienti sono conservati e riceveranno risposta appena il problema sarà
> risolto: non si perde nulla. Ci stiamo lavorando e ti aggiorneremo entro
> le <ora>. Se un cliente ha bisogno di te con urgenza, la conversazione è
> nella tua casella: <link>.

### Outage or degradation: resolved

**English**

> Subject: Resolved: <channel or feature>
>
> <Channel or feature> works again since <time>. The assistant has
> answered the messages that waited. Cause: <one sentence, no blame>. What
> we change so it does not happen again: <one sentence>. We are sorry for
> the trouble.

**Italiano**

> Oggetto: Risolto: <canale o funzione>
>
> Dalle <ora> <canale o funzione> funziona di nuovo. L'assistente ha
> risposto ai messaggi in attesa. Causa: <una frase, senza colpe>. Cosa
> cambiamo perché non si ripeta: <una frase>. Ci scusiamo per il disagio.

### Personal data breach: the five texts of the notice

Sent by the platform (`POST /v1/admin/incidents`): the frame is fixed in
each language, the team writes the five texts. Draft them in plain words:

| Field | English example | Esempio in italiano |
| --- | --- | --- |
| `nature` | A support export with customer names and phone numbers was sent to a wrong e-mail address. | Un'esportazione dell'assistenza con nomi e numeri di telefono dei clienti è stata inviata a un indirizzo e-mail sbagliato. |
| `subject_categories` | Customers who wrote to your business by WhatsApp in September | I clienti che hanno scritto alla tua attività su WhatsApp a settembre |
| `record_categories` | Names and phone numbers; no messages, recordings, payments or passwords | Nomi e numeri di telefono; nessun messaggio, registrazione, pagamento o password |
| `likely_consequences` | Unwanted calls or messages are possible; misuse beyond that is unlikely. | Sono possibili chiamate o messaggi indesiderati; altri abusi sono improbabili. |
| `measures` | The recipient confirmed deletion; exports now need a second person's approval. | Il destinatario ha confermato la cancellazione; ora le esportazioni richiedono l'approvazione di una seconda persona. |

### Personal data breach: what an owner may tell its customers (art. 34)

For the owner to send in its own name when its customers must be told
(the platform never writes to a business's customers about a breach).

**English**

> Subject: <Business>: about your personal data
>
> On <date> we learned that <what happened, in one sentence>. It concerns
> <which data: your name and phone number / the recording of your call of
> <date>>. What this may mean for you: <likely consequences>. What we did:
> <measures>. What you can do: <e.g. be careful with calls or messages
> that ask for payment details>. For questions write to <contact>.

**Italiano**

> Oggetto: <Attività>: informazioni sui tuoi dati personali
>
> Il <data> abbiamo saputo che <cosa è successo, in una frase>. Riguarda
> <quali dati: il tuo nome e numero di telefono / la registrazione della
> tua chiamata del <data>>. Cosa può significare per te: <conseguenze
> probabili>. Cosa abbiamo fatto: <misure adottate>. Cosa puoi fare tu:
> <ad es. diffidare di chiamate o messaggi che chiedono dati di
> pagamento>. Per domande scrivi a <contatto>.

## Postmortem template

Blameless: describe what the system and the process allowed, never who
"should have". Store it in the team's drive as
`postmortems/<yyyy-mm-dd>-<slug>.md` and link it from the incident's
ticket. Its action items are tracked as `docs/operations/maintenance.md`
("Postmortems") says.

```markdown
# <Title> (<SEV>, <date>)

Incident id: <incident_...>   Lead: <name>   Status: draft | final

## Summary
Two or three sentences: what broke, for whom, how long, how it ended.

## Impact
- Businesses affected: <count>; customers' messages delayed or lost: <count>
- SLO budget spent: answered in time <x>%, latency <x>%, availability <x>%
- Data: none | <what, how many people and records> (DPA notice sent <time>)

## Timeline (UTC)
| Time | Event |
| --- | --- |
| hh:mm | first symptom (alert / owner / monitor) |
| hh:mm | declared, lead named |
| hh:mm | mitigated |
| hh:mm | resolved |

## Root cause
What happened in the system, as a chain of causes (5 whys), not a name.

## What went well / what went badly / where we were lucky

## Action items
| Action | Kind (prevent / detect / mitigate) | Owner | Due | Issue |
| --- | --- | --- | --- | --- |

## Alerts and runbooks
Did an alert fire in time? Does a threshold in ops/alerts/ change? Which
runbook step was missing or wrong (fix it in the same week)?
```
