---
summary: Send the calls you miss to the assistant with one code per condition, for any mobile operator.
topic: channels
order: 50
keywords: call forwarding, forwarding, phone, calls, missed calls, busy, no answer, unreachable, operator, carrier, tim, vodafone, windtre, iliad, verizon, t-mobile, at&t, united states, usa, gsm code, **61, **67, **62, ##002#, *71, *73, ##004#
related: channels, inbox
---
# Call forwarding

Staff still answer first. The calls they miss, or that come while the line is busy or the phone is off, go to the assistant: it answers, books and sends you a summary of the call.

## Turn it on

You need the assistant's number first: connect the **Phone** channel in **Assistant → [Channels](cabinet:assistant/channels)**. The page then shows the codes with your number filled in.

Take the phone with the SIM card whose number customers call and dial each code, then press call:

| When | Code |
| --- | --- |
| You do not answer | `**61*number#` |
| The line is busy | `**67*number#` |
| The phone is off or out of coverage | `**62*number#` |
| Switch all forwarding off | `##002#` |

After each code wait for the operator's confirmation on the screen. Then check: call your number from another phone and do not answer; the assistant should pick up.

## By operator

- **TIM**, **Vodafone**, **WindTre** and **Iliad**, like most mobile operators, accept these standard GSM codes.
- If a code does not work, the operator may switch forwarding on in its app or through its support.

## In the United States

US carriers take different codes, so for a business in the US the page lists **Verizon**, **T-Mobile** and **AT&T** first: open yours and dial its codes one at a time. Any other carrier gets the standard codes under **Other carriers**. For an assistant number of +1 212-555-0123 the page shows:

| Carrier | Codes |
| --- | --- |
| Verizon | `*712125550123` (no answer or busy: one code for both), `*73` (switch off) |
| T-Mobile | `**61*12125550123#`, `**67*12125550123#`, `**62*12125550123#`, `##004#` (switch off; brings voicemail back) |
| AT&T | `**61*2125550123#`, `**67*2125550123#`, `**62*2125550123#`, `##002#` |
| Other carriers | `**61*12125550123#`, `**67*12125550123#`, `**62*12125550123#`, `##002#` |

- None of these codes is confirmed with the carrier yet, and the page says so: if a code fails, ask your carrier.
- Verizon forwards once your phone has rung 3 to 6 times, and it has no code for a phone that is off or out of coverage: those calls still go to voicemail.
- On T-Mobile your voicemail is itself the no-answer forwarding, so the no-answer code replaces it. To let the phone ring longer first, put `**25` or `**30` (seconds) before the last `#` of the no-answer code.
- On an iPhone, if unanswered calls still go to voicemail, turn Live Voicemail off in the Phone settings.
- The page never shows a code that forwards every call (Verizon's `*72`, the `*21*` codes): your staff keep answering first.

## Good to know

- Landlines and office exchanges (PBX) set forwarding in their own settings; ask whoever maintains them.
- If you disconnect the Phone channel, also dial `##002#` (on Verizon `*73`, on T-Mobile `##004#`), or callers will hear that the number is unavailable.
- **Settings → [Calls](cabinet:settings/calls)** can text back callers who did not get through: on WhatsApp, and by SMS where it can be sent (the page says when it cannot).
