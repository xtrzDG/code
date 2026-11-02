# At run time: the assistant, calls, bookings and money

The second half of `docs/security/runtime-protections.md`, which lists the
platform's own edge (configuration, sign-in, the API, the cabinet,
monitoring). This page lists what the AI agent, the phone line, bookings,
payments and customers' data refuse and limit, each with its code and the
test that proves it. `tests/legal/test_operations_documents.py` fails when
a path here moves.

## The AI agent

- **Fenced values**: what customers wrote reaches the model only inside
  one-line `<customer_value>` blocks it cannot close (the contact's name,
  request details, conversation summaries, the guest's name in booking
  results); team notes are `<team_note>`, imported knowledge
  `<untrusted>`, the owner's tone and rules `<owner_text>`, which never
  override the platform's rules. A customer who types one of these tags is
  neutralised like a forged header, and customer values never count as
  trusted evidence for the reply guard
  (`app/utilities/conversations/untrusted_text.py`,
  `app/utilities/conversations/customer_text_fencing.py`,
  `app/utilities/conversations/owner_text_fencing.py`;
  `tests/brain/test_untrusted_customer_values.py`,
  `tests/assembly/test_untrusted_blocks.py`,
  `tests/security/test_owner_text_rendering.py`).
- **Typed tool inputs**: a guest's name at most 60 characters on one line
  without markup or invisible characters, a booking note 500, lead details
  1,000, a budget 100, a handoff summary 1,000; the website chat checks a
  visitor's name the same way (422) (`tests/brain/test_tool_input_limits.py`,
  `tests/channels/test_widget_contact_names.py`). Owner texts are saved only
  as one line without `< > [ ] { }` or a backtick and not starting with `#`
  (`app/schemas/typings/profiles/constrained_strings.py`).
- **Caps**: at most 5 tool calls run per model response, and the business's
  spend is checked again before every later model round
  (`app/use_cases/conversations/replies/round_limits.py`;
  `tests/brain/test_reply_round_limits.py`); per contact and 24 hours at
  most 5 leads made in conversations and 3 staff alerts for handoffs (an
  emergency always alerts; `app/utilities/conversations/contact_daily_caps.py`;
  `tests/operations/test_contact_daily_caps.py`); a conversation is
  answered for at most 150 customer messages
  (`app/use_cases/conversations/turns/turn_gate.py`;
  `tests/brain/test_conversation_length_limit.py`). Test chats count toward
  none of them.
- **Reply guard**: a reply that repeats 5 or more words in a row of a team
  note the model was shown, or links to a host the business did not
  publish (other than the platform's hosts, well-known map services and
  Stripe's and Flitt's checkout), is rewritten once, then handed to the
  team (`app/utilities/reply_guard/team_note_quotes.py`,
  `app/utilities/reply_guard/reply_links.py`;
  `tests/brain/test_reply_guard_links_and_notes.py`,
  `tests/brain/test_reply_link_vetting.py`).
- **Disclosure**: every channel says it is an AI assistant at the start, in
  every language the detector reads; the first messenger reply links the
  business's privacy notice; asked "are you a real person?", it says it is
  an AI and offers a colleague
  (`app/utilities/conversations/assistant_texts/ai_disclosure_texts.py`;
  `tests/brain/test_first_reply_disclosure.py`).
- **Emergencies and allergens**: the assistant is not an emergency
  service; it names the country's emergency number (112), which counts as
  platform evidence, and hands off as critical; allergen and diet answers
  come only from the business's data and always suggest confirming with
  the staff (`app/utilities/assembly/instruction_rule_sections.py`;
  `tests/assembly/test_safety_rules_in_instruction.py`).

## Calls

- **A caller ID is not authentication**: the voice agent learns nothing
  about the caller from it, and `list_my_bookings`, `cancel_booking` and
  `reschedule_booking` are refused on calls with advice to hand off
  (`app/utilities/channels/voice_service.py`,
  `app/use_cases/voice/authenticate_voice_tool_call_use_case.py`;
  `tests/channels/test_voice_caller_id_tools.py`). A customer's cancel or
  move needs a contact or a proven phone and is refused from a phone call;
  staff need their user (`tests/operations/test_booking_requesters.py`).
  The phone instruction names only the voice agent's tools: it creates
  bookings and passes existing ones to a colleague with
  `handoff_to_human`, and it never promises a text unless a tool result
  says one is sent (`app/utilities/assembly/phone_instruction_sections.py`;
  `tests/assembly/test_phone_instruction.py`,
  `tests/brain/test_voice_text_promises.py`). The missed-call text-back
  writes to the number's WhatsApp account, or to a new contact that holds
  only that account and no verified phone; a caller ID never finds a
  contact by a verified or given phone and never adds an identity to one
  (`app/use_cases/voice/missed_calls/text_back_conversation.py`;
  `tests/calls/test_text_back_delivery.py`).
- **Agents** start a web or WebSocket conversation only with a signed URL
  made with the platform's key (calls to the business's number are not
  affected) and take at most 5 calls at once and 300 a day
  (`app/adapters/voice/elevenlabs_agent_config.py`;
  `tests/channels/test_voice_agent_creation.py`); a business takes no new
  call past 600 call minutes in its day, and a number is refused at the
  call's start, also by the carrier fallback, when any contact holding it
  is blocked (one that proved it, the call-only and per-call contacts, the
  WhatsApp customer of the number, any contact that gave it); a STOP or a
  block of any of them also stops the text-back
  (`app/use_cases/voice/call_admission.py`,
  `app/utilities/calls/call_contacts.py`;
  `tests/spend_guard/test_voice_caps.py`,
  `tests/calls/test_call_fallback_blocked.py`,
  `tests/calls/test_blocked_callers_by_number.py`).
- **Toll fraud**: calls are put through only to a mobile or landline of the
  business's country or an EU state, never to premium, shared-cost,
  special-tariff, satellite or international premium numbers, checked
  when the owner saves the staff number or a manager's WhatsApp or SMS
  number (422, nothing stored) and again before every transfer and
  fallback dial (`app/utilities/channels/transfer_destinations.py`,
  `app/use_cases/businesses/manager_contact_rules.py`;
  `tests/channels/test_transfer_destinations.py`,
  `tests/businesses/test_manager_contact_destinations.py`); a transfer
  happens only while the business is open and after the owner confirmed
  that staff were told (`tests/channels/test_call_transfers.py`).
- **Recording is off by default** (`app/schemas/domain/call_settings.py`):
  without it the audio is deleted after the call and the transcript is kept
  redacted; nothing of the staff part of a connected transfer is kept; the
  greeting mentions a recording only while recording is on and always says
  where the privacy notice is, and the hosted chat's privacy page says
  calls are recorded only then. Only the call settings switch recording;
  the profile's old recording-notice flag is deprecated and changes
  nothing (`tests/calls/test_call_recording_settings.py`,
  `tests/calls/test_declined_recordings.py`,
  `tests/brain/test_call_greeting_without_recording.py`,
  `tests/sharing/test_privacy_notice_calls.py`).

## Bookings, money and data

- **Booking caps**: customers book at most 365 days ahead and 5 times a day
  per contact; anonymous bookings (website chat, phone) at most 200 a day
  per business and 10 per client network
  (`app/use_cases/bookings/booking_limits.py`;
  `tests/operations/test_booking_daily_caps.py`).
- **Platform brakes**: a SUPER admin pauses every assistant at once (step-up,
  a reason, audited), and at `PLATFORM_DAILY_SPEND_STOP_PERCENT` of the
  daily budget every assistant stops calling the model until UTC midnight:
  customer turns go to the team, calls to the forwarding number, the
  background model jobs ask no model (quality sampling and topics skip
  the run, summaries wait an hour, knowledge indexing fails and is retried,
  a website import fails, a finished call's summary is skipped and staff
  get the report without it, an autotest run queued before the brake is
  skipped when the worker starts it), and owners' costly actions (menu
  import, starting a website import, autotest runs, alias suggestions,
  renting a number) get 409 `platform_brake`, which the cabinet words by
  its detail in English and Italian (`app/utilities/spend/platform_brakes.py`,
  `app/use_cases/spend_guard/admit_owner_action_use_case.py`,
  `app/use_cases/voice/summaries/summarize_call_use_case.py`;
  `tests/spend_guard/test_platform_pause_reach.py`,
  `tests/calls/test_call_summary_brake.py`,
  `tests/assembly/test_autotest_brake_at_start.py`,
  `web/src/api/platformBrake.test.ts`,
  `tests/quality/test_quality_sampling_brake.py`,
  `tests/spend_guard/test_platform_brakes.py`,
  `tests/spend_guard/test_platform_pause_admin.py`;
  `docs/operations/runbooks/platform-brakes.md`).
- **Queued jobs stay in their tenant**: a business-scoped job whose payload
  names another business than the job is refused, logged as
  `job_tenant_mismatch` and dead-lettered
  (`app/operators/business_scoped_pipeline_operator.py`;
  `tests/storage/test_job_tenant_isolation.py`).
- **Payment reconciliation**: every day the checkout orders of the last 7
  days are compared with Flitt's and Stripe's own status; mismatches are
  stored, logged and alerted (`payment_mismatch`)
  (`app/use_cases/billing/reconciliation/reconcile_payments_use_case.py`;
  `tests/payments/test_payment_reconciliation.py`;
  `docs/operations/runbooks/payment-mismatch.md`).
- **Erasures survive a restore**: each customer erasure is recorded in the
  backup bucket (ids and the moment only), and a daily job erases again a
  customer a restore brought back
  (`app/use_cases/compliance/record_contact_erasure_use_case.py`,
  `app/use_cases/compliance/reapply_contact_erasures_use_case.py`;
  `tests/compliance/test_contact_erasure_ledger.py`,
  `tests/storage/test_contact_erasure_ledger_on_postgres.py`).
- **Marketing consent**: invitations to come back go only to customers with
  an active consent, recorded with its wording's version, source, who and
  when, and only in the chat the anchor booking was made in (a phone or
  website-chat booking gets none); STOP, the suppression list and a block
  always win, and a STOP in a chat already stopped withdraws a consent
  given after it, in one atomic change of the card
  (`app/use_cases/campaigns/campaign_writer.py`,
  `app/use_cases/feedback/answers/messaging_preferences.py`,
  `app/schemas/domain/contacts.py`;
  `tests/campaigns/test_campaign_consent.py`,
  `tests/customers/test_marketing_consent_stop.py`,
  `tests/bookings/test_booking_page_consent.py`).
