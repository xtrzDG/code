/** `dataExports.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { dataExportsEn } from "./dataExports.en";

export const dataExportsDe: Translation<typeof dataExportsEn> = {
  csv: {
    button: "CSV exportieren",
    bookingsHint: "Die Buchungen, die die Filter zeigen, als Tabelle (CSV)",
    inboxLabel: "Diese Gespräche als CSV exportieren",
    inboxHint: "Die gewählte Ansicht und der Kanal, mit allen Nachrichten",
    tableLabel: "{table} als CSV herunterladen",
    saved: "Die Datei ist heruntergeladen",
    tables: {
      bookings: "Buchungen",
      leads: "Anfragen",
      contacts: "Kunden",
      conversations: "Gespräche",
      audit_log: "Protokoll",
    },
  },
  full: {
    title: "Ihre Daten exportieren",
    description:
      "Alles, was für Ihr Unternehmen gespeichert ist, in einer ZIP-Datei: Kunden, Gespräche mit allen Nachrichten, Anrufe, Buchungen, Anfragen, Leistungen, verpasste Anrufe, Feedback und das Protokoll, als JSON und als Tabellen (CSV).",
    start: "Vollständigen Export vorbereiten",
    started: "Der Export wird vorbereitet",
    working: "Das Archiv wird vorbereitet. Das dauert einige Minuten; Sie können die Seite verlassen und wiederkommen.",
    history: "Letzte Exporte",
    empty: "Noch keine Exporte. Bereiten Sie einen vor, wann immer Sie eine Kopie Ihrer Daten brauchen.",
    requested: "Angefordert {date}",
    readyUntil: "Aufbewahrt bis {date}",
    download: "ZIP herunterladen",
    downloadLabel: "Den am {date} angeforderten Export herunterladen",
    downloadStarted: "Der Download hat begonnen",
    downloadsLeft: { one: "Noch {count} von {total} Downloads", other: "Noch {count} von {total} Downloads" },
    usedUp: "Dieser Export wurde dreimal heruntergeladen. Bereiten Sie für eine weitere Kopie einen neuen vor.",
    gone: "Dieser Export wird nicht mehr aufbewahrt. Bereiten Sie einen neuen vor.",
    sizeKb: "{size} KB",
    sizeMb: "{size} MB",
    records: { one: "{count} Datensatz", other: "{count} Datensätze" },
    failed: "Das Archiv konnte nicht erstellt werden. Bereiten Sie es erneut vor; wenn es wieder fehlschlägt, schreiben Sie dem Support.",
    status: {
      queued: "Wartet",
      running: "Wird vorbereitet",
      ready: "Bereit",
      expired: "Gelöscht",
      failed: "Fehlgeschlagen",
    },
    linkNote:
      "Jeder Download erzeugt einen einmaligen Link, der 10 Minuten und nur für Sie funktioniert. Ein Export kann innerhalb eines Tages dreimal heruntergeladen werden, und jeder Inhaber erfährt, wer ihn von welchem Gerät und welcher Adresse heruntergeladen hat.",
    erasedNote: "Kunden, deren Daten gelöscht wurden, sind in keinem Export enthalten.",
  },
  tables: {
    title: "Tabellen als Tabellenblätter",
    description: "Eine Tabelle als CSV, für Excel, Numbers oder Google Sheets. Buchungen und der Posteingang lassen sich auch mit den dort gewählten Filtern exportieren.",
  },
};
