# AI Act classification and Article 50(2) assessment

The platform's record of how Regulation (EU) 2024/1689 (the AI Act)
applies to the assistant: its role, why it is not high-risk, why no
practice of Article 5 is used, what Article 50 asks of it and of the
businesses, and the decision on machine-readable marking (Article 50(2)).
It is a record prepared by the team for a lawyer's review and sign-off
(below), not legal advice. The tenant-facing guidance it leads to is the
help article "Using the AI assistant responsibly"
(`docs/help/en/ai-use-guidance.md`, Italian `docs/help/it/ai-use-guidance.md`);
staff training is `docs/security/ai-literacy.md`.

Reviewed: 2026-11-03. Review with every release that touches the AI
features (the pull request template's "AI features" item: prompts, tools,
models, the voice agent, anything that analyses callers or customers) and
at least once a year. `tests/legal/test_ai_act_assessment.py` fails when
the review is more than a year old, when a path below moved, or when code
under `app/` starts naming emotion, sentiment or biometric analysis before
this record and the DPIA cover it.

## The system and the roles

| Who | Role under the AI Act | Why |
| --- | --- | --- |
| The platform (the operator of Assistant Workshop) | **provider** of an AI system (Art. 3(3)), and downstream provider integrating general-purpose AI models | it develops the assistant (prompts, tools, guards, the voice agent's configuration) and makes it available to businesses under its own name |
| Each business using the assistant | **deployer** (Art. 3(4)) | it uses the system under its authority, with its own customers, its knowledge and its settings |
| OpenAI, Anthropic (language models), ElevenLabs (speech recognition and synthesis) | providers of general-purpose AI models or AI components used through their APIs | the platform does not train or place models on the market; their own obligations (Art. 53) stay with them |
| Customers and callers | affected persons | they talk to the assistant |

What the system does: it answers a business's customers in chat
(website widget, hosted chat page, messengers) and on the phone, from the
business's own facts; it takes bookings, requests and waitlist places
through a fixed set of tools (`app/registries/tools/`), hands a
conversation to the team when it cannot help, and writes summaries for the
team. Its post-call analysis records only whether a booking matches what
was said and whether the AI disclosure was spoken, with the collected
date, time and party size (`app/schemas/domain/call_analysis.py`). Voices
are presets the platform chose per language
(`app/registries/localization/voice_profile_registry.py`): owners cannot
upload or clone a voice.

## Article 5: no prohibited practice

| Art. 5(1) | Practice | Here |
| --- | --- | --- |
| (a) | subliminal, manipulative or deceptive techniques that distort behaviour | no: the assistant says it is an AI (`app/utilities/conversations/assistant_texts/ai_disclosure_texts.py`), answers only from the business's facts and its claims are checked before they are sent (`app/utilities/reply_guard/`); it answers honestly that it is an AI whenever asked, and owners' texts cannot override that rule |
| (b) | exploiting vulnerabilities of age, disability or social situation | no: nothing targets people by age, disability or situation; there are no outbound promotional calls, and campaigns reach only customers who consented |
| (c) | social scoring | no: no per-customer score or ranking of any kind (`docs/security/dpia.md`, "No-show history and profiling") |
| (d) | predicting criminal offences | not applicable |
| (e) | untargeted scraping of facial images | not applicable: no images of faces are collected |
| (f) | emotion recognition in the workplace or education | no: no emotion recognition at all, of callers or of staff |
| (g) | biometric categorisation | no: speech is turned into text to answer; voices are not used to identify or categorise people |
| (h) | real-time remote biometric identification | not applicable |

## Article 6 and Annex III: not high-risk

The system is not a safety component of a product under Annex I, and it
falls in none of the areas of Annex III: no biometrics (1), no critical
infrastructure (2), no education (3), no employment or worker management
(4; staff receive notifications, they are not evaluated), no access to
essential services (5: no creditworthiness, insurance pricing or
emergency-call dispatch; the assistant is not an emergency line and tells
callers to call 112), no law enforcement (6), migration (7) or justice and
democratic processes (8). The Article 6(3) derogation is therefore not
needed, and no registration in the EU database applies.

A change that would revisit this: screening job applicants for a business,
deciding on a customer's access to a service from their history (refusing
bookings, setting individual deposits), triaging emergency calls, or any
analysis of a person's emotions or biometric traits.

## Article 50: transparency

| Paragraph | Duty | Who | How it is met |
| --- | --- | --- | --- |
| 50(1) | people are told they interact with an AI | provider | every call opens with the spoken disclosure in the caller's language (`app/use_cases/conversations/build_call_greeting_use_case.py`, no field a business can edit) and the first reply of every chat with the written one (`app/utilities/conversations/assistant_texts/ai_disclosure_texts.py`); the widget shows "AI assistant" at all times; the post-call analysis checks the disclosure was said |
| 50(2) | synthetic audio and text marked in a machine-readable way | provider | assessed below |
| 50(3) | people exposed to emotion recognition or biometric categorisation are informed | deployer | not applicable: neither is used. If voice sentiment or emotion analysis is ever applied to callers, the business must inform them, the DPIA must cover it and this record must be updated first |
| 50(4) | deep fakes and AI text published on matters of public interest disclosed | deployer | not applicable: the assistant speaks for the business in a disclosed conversation; voices are stock presets, never a real person's clone. The terms' acceptable use rules do not yet forbid impersonation or voice cloning without consent: the next terms version adds it (owner action with the lawyer, GOV-01) |

## Article 50(2) assessment: machine-readable marking

The duty applies to providers of AI systems that generate synthetic
audio, image, video or text, from 2 August 2026, with the Commission's code
of practice on marking and labelling as the reference. Secondary sources
report that Regulation (EU) 2026/1744 (the "Digital Omnibus on AI") gives
systems placed on the market before 2 August 2026 until **2 December 2026**
to comply; this date is **to be verified against the Official Journal
text** by the lawyer before it is relied on.

| Output | Stored or shared? | Decision |
| --- | --- | --- |
| Synthetic speech on calls (ElevenLabs, streamed to the telephone network) | not stored by the platform as such; heard once in a disclosed call | Marking the audio itself is not feasible on the telephone path: the network's narrow-band codecs (G.711, AMR) carry no metadata and do not preserve audio watermarks reliably. The disclosure that opens every call is the measure. The voice provider's own marking or watermarking is switched on where it offers one (owner action: confirm in the ElevenLabs contract and console, record the date here). |
| Call recordings (only when the owner turns them on) | stored for the business, sealed per business (`app/utilities/security/recording_encryption.py`); downloaded by the team or exported | A recording is a record of a two-party call between the caller and the AI, kept as evidence for the business, not content published as authentic. Each recording belongs to a call whose conversation is marked as the AI's in the cabinet and the export (below). No in-file audio watermark is added: decision to revisit if recordings are ever shared outside the business or the code of practice names call recordings. |
| Generated text in chats and messengers | delivered once to the customer in a disclosed conversation; stored with the conversation | Every stored message carries its author as data (`MessageAuthor.ASSISTANT` versus `STAFF` and `CUSTOMER`, `app/schemas/constants/conversations.py`), which the API, the cabinet and the full export keep: machine-readable marking within the platform's own surfaces. Messenger platforms (WhatsApp, Telegram, Instagram, Messenger) take plain text only, so no metadata can travel with a message there; the disclosure at the start of the conversation is the measure. |
| Summaries, campaign texts and payment links the assistant writes for the team or sends on its behalf | sent as the business's messages | The business is the author of what it sends; campaign texts are templates the business approves. Not marked; covered by the business's own transparency (help article). |

Conclusion (for sign-off): the platform meets Article 50(1) on every
channel; for Article 50(2) it marks generated text as the assistant's in
its own data and export, relies on the disclosure for the real-time audio
where marking is not technically feasible, and asks its voice provider for
marking where offered. The decision is re-examined when the code of
practice is final, when the Official Journal date is verified, and when
recordings or generated audio start leaving the business.

## Article 4: AI literacy

The platform trains its own staff (support, sales, engineering) on what
the assistant can and cannot do, prompt injection and social engineering,
and data protection, with records per person (`docs/security/ai-literacy.md`).
Businesses receive the deployer guidance for their own staff
(`docs/help/en/ai-use-guidance.md`): disclosure, limits, checking the
assistant's answers, human oversight (pausing it, switching tools off,
taking over a conversation) and what to tell staff and callers.

## Sign-off

Prepared by the team on 2026-11-03. Legal review and sign-off: [lawyer's
name, date]. Official Journal check of the Regulation (EU) 2026/1744 date:
[date, result]. Voice provider's marking: [what ElevenLabs offers, date].
