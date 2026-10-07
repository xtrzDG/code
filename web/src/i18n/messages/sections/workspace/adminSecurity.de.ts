/** `adminSecurity.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminSecurityEn } from "./adminSecurity.en";

export const adminSecurityDe: Translation<typeof adminSecurityEn> = {
  nav: "Schlüssel",
  title: "Verschlüsselungsschlüssel",
  description: "Die Schlüssel, die Kanal- und Kalender-Tokens versiegeln, und das Umziehen jedes gespeicherten Tokens auf den neuesten Schlüssel.",
  ring: {
    title: "Schlüsselbund",
    keyCount: "Schlüssel im Bund",
    single: "Ein Schlüssel versiegelt und öffnet alles. Um ihn zu wechseln, setzen Sie einen neuen Schlüssel an die erste Stelle in ENCRYPTION_KEYS, deployen und verschlüsseln dann hier neu.",
    several: {
      one: "Der erste Schlüssel versiegelt alles Neue; {count} älterer Schlüssel öffnet nur, was er versiegelt hat. Verschlüsseln Sie neu und entfernen Sie ihn dann wie im Runbook beschrieben.",
      other: "Der erste Schlüssel versiegelt alles Neue; {count} ältere Schlüssel öffnen nur, was sie versiegelt haben. Verschlüsseln Sie neu und entfernen Sie sie dann wie im Runbook beschrieben.",
    },
  },
  run: {
    title: "Neuverschlüsselung",
    description: "Jedes Kanal- und Kalender-Token wird mit dem neuesten Schlüssel neu versiegelt, und Telegram-Webhooks werden mit dessen Geheimnis neu registriert.",
    start: "Gespeicherte Tokens neu verschlüsseln",
    confirmTitle: "Jedes gespeicherte Token neu verschlüsseln?",
    confirmBody:
      "Der Hintergrund-Worker versiegelt jedes Kanal- und Kalender-Token mit dem neuesten Schlüssel neu und registriert die Telegram-Webhooks neu. Kunden merken nichts. Der Durchlauf wird im Protokoll festgehalten.",
    confirm: "Neu verschlüsseln",
    starting: "Wird gestartet…",
    started: "Neuverschlüsselung eingereiht",
    alreadyRunning: "Eine Neuverschlüsselung läuft bereits.",
    none: "Noch keine Neuverschlüsselung",
    noneDescription: "Führen Sie sie aus, nachdem ein neuer Schlüssel an die erste Stelle in ENCRYPTION_KEYS gesetzt wurde. Mit einem Schlüssel prüft sie nur, dass sich jedes Token öffnen lässt.",
    status: {
      queued: "Eingereiht",
      running: "Läuft",
      done: "Erledigt",
      failed: "Fehlgeschlagen",
    },
    facts: {
      requested: "Angefordert",
      started: "Begonnen",
      finished: "Beendet",
      keys: "Damals Schlüssel im Bund",
      total: "Geprüfte Tokens",
      current: "Bereits mit dem neuesten Schlüssel",
      rotated: "Neu versiegelt",
      unreadable: "Nicht zu öffnen",
      webhooksRenewed: "Telegram-Webhooks neu registriert",
      webhooksFailed: "Telegram-Webhooks nicht registriert",
    },
    verdict: {
      working: "Der Worker verschlüsselt neu. Diese Seite aktualisiert sich selbst.",
      clean: "Jedes gespeicherte Token ist mit dem neuesten Schlüssel versiegelt. Ältere Schlüssel können weg, sobald die von ihnen versiegelten Benachrichtigungslinks und Anrufaufnahmen abgelaufen sind (siehe Runbook).",
      cleanSingle: "Jedes gespeicherte Token öffnet sich mit dem einzigen Schlüssel des Bunds.",
      unreadable: {
        one: "{count} Token lässt sich mit keinem Schlüssel öffnen: Sein Inhaber muss diesen Kanal neu verbinden.",
        other: "{count} Tokens lassen sich mit keinem Schlüssel öffnen: Ihre Inhaber müssen diese Kanäle neu verbinden.",
      },
      webhooks: {
        one: "{count} Telegram-Webhook konnte nicht neu registriert werden: Verschlüsseln Sie später erneut.",
        other: "{count} Telegram-Webhooks konnten nicht neu registriert werden: Verschlüsseln Sie später erneut.",
      },
      failed: "Der Durchlauf ist stehen geblieben: {error}. Starten Sie ihn erneut; bereits umgezogene Tokens bleiben umgezogen.",
      keysChanged: {
        one: "Der Schlüsselbund hat sich nach diesem Durchlauf geändert (damals {then} Schlüssel, jetzt {now}): Verschlüsseln Sie erneut.",
        other: "Der Schlüsselbund hat sich nach diesem Durchlauf geändert (damals {then} Schlüssel, jetzt {now}): Verschlüsseln Sie erneut.",
      },
    },
  },
};
