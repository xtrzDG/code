# Payment mismatch with Flitt or Stripe

**Alert:** `payment_mismatch` (SEV2): the daily `reconcile_payments` job
compared the checkout orders written to in the last 7 days (a Stripe
subscription's order one billing interval more, for its renewals) with
what the provider says now (Flitt's order status; for a Stripe
subscription its latest invoice, else the order's invoice or checkout
session) and found payments that differ in a way that moves money. Every mismatch is also a structured log line
(`payment_event=payment_reconciliation_mismatch`, with the order, the
business, the provider and both statuses; never card data).

**Where:** `GET /v1/admin/payments/reconciliation` (SUPER and BILLING
admins): the latest run, how many orders it compared and could not read,
and each mismatch with its client.

## The kinds

- `paid_at_provider`: the provider took the money, the platform has the
  payment unpaid. Usually a lost or refused notification: the owner paid
  and may be dunned or suspended. Check the provider's dashboard, then
  mark the invoice paid on the client's admin page (Admin → client →
  "Record a payment", audited) or ask the provider to resend the
  notification.
- `failed_at_provider`: the provider declined or let the payment expire,
  the platform has it paid. The client uses the service unpaid: check the
  provider, then contact the owner; the grace and dunning rules apply once
  the invoice is open again.
- `renewal_paid_at_provider`: Stripe charged a renewal of the client's
  subscription that the platform never recorded ("Here" shows the order's
  earlier payment). A lost notification, handled like `paid_at_provider`:
  resend the `invoice.paid` event from Stripe's dashboard or record the
  payment by hand.
- `reversed_at_provider`: a refund or a chargeback the platform did not
  record. Check the provider, record the refund and decide about the
  subscription with billing.

## Afterwards

The alert resolves when the next day's run finds no mismatch. A run whose
"could not be read" count is high points to provider credentials (a
provider refusing the read counts there: every order was opened at that
provider) or an outage ([provider-circuits](provider-circuits.md)).
Flitt's later automatic charges are orders of Flitt's own and are not
compared: only the first payment of a Flitt order is.
