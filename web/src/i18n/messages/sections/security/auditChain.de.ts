/** `auditChain.*` auf Deutsch: die Prüfung des Aktivitätsprotokolls auf Änderungen. */

import type { Translation } from "../../../translate";
import type { auditChainEn } from "./auditChain.en";

export const auditChainDe: Translation<typeof auditChainEn> = {
  title: "Manipulationsprüfung",
  status: {
    unchecked: "Noch nicht geprüft",
    unsealed: "Noch keine versiegelten Einträge",
    intact: "Unverändert",
    broken: "Verändert",
  },
  verdict: {
    unchecked: "Jeder neue Eintrag wird mit dem vorherigen versiegelt. Die erste tägliche Prüfung läuft innerhalb eines Tages.",
    unsealed: "Einträge werden ab dem ersten versiegelt, der nach dem Start der Versiegelung geschrieben wurde, und dieses Protokoll hat noch keinen. Ältere Einträge sind nicht versiegelt.",
    intact: "Jeder seit dem Start der Versiegelung geschriebene Eintrag ist mit dem vorherigen versiegelt, und die tägliche Prüfung fand alle so vor, wie sie geschrieben wurden. Ältere Einträge sind nicht versiegelt.",
    broken: "Die tägliche Prüfung fand ein Problem bei Eintrag {position}: {problem}. Das Plattform-Team wurde alarmiert.",
  },
  problems: {
    hash_mismatch: "er wurde geändert",
    link_broken: "ein Eintrag davor wurde geändert, entfernt oder hinzugefügt",
    position_gap: "er wurde entfernt",
    head_lost: "die neuesten Einträge wurden abgeschnitten oder neu geschrieben",
    checkpoint_mismatch: "nach Ablauf der Aufbewahrungsfrist entfernte Einträge sind wieder da",
  },
  checkedAt: "Geprüft {when}",
  verifiedThrough: "Geprüft bis Eintrag {position}",
  purgedThrough: "Einträge bis {position} wurden nach Ablauf der Aufbewahrungsfrist entfernt",
};
