/** `updates.*` in Italian: owner checks in an update, drafts and the test chat target (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { updatesEn } from "./updates.en";

export const updatesIt: Translation<typeof updatesEn> = {
  expectation: {
    must_mention: "la risposta deve menzionare “{text}”",
    must_not_mention: "la risposta non deve menzionare “{text}”",
    must_hand_off: "la risposta deve passare il cliente a una persona",
    must_create_lead: "la risposta deve registrare una richiesta",
  },
  failed: {
    one: "La tua verifica non è stata superata: “{question}” — {expectation}",
    many: {
      one: "{count} delle tue verifiche non è stata superata",
      other: "{count} delle tue verifiche non sono state superate",
    },
    rest: "Tutto il resto è stato superato. I clienti continuano a ricevere le risposte precedenti finché la verifica non viene superata.",
    result: "La tua verifica non è stata superata",
    openCheck: "Apri la verifica",
    fixAnswer: "Correggi la risposta",
    answered: "L’assistente ha risposto",
    applyAfterFix: "Applica le modifiche",
  },
  pending: {
    checksTitle: "Le tue verifiche",
    checksHint: "L’aggiornamento pone prima queste domande. Se una non viene superata, i clienti continuano a ricevere le risposte precedenti.",
    added: "Nuova verifica: “{question}”",
    changed: "Verifica modificata: “{question}”",
    draftsTitle: "Bozze",
    draftsHint: "Create a mano e mai arrivate ai clienti. Se ne scarti una, le tue modifiche restano.",
    draft: "Bozza del {date}",
    open: "Apri",
    discard: "Scarta",
    discardLabel: "Scarta la bozza del {date}",
    discardTitle: "Scartare questa bozza?",
    discardDescription: "I clienti non l’hanno mai ricevuta. Le tue modifiche restano: il prossimo “Applica le modifiche” partirà da lì.",
    discarded: "Bozza scartata",
    onlyDrafts: "Tutto ciò che hai modificato arriva ai clienti. È rimasta una bozza:",
  },
  checkNow: {
    savedTitle: "Verifica salvata",
    action: "Verifica ora",
    actionLabel: "Verifica ora: “{question}”",
    checking: "Verifica in corso…",
    hint: "Una conversazione di prova con ciò che ricevono ora i clienti.",
    passed: "Superata con ciò che ricevono ora i clienti.",
    failed: "Non superata con ciò che ricevono ora i clienti.",
    errored: "Impossibile completare la verifica. Riprova tra un minuto.",
    notLive: "Ai clienti non arriva ancora nulla: la verifica verrà eseguita al primo “Applica le modifiche”.",
    limited: "Hai fatto molte verifiche in quest’ora. Riprova più tardi.",
    checkedAt: "Verificata il {date}",
  },
  language: {
    auto: "La lingua della domanda",
  },
  chat: {
    target: "Parla con",
    live: "Ciò che ricevono ora i clienti",
    changes: "Con le tue modifiche",
    history: "Dalla Cronologia: aggiornamento {number}",
    noteLive: "Stai parlando con ciò che ricevono ora i clienti. Le conversazioni di prova non arrivano a clienti, personale o fatturazione.",
    noteChanges: "Stai parlando con l’assistente con le tue ultime modifiche, prima che arrivino ai clienti. Le conversazioni di prova non arrivano a clienti, personale o fatturazione.",
    noteHistory: "Stai parlando con un aggiornamento dalla Cronologia. Le conversazioni di prova non arrivano a clienti, personale o fatturazione.",
  },
  publishGate: {
    adminOnly: "Solo per gli amministratori della piattaforma",
  },
};
