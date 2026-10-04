---
summary: Send the calls you miss to the assistant with one code per condition, for any mobile operator.
topic: channels
order: 50
keywords: call forwarding, forwarding, phone, calls, missed calls, busy, no answer, unreachable, operator, carrier, magti, silknet, cellfie, gsm code, **61, **67, **62, ##002#
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

- **Magti** publishes exactly these codes (*61 no answer, *67 busy, *62 unreachable).
- **Silknet** and **Cellfie**, and most operators in other countries, accept the same standard GSM codes. If a code does not work, the operator may switch forwarding on in its app or through its support.

## Good to know

- Landlines and office exchanges (PBX) set forwarding in their own settings; ask whoever maintains them.
- If you disconnect the Phone channel, also dial `##002#`, or callers will hear that the number is unavailable.
- **Settings → [Calls](cabinet:settings/calls)** can text back callers who did not get through.
