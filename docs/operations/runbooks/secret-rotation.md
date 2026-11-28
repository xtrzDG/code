# Rotating a webhook secret without refusing callbacks

**When:** the yearly rotation of `docs/security/secrets-inventory.md`, a
person who could read the secret leaves (`../offboarding.md`), or a
suspected leak (then also `data-breach.md`). Severity: none for a planned
rotation; a leak is SEV1.

The providers sign their callbacks with a shared secret. Changing it at
the provider and on Render cannot happen in the same second, so for these
five the platform accepts a second, previous value while the switch
lasts (`app/utilities/config_helpers/secret_rotation.py`;
`tests/platform/test_previous_secrets.py`,
`tests/channels/test_webhook_secret_rotation.py`):

| Secret | Its previous value | What it verifies |
| --- | --- | --- |
| `ELEVENLABS_WEBHOOK_SECRET` | `ELEVENLABS_WEBHOOK_SECRET_PREVIOUS` | the voice platform's call start and post-call webhooks, and the tool calls' secret derived from it |
| `META_APP_SECRET` | `META_APP_SECRET_PREVIOUS` | WhatsApp, Instagram and Messenger webhooks (`X-Hub-Signature-256`) |
| `FLITT_SECRET_KEY` | `FLITT_SECRET_KEY_PREVIOUS` | Flitt's payment callbacks |
| `ZADARMA_API_SECRET` | `ZADARMA_API_SECRET_PREVIOUS` | Zadarma's PBX notifications |
| `TWILIO_AUTH_TOKEN` | `TWILIO_AUTH_TOKEN_PREVIOUS` | Twilio's voice fallback and dial-status callbacks |

A verifier tries the current value first, then the previous one. Nothing
the platform sends is ever signed with the previous value, and a previous
value without a current one opens nothing. `ENCRYPTION_KEYS` has its own
ring and procedure (`../backup-restore.md`, "Key rotation");
`SUPPRESSION_LIST_KEY` cannot be rotated without orphaning the stored
digests of opted-out numbers.

## Rotate

1. **Keep the old value.** On Render, in the env group
   `workshop-backend` (every backend service reads it): set
   `<NAME>_PREVIOUS` to the value `<NAME>` holds now, and deploy. The
   Blueprint does not declare these variables; production refuses a
   previous value whose current one is not set
   (`docs/dev/environment.md`).
2. **Switch.** Create the new secret in the provider's console (ElevenLabs
   webhook settings, the Meta app's Basic settings, Flitt's merchant
   portal, Zadarma's API settings, Twilio's auth tokens) and set `<NAME>`
   to it on Render; deploy at once. Callbacks signed with either value are
   accepted throughout. What the platform itself does with the secret
   (Twilio's and Flitt's API calls, Meta's sign-in) uses the new value
   from this deploy on, so make the provider's change and the deploy one
   step. Twilio: create the secondary auth token, set it as
   `TWILIO_AUTH_TOKEN`, deploy, then promote it in the console (API calls
   accept both tokens until the promotion; callbacks come signed with the
   old primary until then, which `TWILIO_AUTH_TOKEN_PREVIOUS` accepts).
   Right after the promotion, re-import the rented numbers in ElevenLabs
   (below).
3. **Watch** the security log for `security_event=webhook_delivery_refused`
   with that `provider` (`../observability.md`, "Security and payment
   events") and the channel's own signals (`/admin/system`): nothing new
   should be refused.
4. **Retire the old value** once the provider signs only with the new one
   (a day is plenty; for Flitt and Zadarma wait until callbacks queued
   before the switch have arrived): delete `<NAME>_PREVIOUS` from the env
   group and deploy.
   A leaked value is retired as soon as step 2 is live.

## Twilio: re-import the rented numbers in ElevenLabs

`TWILIO_AUTH_TOKEN` is also the account that rents phone numbers
(`PHONE_NUMBER_PROVIDER=twilio`), and ElevenLabs keeps the token it was
given when it imported each rented number: it takes that number's calls
with it (`app/clients/elevenlabs/elevenlabs_phone_numbers_client.py`). The
platform never hands ElevenLabs a new token: the job
`maintain_phone_numbers` imports only a number ElevenLabs does not have
yet, and no command re-imports the others yet. Once the old token stops
working at Twilio (the promotion in step 2), every rented number must be
re-imported by hand, and until then its calls can fail:

1. List the account's active numbers in the Twilio console (Phone
   Numbers); each one's label in ElevenLabs is its business's name.
2. In the ElevenLabs console (Phone numbers), replace each of them: remove
   it and import it again as a Twilio number with `TWILIO_ACCOUNT_SID` and
   the new token, assigned to the agent that answered it.
3. Call each number: the business's agent answers.
4. A number imported by hand has a new ElevenLabs id, and the platform
   keeps the old one, which it uses to move the number to another agent
   and to remove it from ElevenLabs. So if the business's voice agent is
   ever created anew (a pause or a plan without voice removed it, and the
   business published again), assign the number to the new agent in
   ElevenLabs by hand (the worker's log keeps saying the number "is not
   attached to its voice agent yet"), and when the number is given back,
   remove it from ElevenLabs by hand too.

## Afterwards

- Write the rotation in the log at the end of
  `docs/security/secrets-inventory.md` (secret, date, who, why).
- After a leak: look in the security log for deliveries the old value
  signed after step 2, and treat each as a possible forgery
  (`data-breach.md`).
