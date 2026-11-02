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
      two-factor authentication required for everyone. Repository admins
      can edit the `release` ruleset and the environments; nobody else can
      push to `release`.
- [ ] The required reviewers of the environment `production-release`
      (`.github/repository-settings.json`): each one still approves
      promotions, and the team reviewers' members are who they should be
      (the daily check reads the reviewer list, not a team's members).
- [ ] The deploy key used for the promotion (Settings → Deploy keys; its
      private half is `production-release`'s `RELEASE_DEPLOY_KEY`): exactly
      one key with write access, and the `release` ruleset's only bypass is
      "Deploy keys" (the daily check cannot read bypass actors).
- [ ] Branch protection on the default branch: pull requests only, the CI
      checks required, no force push or deletion; the daily
      `.github/workflows/repo-settings.yml` is green and its token
      (`REPO_SETTINGS_TOKEN`, SECURITY.md "Repository settings", with
      Administration and Actions read-only) has more than a quarter left.
- [ ] Deploy keys, GitHub Apps and personal access tokens with access to the
      repository: each one still needed.
- [ ] Environment secrets (the restore drill's age key, the contract tests'
      provider keys): who can read them.
- [ ] Private vulnerability reporting is switched on (SECURITY.md; the same
      daily check reads it).

### Provider consoles

For each vendor of `docs/operations/vendor-register.md` (OpenAI,
Anthropic, ElevenLabs, Zadarma, Meta, Telegram, Flitt, Stripe, Langfuse,
Sentry, Google, Cloudflare, the object storage, the e-mail provider,
Twilio, the registrar and DNS host):

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
- [ ] The security.txt fields (`web/src/server/securityTxt.ts`) have more
      than a quarter left before `Expires` (the test fails 30 days ahead),
      and production's `/.well-known/security.txt` names the security
      mailbox that someone reads.

### Records

- [ ] The threat model (`docs/security/threat-model.md`) still describes the
      trust boundaries; new integrations of the quarter are in it.
- [ ] The rotation log of `docs/security/secrets-inventory.md` has no secret
      older than its period; every departure of the quarter has a complete
      row in `docs/operations/offboarding.md`.
- [ ] Every owner's monitor of `docs/operations/on-call.md` (certificates,
      domain, PSPs, provider budgets, uptime) exists and pages the rota.

## Reviews

| Quarter | Reviewed by | Checked by | Removed or changed |
| --- | --- | --- | --- |
| 2026 Q4 | [name] | [name] | [first review: to do in the first week of October 2026] |
