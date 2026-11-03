# Declined payments of a business (card testing)

**Alert:** `tenant_payment_declines` (SEV2): the payments of one business
were declined 5 times within two hours, or 10 times. Someone may be
testing stolen cards on the platform's payment pages (checkout, "Save
card") under that business's account. From the 10th decline the business
opens no new payment page (the cabinet answers 429 with Retry-After)
until the hourly windows cool down; the brake lifts by itself after one
to two quiet hours. Retries of a declined automatic charge (the dunning
job) do not count. A warning line of the worker names the business.

## Check

1. Which business? Search the worker logs for "payments declined within
   two hours" with its `business_id`; open the client on Admin → Clients.
2. Is the account new, still in its trial, with no real activity? Many
   declines from different cards on a new account are card testing; a few
   declines of one card of a long-standing owner are not.
3. Look at the orders at Flitt or Stripe (merchant console): card
   countries, amounts, the times of the attempts.

## Mitigate and fix

- Card testing: suspend the client on Admin → Clients, keep the evidence
  (order ids, times), and tell the payment provider's risk team. Do not
  lift the brake by hand.
- A real owner with a failing card: tell them to wait an hour and try
  another card, or to call their bank; nothing to change on the platform.

## Afterwards

The alert resolves once the signal windows are quiet. Record the
business, the number of attempts and the provider's answer in the
incident record.
