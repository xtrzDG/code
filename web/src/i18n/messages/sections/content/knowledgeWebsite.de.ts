/** `knowledgeWebsite.*` in German: importing from the website (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { knowledgeWebsiteEn } from "./knowledgeWebsite.en";

export const knowledgeWebsiteDe: Translation<typeof knowledgeWebsiteEn> = {
  website: {
    tabsLabel: "Was importiert wird",
    tabMenu: "Speisekarte oder Preisliste",
    tabWebsite: "Von Ihrer Website",
    title: "Von Ihrer Website importieren",
    description:
      "Geben Sie die Adresse Ihrer Website an. Wir lesen bis zu 15 ihrer Seiten — Speisekarte, Preise, Leistungen, Fragen und Öffnungszeiten — und zeigen Ihnen, was wir gefunden haben, bevor sich etwas ändert.",
    address: "Adresse der Website",
    addressHint: "Ihre eigene Website, zum Beispiel https://my-cafe.ge",
    start: "Meine Website lesen",
    starting: "Wird gestartet…",
    safety: "Nur öffentliche Seiten werden gelesen. Nichts erreicht Kunden, bevor Sie die Einträge geprüft und hinzugefügt haben.",
    progressLabel: "Ihre Website wird gelesen",
    queued: "Startet gleich…",
    opening: "{host} wird geöffnet…",
    reading: "Seite {current} von {total} wird gelesen",
    found: { one: "Bisher {count} Eintrag gefunden", other: "Bisher {count} Einträge gefunden" },
    leaveHint: "Sie können diese Seite verlassen: Der Import läuft weiter, und was er findet, wartet hier auf Sie.",
    doneTitle: { one: "{count} Eintrag auf Ihrer Website gefunden", other: "{count} Einträge auf Ihrer Website gefunden" },
    doneDescription: {
      one: "{count} Seite gelesen. Prüfen Sie die Einträge, bevor sie hinzugefügt werden.",
      other: "{count} Seiten gelesen. Prüfen Sie die Einträge, bevor sie hinzugefügt werden.",
    },
    review: "Gefundenes prüfen",
    waitingTitle: "Einträge von Ihrer Website warten auf Sie",
    waitingDescription: { one: "{count} Eintrag auf {host} gefunden.", other: "{count} Einträge auf {host} gefunden." },
    nothingTitle: "Nichts zum Importieren gefunden",
    nothingDescription:
      "Die Seiten hatten keine Speisekarte, Preise, Leistungen, Fragen oder Öffnungszeiten, die wir lesen konnten. Versuchen Sie eine andere Adresse oder fügen Sie die Einträge von Hand hinzu.",
    another: "Andere Adresse versuchen",
    sourcePage: "Von {page}",
    errors: {
      required: "Geben Sie die Adresse Ihrer Website ein",
      address: "Geben Sie eine Webadresse wie https://my-cafe.ge ein",
      failedTitle: "Die Website konnte nicht gelesen werden",
      notPublic: "Das ist keine öffentliche Website. Verwenden Sie die Adresse, die Kunden im Browser öffnen.",
      notHttp: "Verwenden Sie eine Webadresse, die mit http:// oder https:// beginnt.",
      port: "Adressen mit einem Port wie :8080 können nicht gelesen werden. Verwenden Sie die übliche Adresse Ihrer Website.",
      credentials: "Entfernen Sie Benutzername und Passwort aus der Adresse.",
      unknownHost: "Unter dieser Adresse wurde keine Website gefunden. Prüfen Sie die Schreibweise.",
      timeout: "Die Website hat zu lange gebraucht. Versuchen Sie es in ein paar Minuten erneut.",
      unreachable: "Die Website konnte nicht geöffnet werden. Prüfen Sie die Adresse und ob die Website online ist.",
      httpStatus: "Die Website hat mit Fehler {status} geantwortet. Prüfen Sie die Adresse.",
      unreadable: "Die Adresse hat sich geöffnet, aber nicht als lesbare Webseite (eine Datei oder zu groß). Versuchen Sie die Adresse Ihrer Startseite.",
      reader: "Der Lesedienst ist gerade nicht verfügbar. Versuchen Sie es später erneut.",
      interrupted: "Der Import ist vor dem Ende stehen geblieben. Starten Sie ihn erneut.",
      running: "Ihre Website wird bereits gelesen. Warten Sie, bis dieser Import fertig ist.",
      tooMany: "Ihre Website wurde in der letzten Stunde 10-mal importiert. Versuchen Sie es später erneut.",
    },
  },
};
