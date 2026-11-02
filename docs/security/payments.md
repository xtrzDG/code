# Payments and card data

How money moves through the platform, why no card data is ever ours, what
that makes our PCI DSS scope, and who is responsible for what when a
business asks its customers for deposits. The controls named here are in
the code cited next to them, and their tests run in CI.

Status: drafted by engineering from the code (2026-11). A QSA or the
acquirers' PCI teams and a lawyer still review it before it is published
to businesses (owner step at the end).

## Two payment flows

| | Platform billing | Deposits |
| --- | --- | --- |
| Who pays whom | a business pays the platform (subscription, setup fee, voice packs) | a customer pays a business (a table, a room, a banquet) |
| Merchant of record | the platform | the business |
| Payment page | Stripe Checkout, or Flitt's hosted checkout (redirect) | the business's own PSP page (Stripe Payment Link, Flitt, SumUp, a bank's page, ...) |
| What the platform holds | the order, its status and amount; for retries of a declined Flitt charge, Flitt's card token (`rectoken`) sealed with the key ring | the deposit request (amount, reference, the page it was asked on, a key in the page's address sealed); never whether a card was used |
| Card data on platform systems | none | none |

### Platform billing

1. The cabinet asks the API for a checkout. The API creates a Stripe
   Checkout session (`app/clients/stripe/stripe_client.py`) or a Flitt
   order (`app/clients/flitt/flitt_client.py`) and answers with the
   provider's URL. The browser leaves for the provider's own page; the
   cabinet's CSP allows forms to post only to itself and `pay.flitt.com`
   (`web/src/server/contentSecurityPolicy.ts`).
2. The business types the card on the provider's page. The PSP applies
   SCA (3-D Secure) and keeps the card; the platform receives at most a
   token (`rectoken`) for retrying a declined renewal, sealed at rest
   (`app/use_cases/billing/payment_webhook/card_on_file_recording.py`).
3. The provider tells the API the result by webhook. Nothing in the
   browser's return URL is trusted:
   - the signature is checked over the raw body before parsing, in
     constant time, failing closed without a secret (Stripe: 300 s
     tolerance; Flitt: its SHA-1 signature, `app/clients/flitt/flitt_protocol.py`);
   - a Flitt approval or refund takes effect only when Flitt's status API
     reports the same status and amount for the order
     (`app/adapters/payments/flitt_status_confirmation.py`); otherwise the
     API answers 409 and Flitt sends it again;
   - each order's notifications are applied under a lock across API
     instances (`app/registries/locks/payment_notification_lock_registry.py`)
     against the keys the order already applied, so two copies of one
     delivery apply once (`tests/billing/test_payment_notification_races.py`);
   - the daily reconciliation compares every open order with the
     provider's state (`app/use_cases/billing/reconciliation/`).

### Deposits

1. The owner adds their own payment page in Settings → Deposits: an
   `https` address on a public host, without credentials, with only the
   placeholders the platform fills (`{amount}`, `{amount_minor}`,
   `{currency}`, `{reference}`). An address that carries a key is stored
   sealed and never shown again (`app/utilities/deposits/payment_link_addresses.py`).
   Adding or changing a page needs a recent sign-in and is audited.
2. A booking or banquet the owner's policy covers gets a deposit: the
   amount comes from the policy, never from the model. The platform writes
   the payment line under the assistant's reply (the model never writes a
   link or an amount): the amount, the link, until when the place is held,
   the reference and the refund terms in the customer's language
   (`app/utilities/deposits/deposit_refund_terms.py`; the last moment of a
   free cancellation is the one settling applies). On a call the line is
   texted after the call, never read aloud.
3. The customer pays on the business's PSP page (that PSP applies SCA).
   Staff mark the deposit paid when they see the money in their merchant
   account; the platform never learns card details. A cancellation before
   the cutoff tells staff to refund it in their merchant account.

There are no no-show or late-cancellation fees charged by the platform: no
card is saved for a business's customers, so there is no
merchant-initiated transaction and no mandate.

## Card numbers customers type or say anyway

The assistant is told never to ask for or accept card numbers, security
codes, PINs or banking passwords, never to repeat one and to point to the
payment link (the prohibition rules,
`app/utilities/assembly/instruction_rule_sections.py`; evals
`carddata__it`, `carddata__en`). A customer may still send one. A
Luhn-valid 13 to 19 digit number (spaced, dashed, or said digit by digit),
the digits said right after it, a named security code, an IBAN and an ID
number become placeholders (`app/utilities/privacy/sensitive_numbers.py`):

| Where | Masked at |
| --- | --- |
| a messenger message and its captions, before the inbox stores it | `app/utilities/deliveries/inbox_messages.py` |
| an Instagram comment | `accept_instagram_comments_use_case.py` |
| the website chat, the hosted chat, the owner's test chat, the API | `app/use_cases/conversations/turns/inbound_message_rules.py` |
| a voice note's transcript | `transcribe_voice_note_use_case.py` |
| the turn the model reads (also messages stored before masking) | `app/use_cases/conversations/replies/customer_turn.py` |
| a call's transcript, recorded or not, and its summary | `app/adapters/voice/elevenlabs_post_call_reading.py` |
| the quality journal (Langfuse), even with raw text allowed | `app/adapters/llm/tracing_llm_adapter.py` |
| log lines (message, traceback, text fields) | `app/utilities/observability/log_formatting.py` |
| error reports (Sentry) | `app/facilitators/observability/sentry_event_scrubbing.py` |

A call whose caller read out a card number or a security code keeps no
audio, even where the business records calls: the platform deletes its
copy and the voice platform's, as for a declined recording
(`app/use_cases/voice/finished_call/call_recording_policy.py`). Tests:
`tests/privacy/test_card_numbers_in_chat.py`,
`tests/calls/test_card_numbers_in_calls.py`,
`tests/platform/test_log_secret_redaction.py`.

What masking cannot reach:

- During a live call the voice platform's model hears what the caller
  says; the prompt tells it not to ask, repeat or accept card data. The
  voice platform's own retention applies to its copy until the platform
  deletes it.
- The messenger (WhatsApp, Telegram, Instagram, Messenger) keeps its copy
  of the customer's message on the customer's and the business's devices.
- Conversations stored before masking existed are masked for the model,
  not rewritten in storage.

## PCI DSS scope

The platform is a merchant only for its own billing, and there it
outsources every card function to PCI DSS validated providers through a
redirect (Stripe Checkout, Flitt's hosted checkout). That is the profile
of the Self-Assessment Questionnaire A. Its eligibility points, as the
platform meets them:

| SAQ A eligibility | How the platform meets it |
| --- | --- |
| card-not-present (e-commerce) transactions only | billing is online only; no terminal, no phone orders |
| all processing of account data is outsourced to PCI DSS compliant third parties | Stripe (Level 1) and Flitt (certificate on file, `docs/operations/vendor-register.md`) |
| the payment page comes entirely from the provider (redirect) | the cabinet sends the browser to the provider's URL; no card field, iframe or provider script on our pages |
| no electronic storage, processing or transmission of account data on our systems | no PAN or security code is ever accepted; one typed or said by mistake is masked before storage, model, logs and traces, and its call audio is deleted (above) |
| paper records with account data, if any, are not electronic | none exist |
| the pages that send to the payment page are protected | the cabinet's CSP runs scripts only with the page's nonce, enforces Trusted Types, posts forms only to itself and `pay.flitt.com` and reports violations (`web/src/server/contentSecurityPolicy.ts`); the billing pages load no third-party script (Turnstile runs on sign-in, Facebook's SDK on the Meta connection pages) |

For deposits the platform is not the merchant and never sees the card, so
it does not enter the business's cardholder data environment; it writes a
link to the business's PSP page. It is still a third party whose conduct
affects how the business's customers pay, hence the matrix below.

## Responsibility matrix for businesses

| Duty | The business (merchant) | The platform | The business's PSP |
| --- | --- | --- | --- |
| Own merchant account, its SAQ and its attestation | yes (usually SAQ A for a hosted payment link) | no | supports it |
| Payment page that takes the card, PCI DSS validated, with SCA | chooses one | checks only that the address is `https` on a public host without credentials | provides and runs it |
| Keep the page's address and any key in it secret | gives it only in Settings → Deposits | stores a keyed address sealed; never shows it again | |
| Amount and reference of each deposit | sets the policy | computes them from the policy, never from the model | charges what the page asks |
| Deposit, cancellation and refund terms before payment | sets the hold and the refund cutoff; has the wording reviewed (Codice del consumo art. 49) | states them in every deposit line and reminder, in the customer's language | |
| Never ask for card data in chats or calls | staff never ask in their own replies | the assistant never asks, repeats or accepts it; masking above | |
| Refunds | refunds in the merchant account | tells staff which deposit to refund and when | executes the refund |
| Card data a customer sends anyway | deletes it from the messenger if staff saw it | masks it and deletes call audio holding it | |
| Disputes and chargebacks | handles them with the PSP | gives the booking, the line sent and its time | runs the process |
| Fraud tooling on the page (card testing) | turns on the PSP's tooling | asks one deposit per booking or banquet request (asking again sends the same one) | provides it |

## Owner steps

- Have a QSA or the acquirers (Stripe, Flitt) confirm the SAQ A
  eligibility above and file the yearly SAQ A with its attestation.
- Publish the responsibility matrix to businesses (the help centre and the
  terms) after the lawyer's review, together with the deposit, cancellation
  and refund wording of the deposit lines.
- Keep Flitt's PCI DSS certificate and Stripe's attestation on file in the
  vendor register each year.
