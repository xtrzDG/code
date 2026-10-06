/** `adminStatus.*` in German: the admin's status announcements (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminStatusEn } from "./adminStatus.en";

export const adminStatusDe: Translation<typeof adminStatusEn> = {
  title: "Meldungen auf der Statusseite",
  description: "Was die öffentliche Statusseite und das Banner über jedem Dashboard sagen. Jede Änderung steht im Protokoll.",
  create: "Neue Meldung",
  openPage: "Statusseite öffnen",
  none: "Noch keine Meldungen",
  noneDescription: "Schreiben Sie eine, wenn ein Teil der Plattform ausfällt, langsam ist oder gewartet wird.",
  status: {
    active: "Aktiv",
    resolved: "Behoben",
  },
  edit: "Aktualisieren",
  resolve: "Als behoben markieren",
  resolveTitle: "Diese Meldung als behoben markieren?",
  resolveBody: "Das Banner verschwindet aus allen Dashboards, und die Statusseite führt sie unter vergangenen Störungen.",
  published: "Meldung veröffentlicht",
  saved: "Meldung aktualisiert",
  resolvedToast: "Meldung als behoben markiert",
  form: {
    createTitle: "Neue Meldung",
    editTitle: "Meldung aktualisieren",
    description: "Inhaber sehen sie sofort auf der Statusseite und über ihrem Dashboard.",
    level: "Stufe",
    levelHints: {
      info: "Ein Hinweis: Kein Teil der Plattform wird als betroffen markiert.",
      maintenance: "Geplante Arbeiten: Geben Sie eine Startzeit an, um sie vorab anzukündigen.",
      degraded: "Funktioniert, aber langsamer oder mit einigen Fehlern.",
      outage: "Funktioniert nicht. Inhaber können dieses Banner nicht ausblenden.",
    },
    components: "Betroffene Teile",
    componentsHint: "Solange sie aktiv ist, zeigt jeder gewählte Teil diese Stufe auf der Statusseite.",
    textLabel: "Text auf {language}",
    textHint: "Englisch ist Pflicht. Inhaber, deren Sprache leer bleibt, lesen den englischen Text.",
    startsAt: "Beginn",
    startsAtHint: "Leer: jetzt. Eine spätere Zeit kündigt geplante Arbeiten an.",
    expectedEnd: "Voraussichtliches Ende",
    timeZone: "Die Zeiten gelten in der Zeitzone dieses Geräts.",
    publish: "Veröffentlichen",
    save: "Speichern",
    saving: "Wird gespeichert…",
    errors: {
      textRequired: "Schreiben Sie den englischen Text: mindestens 3 Zeichen.",
      textShort: "Mindestens 3 Zeichen, oder leer lassen.",
      componentsRequired: "Wählen Sie mindestens einen betroffenen Teil.",
      time: "Geben Sie ein Datum und eine Uhrzeit ein.",
      endBeforeStart: "Das Ende muss nach dem Beginn und in der Zukunft liegen.",
      startTooLate: "Der Beginn darf höchstens 60 Tage in der Zukunft liegen.",
    },
  },
};
