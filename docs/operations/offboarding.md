# Offboarding: access removed within 24 hours

When someone leaves the platform team, or no longer needs access, every
account, token and shared secret they could use is removed within 24 hours
of their last day (or at once when they leave on bad terms). The person
who does it fills the record at the end with a time for each step; a
second maintainer checks it. Joining is the reverse: least privilege, the
smallest admin role that is enough (`docs/security/permission-matrix.md`),
and the security and AI-literacy briefing before the first access.

## Checklist

Start at the top: the first steps cut access to customers' data.

### Within the first hour

- [ ] **Platform admin team**: remove them from Admin → Team
      (`DELETE /v1/admin/team/{admin_id}`); the role is read at every
      request, so their admin access ends at the next one. If they are in
      `PLATFORM_ADMIN_EMAILS` or `PLATFORM_ADMIN_PHONE_NUMBERS` on Render
      (the bootstrap list, which grants the role by itself), remove them
      there too and redeploy.
- [ ] **Open looks into clients' cabinets**: a support grant opens
      nothing once the role is gone, and ends within the hour anyway; note
      in the record which businesses they looked into in their last week
      (the businesses' `support_access_start` audit entries).
- [ ] **Render**: remove them from the workspace; rotate any API key or
      deploy hook they created.
- [ ] **GitHub**: remove them from the organisation and the repository;
      revoke their personal access tokens' access, deploy keys and GitHub
      App installations they own; if they had admin, check the branch
      protection is unchanged (`repo-settings.yml` the next morning).

### Within 24 hours

- [ ] **Provider consoles**: remove their user from each console in
      `docs/operations/vendor-register.md` (OpenAI, Anthropic, ElevenLabs,
      Zadarma, Twilio, Meta Business Manager, Telegram (BotFather access of
      the platform bot), Stripe, Flitt, Google Cloud, Cloudflare, Sentry,
      Langfuse, the object storage, the e-mail provider, the registrar and DNS
      host).
- [ ] **Shared secrets they could read**: rotate every secret of
      `docs/security/secrets-inventory.md` whose store they could open (all
      of them for someone with Render access), except the rows marked "on
      exposure" (`SUPPRESSION_LIST_KEY`, the push keys, the Sentry DSN):
      those only when the departure is on bad terms or a copy is suspected,
      as an incident. Log each rotation in the inventory's rotation log.
- [ ] **The ops chat and paging**: remove them from the Telegram group of
      `PLATFORM_ALERT_TELEGRAM_CHAT_IDS`, the addresses of
      `PLATFORM_ALERT_EMAILS`, the paging rota and the uptime monitor.
- [ ] **Password manager vault**: remove them; if they held the escrow
      copies, re-seal the escrow with the new holder
      (`docs/operations/backup-restore.md`, "Keys and custody").
- [ ] **Mailboxes**: remove them from the security and support mailboxes.
- [ ] **Devices**: company laptops and phones returned and wiped, or their
      access to the above confirmed removed when the device is personal.
- [ ] **Ownership**: issues, alerts and documents they owned get a new owner;
      `.github/CODEOWNERS` names someone else where it named them.

### Afterwards

- [ ] The next quarterly access review (`docs/security/access-review.md`)
      finds no trace of them.

## Record

Keep one row per departure; the times are UTC.

| Person | Last day | Admin team removed | Render | GitHub | Consoles | Secrets rotated | Chat, paging, vault | Done by | Checked by |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [none yet] | | | | | | | | | |
