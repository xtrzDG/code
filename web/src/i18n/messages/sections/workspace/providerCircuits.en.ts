/**
 * `providerCircuits.*` texts: the provider circuits card of the admin
 * System page, in English: the reference the other languages are typed
 * against. Circuit names of language models stay as the API sends them.
 */

export const providerCircuitsEn = {
  title: "Provider circuits",
  description:
    "Every provider the workers send through has a circuit breaker. Five failures within a minute open it: messages wait without a call, and one trial goes through 30 s later. Each provider holds at most half of a worker's delivery threads.",
  none: "No worker has reported its circuits",
  noneDescription: "Workers report their circuits with every beat; a worker of an older release reports none.",
  circuit: "Circuit",
  state: "State",
  workers: "Workers not closed",
  workersOf: "{notClosed} of {total}",
  failures: "Failures, last minute",
  opened: "Opened",
  states: {
    closed: "Closed",
    half_open: "Trying again",
    open: "Open",
  },
  providers: {
    meta: "Meta (WhatsApp, Messenger, Instagram)",
    telegram: "Telegram bots",
    platform_bot: "Platform bot",
    twilio_sms: "SMS (Twilio)",
    smtp: "E-mail (SMTP)",
    flitt: "Payments (Flitt)",
    stripe: "Payments (Stripe)",
    elevenlabs: "Voice (ElevenLabs)",
    web_push: "Web push",
  },
} as const;
