/** `assistantComparison.*` in Italian (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { assistantComparisonEn } from "./assistantComparison.en";

export const assistantComparisonIt: Translation<typeof assistantComparisonEn> = {
  comparison: {
    title: "Confronto con l'aggiornamento online {number}",
    description: "Si confrontano solo gli scenari eseguiti da entrambi gli aggiornamenti.",
    shared: "Scenari confrontati: {count}",
    averageScore: "Punteggio medio",
    averageWas: "Aggiornamento online: {score}",
    newFailures: "Nuovi problemi",
    fixed: "Risolti",
    newFailuresHint: "Questi erano superati con l'aggiornamento online e ora non lo sono più.",
    fixedHint: "Questi non erano superati con l'aggiornamento online e ora lo sono.",
    scoreDrops: "Punteggi scesi",
    scoreRises: "Punteggi saliti",
    criteria: "Per criterio",
    scenario: "{name} · {language}",
    phoneScenario: "{name} · {channel} · {language}",
    scoreMove: "{from} → {to}",
    outcomeMove: "{from} prima, {to} ora",
    noChanges: "Nulla è cambiato rispetto all'aggiornamento online: nessun nuovo problema e nessun punteggio variato di mezzo punto o più.",
    noShared: "Questa esecuzione e quella dell'aggiornamento online non hanno ancora scenari in comune.",
    plays: { one: "{passed} esecuzione su {played} superata", other: "{passed} esecuzioni su {played} superate" },
    playsHint: "Gli scenari importanti vengono eseguiti più volte; ogni esecuzione deve essere superata.",
  },
};
