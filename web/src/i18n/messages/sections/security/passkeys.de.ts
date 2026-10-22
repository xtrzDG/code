/** `passkeys.*` texts in German: passkeys in Account → Security, at sign-in and step-up. */

import type { Translation } from "../../../translate";
import type { passkeysEn } from "./passkeys.en";

export const passkeysDe: Translation<typeof passkeysEn> = {
  title: "Passkeys",
  description:
    "Bestätigen Sie mit Fingerabdruck, Gesichtserkennung oder Geräte-PIN statt mit einem Code. Ein Passkey funktioniert nur auf dieser Website und lässt sich daher nicht abfischen.",
  recommended:
    "Der sicherste zweite Faktor: Fügen Sie auf jedem Gerät, das Sie nutzen, einen Passkey hinzu.",
  unavailable:
    "Passkeys sind auf diesem Server noch nicht eingerichtet. Nutzen Sie die Authenticator-App unten.",
  unsupported:
    "Dieser Browser unterstützt keine Passkeys. Öffnen Sie das Dashboard in einem anderen Browser oder nutzen Sie die Authenticator-App.",
  empty: "Noch keine Passkeys.",
  add: "Passkey hinzufügen",
  adding: "Warte auf Ihr Gerät…",
  added: "Passkey hinzugefügt",
  addedOn: "Hinzugefügt {date}",
  lastUsed: "Zuletzt verwendet {date}",
  neverUsed: "Noch nicht verwendet",
  synced: "Auf Ihren Geräten synchronisiert",
  suspended:
    "Abgelehnt: Möglicherweise wird eine Kopie dieses Passkeys verwendet. Entfernen Sie ihn und fügen Sie ihn neu hinzu.",
  name: "Name",
  rename: "Umbenennen",
  renameLabel: "{name} umbenennen",
  renameTitle: "Passkey umbenennen",
  renameHint: "Zum Beispiel das Gerät oder der Passwortmanager, der ihn aufbewahrt.",
  renamed: "Passkey umbenannt",
  save: "Speichern",
  remove: "Entfernen",
  removeLabel: "{name} entfernen",
  removeTitle: "Diesen Passkey entfernen?",
  removeDescription:
    "Sie können sich damit nicht mehr anmelden. Entfernen Sie ihn auch vom Gerät.",
  removed: "Passkey entfernt",
  signIn: {
    use: "Mit Passkey anmelden",
    waiting: "Warte auf Ihren Passkey…",
    description: "Bestätigen Sie mit dem Passkey auf diesem Gerät oder Ihrem Telefon.",
    useCode: "Stattdessen einen Code verwenden",
    usePasskey: "Stattdessen einen Passkey verwenden",
  },
  enrollment: {
    description:
      "Admins melden sich mit einem zweiten Faktor an. Am sichersten ist ein Passkey: Fügen Sie jetzt einen hinzu oder richten Sie eine Authenticator-App ein.",
    add: "Passkey hinzufügen",
    useApp: "Stattdessen eine Authenticator-App einrichten",
  },
  stepUp: {
    use: "Mit Passkey bestätigen",
    description:
      "Bestätigen Sie mit dem Passkey auf diesem Gerät oder Ihrem Telefon. Es wird nichts gesendet.",
    orCode: "oder einen Code eingeben",
  },
  errors: {
    cancelled:
      "Die Passkey-Anfrage wurde abgebrochen oder ist abgelaufen. Versuchen Sie es erneut.",
    alreadyAdded: "Auf diesem Gerät ist bereits ein Passkey für Ihr Konto gespeichert.",
    wrongSite:
      "Passkeys funktionieren nur unter der gewohnten Adresse des Dashboards. Öffnen Sie es dort und versuchen Sie es erneut.",
    unsupported:
      "Dieser Browser unterstützt keine Passkeys. Versuchen Sie einen anderen Browser oder melden Sie sich mit einem Code an.",
    rejected: "Der Passkey konnte nicht bestätigt werden. Versuchen Sie es erneut.",
    suspended:
      "Dieser Passkey wurde abgelehnt: Möglicherweise wird eine Kopie verwendet. Melden Sie sich anders an und entfernen Sie ihn.",
    unavailable: "Passkeys sind hier nicht verfügbar. Melden Sie sich mit einem Code an.",
  },
};
