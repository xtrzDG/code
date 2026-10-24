/** `adminTeam.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminTeamEn } from "./adminTeam.en";

export const adminTeamDe: Translation<typeof adminTeamEn> = {
  nav: "Team",
  title: "Admin-Team",
  description: "Wer die Admin-Seiten öffnen darf und was jede Rolle darf. Jede Änderung wird im Protokoll festgehalten.",
  roles: {
    super: "Super-Admin",
    support_readonly: "Support (nur lesen)",
    billing: "Abrechnung",
  },
  roleHints: {
    super: "Alles: Kunden, Betrieb, Kennzahlen, das Team; Änderungen im Dashboard eines Kunden, wenn der Inhaber es erlaubt.",
    support_readonly: "Kunden und der Zustand der Plattform; öffnet das Dashboard eines Kunden für eine Stunde, nur lesend.",
    billing: "Kunden, ihr Konto (Testphase, Rabatte, Guthaben, manuelle Zahlungen, Tarif), Notizen und die Wachstumskennzahlen; öffnet nie das Dashboard eines Kunden.",
  },
  you: "Sie",
  notSignedIn: "Hat sich noch nicht angemeldet",
  addedBy: "Hinzugefügt von {name} {date}",
  addedOn: "Auf der Team-Seite hinzugefügt {date}",
  bootstrapped: "Aus den PLATFORM_ADMIN_*-Listen {date}",
  role: "Rolle",
  roleFor: "Rolle von {name}",
  changed: "Rolle geändert",
  remove: "Entfernen",
  removeLabel: "{name} aus dem Team entfernen",
  removeTitle: "{name} aus dem Admin-Team entfernen?",
  removeDescription: "Bei der nächsten Anfrage verliert die Person die Admin-Seiten.",
  removed: "Aus dem Team entfernt",
  add: "Person hinzufügen",
  addTitle: "Person zum Admin-Team hinzufügen",
  addDescription:
    "Die Person bekommt die Admin-Seiten bei der nächsten Anmeldung mit dieser Telefonnummer oder E-Mail und muss eine Authenticator-App einrichten.",
  by: "Meldet sich an mit",
  byPhone: "Telefonnummer",
  byEmail: "E-Mail",
  phone: "Telefonnummer",
  email: "E-Mail",
  added: "Zum Team hinzugefügt",
  lastSuper: "Das Team braucht mindestens einen Super-Admin: Geben Sie die Rolle zuerst jemand anderem.",
};
