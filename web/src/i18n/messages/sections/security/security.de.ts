/** `security.*` in German: Account → Security (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { securityEn } from "./security.en";

export const securityDe: Translation<typeof securityEn> = {
  title: "Sicherheit",
  description: "Wie Sie sich beim Dashboard anmelden.",
  menu: "Sicherheit",
  back: "Zu meinen Unternehmen",
  required: {
    business:
      "Dieses Unternehmen verlangt von allen im Team die Anmeldung mit einer Authenticator-App. Richten Sie unten eine ein und fahren Sie dann fort.",
    admin:
      "Die Admin-Seiten verlangen eine Anmeldung mit einer Authenticator-App. Richten Sie unten eine ein oder bestätigen Sie damit, und fahren Sie dann fort.",
    continue: "Weiter",
  },
  app: {
    title: "Authenticator-App",
    description:
      "Nach dem Anmeldecode fragt das Dashboard auch nach einem Code aus einer App auf Ihrem Telefon. Wer Ihren Anmeldecode bekommt, kommt trotzdem nicht hinein.",
    on: "An",
    off: "Aus",
    pending: "Einrichtung nicht abgeschlossen",
    since: "Eingeschaltet {date}",
    lastUsed: "Letzter Code {date}",
    setUp: "Einrichten",
    finishSetup: "Einrichtung abschließen",
    remove: "Ausschalten",
    removeTitle: "Authenticator-App ausschalten?",
    removeDescription: "Die Anmeldung fragt dann wieder nur nach dem Anmeldecode, und Ihre Wiederherstellungscodes funktionieren nicht mehr.",
    removeAdmin: "Als Plattform-Admin werden Sie bei der nächsten Anmeldung aufgefordert, sie erneut einzurichten.",
    removed: "Die Authenticator-App ist aus",
    adminRequired: "Plattform-Admins melden sich immer mit einer Authenticator-App an.",
    turnedOn: "Die Authenticator-App ist an",
  },
  codes: {
    title: "Wiederherstellungscodes",
    description: "Für ein verlorenes Telefon: Jeder Code ersetzt einmal den Code der App.",
    left: {
      one: "{count} unbenutzter Code übrig",
      other: "{count} unbenutzte Codes übrig",
    },
    none: "Keine unbenutzten Codes mehr. Holen Sie sich neue.",
    renew: "Neue Codes holen",
    renewTitle: "Neue Wiederherstellungscodes holen?",
    renewDescription: "Ihre aktuellen Codes funktionieren sofort nicht mehr.",
    renewing: "Wird vorbereitet…",
  },
  session: {
    title: "Diese Sitzung",
    twoFactor: "Angemeldet mit Anmeldecode und Authenticator-App.",
    oneFactor: "Nur mit einem Anmeldecode angemeldet.",
    upgrade: "Mit der App bestätigen",
    upgraded: "Diese Sitzung gilt jetzt als mit der App angemeldet",
  },
  team: {
    title: "Zwei-Faktor-Anmeldung für das Team",
    description: "Alle, die dieses Unternehmen öffnen, müssen sich zusätzlich zum Anmeldecode mit einer Authenticator-App anmelden.",
    toggle: "Authenticator-App verlangen",
    on: "Für alle Pflicht",
    off: "Keine Pflicht",
    without: {
      one: "{count} Person hat noch keine Authenticator-App: Sie kann das Unternehmen erst öffnen, wenn sie unter Konto → Sicherheit eine eingerichtet hat.",
      other:
        "{count} Personen haben noch keine Authenticator-App: Sie können das Unternehmen erst öffnen, wenn sie unter Konto → Sicherheit eine eingerichtet haben.",
    },
    everyone: "Alle haben eine Authenticator-App.",
    ownFirst: "Melden Sie sich zuerst mit Ihrer eigenen Authenticator-App an: Richten Sie sie unter Konto → Sicherheit ein oder bestätigen Sie damit.",
    openSecurity: "Sicherheit öffnen",
    ownerOnly: "Nur ein Inhaber kann das ändern.",
    saved: "Gespeichert",
  },
};
