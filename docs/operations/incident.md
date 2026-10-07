# Incidents: severity, roles, communication and postmortems

What counts as an incident, who does what while it lasts, what owners are
told and when, how a personal data breach is reported (DPA section 12),
and how the team learns from it. The objectives and alerts are in
`docs/operations/slo.md`; each failure has its runbook in
`docs/operations/runbooks/`.

## Severity

| Severity | What it means | Examples | Respond | Owners told |
| --- | --- | --- | --- | --- |
| **SEV1** | Customers of many businesses get no answers, data is exposed, or money moves wrongly | the model provider is down (`llm_errors`), no worker runs, the database is lost, a personal data breach, double charges | at once, day or night; all hands | within 1 hour, then every 2 hours until resolved |
| **SEV2** | A channel, a feature or some businesses are broken, or answers are slow | Meta or Telegram outage, dead jobs piling up, the inbound backlog over 2 minutes, a stuck worker, SMS pumping, a bad deploy | within 30 minutes during the day (08:00-23:00 Tbilisi), first thing otherwise | when it lasts over 30 minutes or an owner noticed |
| **SEV3** | Degraded, with a workaround, or one business | tool errors of one calendar, a slow admin page, one channel's token expiring | next working day | the affected owner, if they need to act |

When unsure, pick the higher severity; lowering it later costs nothing.
A breach is always SEV1, even when it looks small.

## Roles

One person can hold several roles in a small team; the roles still exist.

- **Incident lead**: decides, assigns, keeps the timeline. Says "I am the
  lead" in the ops chat. Hands over explicitly.
- **Fixer**: works the runbook; tells the lead before any risky step
  (rollback, restore, key rotation).
- **Communicator**: owner notices (templates below), the status page once
  it exists (R13), the founder for SEV1.

## Timeline of an incident

1. **Detect**: a platform alert in the ops chat, Sentry, the uptime
   monitor, or an owner. Open `/admin/system` first: alerts, lanes, dead
   letters, workers, channels.
2. **Declare**: post in the ops chat `INCIDENT <SEV> <one line>`, name the
   lead, start the timeline (UTC times).
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

## Personal data breach (DPA section 12)

The platform is the processor; each business is the controller of its
customers' data. Under DPA 12.1 the platform tells the controller "without
undue delay and in any case within 48 hours" of becoming aware; the
controller has 72 hours under the GDPR to tell the supervisory authority
(12.2), and the platform helps. Follow
[runbooks/data-breach.md](runbooks/data-breach.md); the notice itself goes
out through `POST /v1/admin/incidents` with `kind: data_breach`:

- `title`, `severity` (SEV1), `started_at`, `detected_at` (the moment the
  platform became aware: the 48-hour clock starts here);
- `affected_business_ids`: only businesses whose data was concerned (at
  most 1,000), or `scope: all_businesses` with none named when every
  business's data was (the `expand_incident` job then reaches each one a
  keyset batch at a time: the batch's notices, audit entries and progress
  commit together, so a worker that dies mid-walk resumes without telling
  anyone twice);
- `approximate_subject_count`, `approximate_record_count`;
- `notice_texts`: for each language (English is required; add Georgian and
  Russian), the five DPA 12.1 texts: what happened (`nature`), the
  categories of people (`subject_categories`) and of records
  (`record_categories`), the likely consequences, and the measures taken
  or proposed (`measures`).

Every owner (not staff) of each affected business gets the notice in the
cabinet language, by e-mail to the sign-in address or else by SMS, through
the outbox (retried; idempotent per incident), and an audit entry in the
business's log names the incident and the admin. The request needs a
recent sign-in (step-up). Record later facts as a new incident note in the
postmortem; a second notice goes out only for new facts.

## Communication templates

Fill the parts in angle brackets; keep times in the business's time zone
for owners and UTC in the ops chat. Never name other businesses, customers
or internal hosts.

### Outage or degradation: started

**English**

> Subject: Assistant Workshop: <channel or feature> disrupted
>
> Since <time>, <what owners see: replies in WhatsApp are delayed / calls
> are not answered>. Your customers' messages are kept and will be
> answered once it is fixed; nothing is lost. We are working on it and
> will update you by <time>. If a customer needs you urgently, the
> conversation is in your inbox: <link>.

**Русский**

> Тема: «Мастерская ассистентов»: перебои — <канал или функция>
>
> С <время> <что видит владелец: ответы в WhatsApp задерживаются / звонки
> не принимаются>. Сообщения ваших клиентов сохраняются, и помощник ответит
> на них, как только мы всё исправим, — ничего не потеряно. Мы уже
> работаем над этим и напишем вам до <время>. Если клиенту нужен ответ
> срочно, разговор есть во «Входящих»: <ссылка>.

**ქართული**

> თემა: „ასისტენტების სახელოსნო“: შეფერხება — <არხი ან ფუნქცია>
>
> <დრო>-დან <რას ხედავს მფლობელი: WhatsApp-ში პასუხები იგვიანებს / ზარებს
> არავინ პასუხობს>. თქვენი კლიენტების შეტყობინებები შენახულია და
> ასისტენტი უპასუხებს მათ, როგორც კი პრობლემას გამოვასწორებთ — არაფერი
> დაიკარგება. უკვე ვმუშაობთ ამაზე და <დრო>-მდე მოგწერთ. თუ კლიენტს პასუხი
> სასწრაფოდ სჭირდება, საუბარი „შემოსულებშია“: <ბმული>.

### Outage or degradation: resolved

**English**

> Subject: Resolved: <channel or feature>
>
> <Channel or feature> works again since <time>. The assistant has
> answered the messages that waited. Cause: <one sentence, no blame>. What
> we change so it does not happen again: <one sentence>. We are sorry for
> the trouble.

**Русский**

> Тема: Исправлено: <канал или функция>
>
> С <время> <канал или функция> снова работает. Помощник ответил на
> сообщения, которые ждали. Причина: <одно предложение, без поиска
> виноватых>. Что мы меняем, чтобы это не повторилось: <одно предложение>.
> Приносим извинения за неудобства.

**ქართული**

> თემა: გამოსწორდა: <არხი ან ფუნქცია>
>
> <დრო>-დან <არხი ან ფუნქცია> ისევ მუშაობს. ასისტენტმა უპასუხა
> შეტყობინებებს, რომლებიც ელოდებოდა. მიზეზი: <ერთი წინადადება, ბრალის
> დადების გარეშე>. რას ვცვლით, რომ აღარ განმეორდეს: <ერთი წინადადება>.
> ბოდიშს გიხდით შეფერხებისთვის.

### Personal data breach

Sent by the platform (`POST /v1/admin/incidents`): the frame is fixed in
each language (`app/use_cases/admin/incidents/incident_notices.py`), the
team writes the five texts. Draft them in plain words:

| Field | English example | Русский пример | ქართული მაგალითი |
| --- | --- | --- | --- |
| `nature` | A support export with customer names and phone numbers was sent to a wrong e-mail address. | Выгрузка поддержки с именами и телефонами клиентов ушла на неверный адрес почты. | მხარდაჭერის ექსპორტი კლიენტების სახელებითა და ტელეფონებით შეცდომით გაიგზავნა არასწორ მისამართზე. |
| `subject_categories` | Customers who wrote to your business by WhatsApp in September | Клиенты, писавшие вашему бизнесу в WhatsApp в сентябре | კლიენტები, რომლებმაც სექტემბერში თქვენს ბიზნესს WhatsApp-ით მისწერეს |
| `record_categories` | Names and phone numbers; no messages, payments or passwords | Имена и телефоны; без сообщений, платежей и паролей | სახელები და ტელეფონის ნომრები; შეტყობინებების, გადახდებისა და პაროლების გარეშე |
| `likely_consequences` | Unwanted calls or messages are possible; misuse beyond that is unlikely. | Возможны нежелательные звонки или сообщения; иное злоупотребление маловероятно. | შესაძლებელია არასასურველი ზარები ან შეტყობინებები; სხვა სახის ბოროტად გამოყენება ნაკლებად სავარაუდოა. |
| `measures` | The recipient confirmed deletion; exports now need a second person's approval. | Получатель подтвердил удаление; выгрузки теперь подтверждает второй сотрудник. | მიმღებმა წაშლა დაადასტურა; ექსპორტს ახლა მეორე თანამშრომელი ადასტურებს. |

## Postmortem template

Blameless: describe what the system and the process allowed, never who
"should have". Store it in the team's drive as
`postmortems/<yyyy-mm-dd>-<slug>.md` and link it from the incident's
ticket.

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
