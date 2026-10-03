/**
 * `adminSecurity.*` texts of the platform admin's Encryption keys page
 * (/admin/security), in English: the reference that ru and ka are typed
 * against. ENCRYPTION_KEYS stays as is: it is the setting's name.
 */

export const adminSecurityEn = {
  nav: "Encryption keys",
  title: "Encryption keys",
  description: "The keys that seal channel and calendar tokens, and moving every stored token to the newest key.",
  ring: {
    title: "Key ring",
    keyCount: "Keys in the ring",
    single: "One key seals and opens everything. To change it, put a new key first in ENCRYPTION_KEYS, deploy, then re-encrypt here.",
    several: {
      one: "The first key seals everything new; {count} older key only opens what it sealed. Re-encrypt, then remove it as the runbook says.",
      other: "The first key seals everything new; {count} older keys only open what they sealed. Re-encrypt, then remove them as the runbook says.",
    },
  },
  run: {
    title: "Re-encryption",
    description: "Every channel and calendar token is sealed again with the newest key, and Telegram webhooks are registered again with its secret.",
    start: "Re-encrypt stored tokens",
    confirmTitle: "Re-encrypt every stored token?",
    confirmBody:
      "The background worker seals each channel and calendar token again with the newest key and registers Telegram webhooks again. Customers notice nothing. The run is written to the audit log.",
    confirm: "Re-encrypt",
    starting: "Starting…",
    started: "Re-encryption queued",
    alreadyRunning: "A re-encryption is already running.",
    none: "No re-encryption yet",
    noneDescription: "Run one after a new key was put first in ENCRYPTION_KEYS. With one key it only checks that every token opens.",
    status: {
      queued: "Queued",
      running: "Running",
      done: "Done",
      failed: "Failed",
    },
    facts: {
      requested: "Requested",
      started: "Started",
      finished: "Finished",
      keys: "Keys in the ring then",
      total: "Tokens checked",
      current: "Already on the newest key",
      rotated: "Sealed again",
      unreadable: "Cannot be opened",
      webhooksRenewed: "Telegram webhooks registered again",
      webhooksFailed: "Telegram webhooks not registered",
    },
    verdict: {
      working: "The worker is re-encrypting. This page updates by itself.",
      clean: "Every stored token is sealed with the newest key. Older keys can go once the notification links and call recordings they sealed have expired (see the runbook).",
      cleanSingle: "Every stored token opens with the only key of the ring.",
      unreadable: {
        one: "{count} token cannot be opened with any key: its owner must reconnect that channel.",
        other: "{count} tokens cannot be opened with any key: their owners must reconnect those channels.",
      },
      webhooks: {
        one: "{count} Telegram webhook could not be registered again: re-encrypt again later.",
        other: "{count} Telegram webhooks could not be registered again: re-encrypt again later.",
      },
      failed: "The run stopped: {error}. Start it again; tokens it already moved stay moved.",
      keysChanged: "The key ring changed after this run ({then} keys then, {now} now): re-encrypt again.",
    },
  },
} as const;
