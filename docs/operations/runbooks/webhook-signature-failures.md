# Webhook signature failures

**Alert:** `webhook_signature_failures` (SEV2): more than 30 webhook
deliveries were refused in 15 to 30 minutes as unsigned, badly signed or
stale (the API processes count every refusal, at most one a second per
process). Each refusal is also an `app.security` line with
`security_event=webhook_delivery_refused`, the `provider`, the `reason`
and the client network ([log inventory](../../security/log-inventory.md)).

## Check

1. In the log store, group the `webhook_delivery_refused` lines of the last
   hour by `provider` and `reason`. One provider with `invalid_signature`
   right after a secret rotation is a secret out of step; many networks
   or providers at once is probing.
2. Did someone rotate a webhook secret (Meta app secret, Telegram secret
   token, Twilio auth token, Stripe or Flitt signing secret) without the
   `*_PREVIOUS` variable ([secret-rotation](secret-rotation.md))?
3. Are real deliveries lost? The channel's messages stop arriving and the
   provider's dashboard shows failed deliveries.

## Mitigate and fix

- A secret out of step: set the provider's new secret (and the old one in
  the `*_PREVIOUS` variable until the provider switched), redeploy; the
  provider retries its deliveries.
- Probing: nothing to do while the refusals hold; the admission
  middleware's flood budget answers 429 to a flooding network. Block the
  network at the edge when it persists.

## Afterwards

The alert resolves once the refusals of a window fall to 30 or fewer. Note
a probing episode in the security log of the incident record.
