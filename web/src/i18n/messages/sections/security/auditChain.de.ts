/** `auditChain.*` auf Deutsch: die Prüfung des Aktivitätsprotokolls auf Änderungen. */

import type { Translation } from "../../../translate";
import type { auditChainEn } from "./auditChain.en";

export const auditChainDe: Translation<typeof auditChainEn> = {
  title: "Manipulationsprüfung",
  status: {
    unchecked: "Noch nicht geprüft",
    intact: "Unverändert",
    broken: "Verändert",
  },
  verdict: {
    unchecked: "Jeder Eintrag ist mit dem vorherigen versiegelt. Die erste tägliche Prüfung läuft innerhalb eines Tages.",
    intact: "Jeder Eintrag ist mit dem vorherigen versiegelt, und die tägliche Prüfung fand alle Einträge so vor, wie sie geschrieben wurden.",
    broken: "Die tägliche Prüfung fand Eintrag {position} nicht so vor, wie er geschrieben wurde: {problem}. Das Plattform-Team wurde alarmiert.",
  },
  problems: {
    hash_mismatch: "er wurde geändert",
    link_broken: "ein Eintrag davor wurde geändert, entfernt oder hinzugefügt",
    position_gap: "ein Eintrag davor wurde entfernt",
    head_lost: "die neuesten Einträge wurden abgeschnitten oder neu geschrieben",
    checkpoint_mismatch: "nach Ablauf der Aufbewahrungsfrist entfernte Einträge sind wieder da",
  },
  checkedAt: "Geprüft {when}",
  verifiedThrough: "Geprüft bis Eintrag {position}",
  purgedThrough: "Einträge bis {position} wurden nach Ablauf der Aufbewahrungsfrist entfernt",
};
