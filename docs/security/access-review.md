# Quarterly access review

Who can reach clients' data changes over time: people join and leave,
tokens are created for a quick test and forgotten. Once a quarter (in the
first week of January, April, July and October) one maintainer walks this
list, a second one checks the result, and the review is recorded at the end
of this file. Anything not needed any more is removed the same day.

## Checklist

### Platform admins (the cabinet)

- [ ] The admin team (Admin → Team, `GET /v1/admin/team`) lists only people
      who still need it, each with the smallest role that is enough.
- [ ] `PLATFORM_ADMIN_EMAILS` and `PLATFORM_ADMIN_PHONE_NUMBERS` on Render name the
      same people (the bootstrap list), nobody else.
- [ ] Every platform admin has an authenticator; nobody signs in with a code
      alone.
- [ ] Support access grants of the quarter (each business's audit log,
      `support_access_start`) all had a reason; none is still open.

### Render

- [ ] Team members and their roles in the Render workspace; former team
      members removed.
- [ ] Environment variables holding secrets (`ENCRYPTION_KEY(S)`, provider
      keys, `DATABASE_URL`) are readable only by people who deploy.
- [ ] Deploy hooks and API keys: each one still used, owner known.

### GitHub

- [ ] Organisation and repository members, outside collaborators and teams;
      two-factor authentication required for everyone.
- [ ] Branch protection on the default branch: reviews and the CI checks
      required.
- [ ] Deploy keys, GitHub Apps and personal access tokens with access to the
      repository: each one still needed.
- [ ] Environment secrets (the restore drill's age key, the contract tests'
      provider keys): who can read them.
- [ ] Private vulnerability reporting is switched on (SECURITY.md).

### Provider consoles

For each sub-processor in `app/registries/legal/` (OpenAI, Anthropic,
ElevenLabs, Zadarma, Meta, Telegram, Flitt, Langfuse, Sentry, Google,
Cloudflare, the object storage, the e-mail provider, Twilio):

- [ ] Console users and their roles; former team members removed.
- [ ] API keys: each one in use, scoped as narrowly as the provider allows,
      rotated within the last year (or the provider's maximum).
- [ ] The Telegram platform bot's token and the WhatsApp system user: who can
      read them.

### Keys and backups

- [ ] `ENCRYPTION_KEYS` holds no key older than the last rotation needs
      (docs/operations/backup-restore.md).
- [ ] The age private key of the backups is held by the restore drill and in
      escrow only; the last restore drill passed.
- [ ] `web/public/.well-known/security.txt` has more than a quarter left
      before `Expires` (the test fails 30 days ahead).

### Records

- [ ] The threat model (`docs/security/threat-model.md`) still describes the
      trust boundaries; new integrations of the quarter are in it.

## Reviews

| Quarter | Reviewed by | Checked by | Removed or changed |
| --- | --- | --- | --- |
| 2026 Q4 | [name] | [name] | [first review: to do in the first week of October 2026] |
