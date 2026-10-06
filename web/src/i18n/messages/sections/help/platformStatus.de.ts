/** `platformStatus.*` in German: the status page (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { platformStatusEn } from "./platformStatus.en";

export const platformStatusDe: Translation<typeof platformStatusEn> = {
  title: "Plattformstatus",
  description: "Ob Kunden-Chats, Kanäle, Anrufe und das Dashboard gerade funktionieren und wie die letzten 90 Tage verliefen.",
  overall: {
    operational: "Alles funktioniert",
    maintenance: "Geplante Wartung läuft",
    degraded: "Einige Teile sind langsamer als üblich",
    outage: "Einige Teile funktionieren gerade nicht",
    no_data: "Noch nichts gemessen",
  },
  levels: {
    operational: "Funktioniert",
    maintenance: "Wartung",
    degraded: "Langsam",
    outage: "Ausgefallen",
    no_data: "Keine Daten",
  },
  components: {
    chat: "Website-Chat und Chat-Seite",
    meta: "WhatsApp, Instagram und Messenger",
    telegram: "Telegram",
    voice: "Anrufe",
    cabinet: "Dashboard und Anmeldung",
  },
  checkedAt: "Geprüft {time}",
  monitoringDelayed: {
    title: "Die eigenen Prüfungen der Plattform sind im Verzug",
    minutesAgo: {
      one: "Die letzte Prüfung war vor {count} Minute.",
      other: "Die letzte Prüfung war vor {count} Minuten.",
    },
    at: "Letzte Prüfung: {time}",
    body: "Bis die Prüfungen aufgeholt haben, kann niemand für die Stufen unten bürgen, daher werden die Chats als langsamer angezeigt.",
  },
  componentsTitle: "Teile der Plattform",
  historyLabel: "{component}: die letzten 90 Tage",
  historyStart: "Vor 90 Tagen",
  historyEnd: "Heute",
  uptime: {
    one: "{share} störungsfrei an {count} Tag",
    other: "{share} störungsfrei über {count} Tage",
  },
  observingSince: "Beobachtet seit {date}",
  noHistory: "Noch keine Tage gemessen",
  day: "{day}: {level}",
  announcementLevels: {
    info: "Hinweis",
    maintenance: "Wartung",
    degraded: "Verlangsamt",
    outage: "Ausfall",
  },
  activeTitle: "Jetzt",
  scheduled: "Geplant",
  starts: "Beginnt {time}",
  since: "Seit {time}",
  expectedEnd: "Voraussichtliches Ende {time}",
  resolved: "Behoben {time}",
  updated: "Aktualisiert {time}",
  affects: "Betrifft: {components}",
  pastTitle: "Vergangene Störungen",
  pastEmpty: "Keine Störungen in den letzten 90 Tagen.",
  unreachable: {
    title: "Der Status kann nicht geladen werden",
    body: "Diese Seite erreicht die Plattform gerade nicht. Wenn auch die Chats nicht funktionieren, schreiben Sie dem Support: Das Team weiß bereits Bescheid.",
  },
  selfMeasured: "Die Plattform prüft sich alle fünf Minuten selbst; das Team ergänzt, was es weiß.",
  openCabinet: "Dashboard öffnen",
  banner: {
    region: "Meldung der Plattform",
    details: "Details",
    dismiss: "Ausblenden",
  },
};
