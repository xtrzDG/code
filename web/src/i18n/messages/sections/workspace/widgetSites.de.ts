/** `widgetSites.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { widgetSitesEn } from "./widgetSites.en";

export const widgetSitesDe: Translation<typeof widgetSitesEn> = {
  title: "Websites, die den Chat zeigen dürfen",
  description:
    "Der Code des Chats funktioniert auf jeder Website, in die er eingefügt wird. Tragen Sie Ihre eigenen Websites ein, dann funktioniert der Chat nur dort, und niemand kann Ihren Assistenten und Ihren Tarif mit einer Kopie des Codes betreiben.",
  anySite: "Jede Website",
  sites: { one: "{count} Website", other: "{count} Websites" },
  listLabel: "Erlaubte Websites",
  empty: "Noch keine Liste: Der Chat funktioniert auf jeder Website.",
  addLabel: "Adresse der Website",
  addHint: "Wie in der Adressleiste des Browsers. Die www.-Adresse und http oder https zählen als dieselbe Website.",
  placeholder: "https://cafe-batumi.ge",
  add: "Hinzufügen",
  remove: "{site} entfernen",
  invalid: "Das ist keine Website-Adresse. Geben Sie sie wie in der Adressleiste ein, zum Beispiel cafe-batumi.ge.",
  duplicate: "Diese Website steht bereits auf der Liste.",
  full: { one: "Die Liste fasst bis zu {count} Website.", other: "Die Liste fasst bis zu {count} Websites." },
  alwaysAllowed: "Ihre Chat-Seite und die Vorschau in diesem Dashboard funktionieren immer.",
  ownerOnly: "Nur ein Inhaber kann diese Liste ändern.",
  save: "Liste speichern",
  saving: "Wird gespeichert…",
  unsaved: "Nicht gespeichert",
  savedToast: "Liste der Websites gespeichert",
  clearedToast: "Der Chat funktioniert wieder auf jeder Website",
};
