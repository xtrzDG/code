# Privacy requests about the platform's own data

Not an outage: the procedure for a person who asks the platform, as
**controller**, about their own data (GDPR art. 12, 15-21): business owners
and staff (their accounts), people who wrote to the platform's own support,
and visitors of the public site. A business's **customers** ask the
business, which is the controller of their data; the platform only assists
it (DPA 11.3, `docs/help/en/privacy.md`).

## How it shows

- A message to the privacy mailbox ([e-mail for privacy requests], the
  address of the privacy policy) or to the support mailbox
  (`GET /v1/support/contacts`), or a letter.
- A business's customer who writes to the platform: forward the request to
  the business's owners the same working day (support mailbox, DPA 11.3),
  tell the person who answers it, and log only that it was forwarded.

## Check

1. **Log it** the day it arrives in the privacy request register
   ([where the register is kept: a restricted sheet or ticket queue]): date
   received, the channel, what is asked (access, copy, correction,
   erasure, objection, restriction), **due date = received + 1 month**.
   Nothing else about the person goes into the register.
2. **Verify the identity** before any data leaves or changes, with the
   least data that proves it:
   - an account holder signs in to the cabinet (a one-time code to the
     account's own phone or e-mail is the proof) and makes the request from
     there, or answers a code sent to the account's address on file;
   - anyone else proves control of the address the data is about (a reply
     from that address, a code sent to that number).
   Never ask for an identity document unless those fail and the request is
   for sensitive data; never act on a request from an address that is not
   the account's.
3. Someone asking for another person (a lawyer, a parent of a child under
   14): ask for the authorisation and verify the person it concerns as
   above.

## Act

| Request | How |
| --- | --- |
| Access, copy | `GET /v1/me` (the account, its businesses and roles), `GET /v1/me/sessions`, `GET /v1/me/security`; an owner's businesses: the full export (Settings → Privacy). Send it to the verified address, encrypted or through the cabinet. |
| Correction | the person edits it in the cabinet (`PATCH /v1/me`); the operator corrects what they cannot reach. |
| Erasure | `DELETE /v1/me` after the step-up (the account goes; a sole owner closes their businesses first, which starts the 30 days and ends with a deletion certificate). Invoices and the audit log stay as the law requires; say so in the answer. |
| Objection to product e-mails | turn them off in the account's notification settings; no marketing is sent without consent. |

## When a business answers its customer

The business (the controller) answers its customers from the cabinet;
support explains these two points when an owner asks:

- **Copy** (the customer's export, `GET /v1/businesses/{business_id}/contacts/{contact_id}/export`):
  besides the conversations, bookings and consent records it lists the
  business's knowledge items that name the customer
  (`records.knowledge_mentions`): by their whole name (without case,
  accents and punctuation, also surname first) or by one of their numbers
  (a run of at least eight of its digits, however punctuated), also
  inside a list of numbers. Each comes with its title,
  text, attribute values and aliases, so the mention itself is in the
  copy. Those texts may name other people: the owner removes third
  parties' data before sending the copy (art. 15(4)). Items a brand shares
  with its locations are searched only as each location's copy; the brand
  owner checks the brand's own items by hand.
- **Erasure**: the owner's knowledge base is never edited by an erasure.
  The items that named the customer are flagged "Names an erased
  customer" in the knowledge editor; the owner removes the details and
  saves, which clears the flag. A later sync of a brand's shared item can
  drop the flag of its location copy, so a brand owner checks the shared
  text too.

The platform keeps no customer e-mail address, so nothing is matched by
e-mail.

## Afterwards

- Answer within the month. Only when a request is complex or one of many,
  extend by up to two more months and tell the person why **within the
  first month** (art. 12(3)).
- Record the answer date and what was done in the register; keep the
  register entry for [2 years], then delete it.
- A refused request (identity not proven, manifestly unfounded): explain
  why and that they may complain to the Garante (www.garanteprivacy.it).
- Review the register at the quarterly access review
  (`docs/security/access-review.md`): every open entry has a due date in
  the future.
