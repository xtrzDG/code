# Audit log anomalies

**Alerts** (SEV2, from the audit log's last hour, `ops/alerts/`):

- `bulk_personal_data`: one business exported or erased personal data more
  than 20 times (EXPORT entries and DELETE of a contact).
- `tenant_hopping`: one platform admin entered or changed more than 10
  different clients' accounts (admin access, support access, trial,
  discount, credit, setup fee, invoice, plan overrides).
- `failed_sign_in_checks`: more than 50 wrong sign-in or second-factor
  codes for one destination (a login code's phone or e-mail, named by its
  keyed digest `dest_...`, or a person's second factor, named by the user
  id).

The message names the business, the admin or the destination by its id
only; the audit log has the rest.

## How it shows

- Bulk personal data: a stolen owner session or API key draining the
  customers, an integration exporting in a loop, a script erasing
  contacts.
- Tenant hopping: an admin account used by someone else, or an admin
  browsing clients without a ticket.
- Failed sign-in checks: someone guessing codes for one phone, e-mail or
  account; the code locks after its attempts (`otp_locked`,
  `mfa_locked`), so the count grows only with new codes.

## Check

1. Admin → Audit (`/admin/audit`): the platform's own entries (sign-in
   failures, lockouts, sign-outs, key rotations), filtered by security
   event. A business's entries are on its Settings → Audit tab (support
   access to that business shows them to an admin).
2. Bulk personal data: the business's Audit tab, action "export" and
   "delete": who (actor), from which address, which entity. Compare with
   the owner's usual pattern (the export card on Customers).
3. Tenant hopping: the admin named in the detail; every entry is in each
   client's log with the admin as actor. Ask the admin; check the support
   tickets of the hour.
4. Failed sign-in checks: the destination digest identifies the address
   without revealing it. `GET /v1/admin/audit-log?security_event=login_failed`
   lists the attempts with their addresses (IP); `otp_locked` and
   `mfa_locked` mark each locked code.

## Mitigate

- Bulk personal data from a stolen session or key: ask the owner to
  remove the member (Settings → Team) and revoke the API key (Settings →
  Integrations → API keys). Tell the owner (docs/operations/incident.md,
  owner communication).
- Tenant hopping: revoke the admin's sessions and remove the address from
  `PLATFORM_ADMIN_EMAILS` until it is explained.
- Failed sign-in checks from one network: block it at the edge; turn on the bot check (`TURNSTILE_SITE_KEY`,
  `TURNSTILE_SECRET_KEY`) if it is off. For SMS cost see
  [sms-pumping](sms-pumping.md).

## Afterwards

- A confirmed leak of customers' data is a breach: start
  [data-breach](data-breach.md) (48 hour clock).
- Record who accessed what in the incident notes; the audit entries stay
  in the hash chain and cannot be edited.
