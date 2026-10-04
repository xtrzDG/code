# Personal data breach

**Always SEV1.** A breach is any accidental or unlawful destruction, loss,
alteration, disclosure of or access to personal data the platform
processes for a business: a misdirected export, a leaked key or backup, a
bug that showed one business's data to another, a compromised admin
account. The DPA (`docs/legal/`, section 12) gives the platform at most
**48 hours from becoming aware** to notify each affected business (the
controller), which then has **72 hours** under the GDPR to notify its
supervisory authority. Write down the moment of awareness: the clocks
start there.

## First hour

1. **Declare** SEV1 in the ops chat; name the lead; tell the founder.
2. **Contain**, without destroying evidence:
   - a leaked secret: rotate it now (`ENCRYPTION_KEY` per
     `../backup-restore.md`, "Key rotation"; provider keys in their
     consoles; the backup bucket's key);
   - a compromised account: remove it from `PLATFORM_ADMIN_EMAILS` /
     `PLATFORM_ADMIN_PHONE_NUMBERS` (read per request: effective at once),
     revoke its sessions;
   - a bug exposing data: roll back ([bad-deploy](bad-deploy.md)) or
     disable the feature;
   - a misdirected file: ask the recipient in writing to delete it and
     confirm.
3. **Preserve**: export the relevant logs, Sentry events and audit entries
   before retention removes them; note who did what, in UTC.

## Within 24 hours: scope

- Which businesses? Only those whose data was concerned (the audit logs
  per business, the access logs).
- Which people and records, roughly how many? Categories (customers,
  staff; names, phone numbers, messages, recordings), approximate counts.
- Likely consequences for those people, and measures taken or proposed.

## Notify the businesses (before 48 hours)

Record the incident on Admin → System → Incidents with `kind`
"data breach" (or `POST /v1/admin/incidents`; it needs a recent sign-in):
the affected businesses, the approximate numbers, and the five texts in
English plus Georgian and Russian (examples in `../incident.md`). Every
owner of each affected business gets the notice by e-mail or SMS through
the outbox, in their language, and each business's audit log records it.
Check on `/admin/system` that the `deliver_outbound` jobs went out; call
owners whose notice failed.

## Help the controllers (DPA 12.2)

- Owners may ask for details for their authority's form (GDPR article 33:
  the nature, categories and numbers, the contact point, consequences,
  measures). Answer within a working day.
- If the people concerned must be told (high risk), help the owner word it;
  the platform does not contact a business's customers on its own.

## Afterwards

- Postmortem within 5 working days; the action items are reviewed by the
  founder. Keep the record (timeline, notices, decisions) for at least 5
  years: the DPA and the GDPR require documenting every breach, notified
  or not.
