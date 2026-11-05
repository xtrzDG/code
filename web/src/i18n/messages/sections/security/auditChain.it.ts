/** `auditChain.*` texts of the audit log tamper check, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { auditChainEn } from "./auditChain.en";

export const auditChainIt: Translation<typeof auditChainEn> = {
  title: "Verifica anti-manomissione",
  status: {
    unchecked: "Non ancora verificato",
    unsealed: "Ancora nessuna voce sigillata",
    intact: "Integro",
    broken: "Modificato",
  },
  verdict: {
    unchecked: "Ogni nuova voce viene sigillata insieme a quella precedente. La prima verifica giornaliera avviene entro un giorno.",
    unsealed: "Le voci vengono sigillate a partire dalla prima scritta dopo l'avvio della sigillatura, e l'ultima verifica non ne ha ancora trovate. Le voci scritte prima non sono sigillate.",
    intact: "Ogni voce scritta dall'avvio della sigillatura è sigillata insieme a quella precedente, e la verifica giornaliera le ha trovate tutte esattamente come erano state scritte. Le voci scritte prima non sono sigillate.",
    broken: "La verifica giornaliera ha trovato un problema alla voce {position}: {problem}. Il team della piattaforma è stato avvisato.",
  },
  problems: {
    hash_mismatch: "è stata modificata",
    link_broken: "una voce precedente è stata modificata, rimossa o aggiunta",
    position_gap: "è stata rimossa",
    head_lost: "le voci più recenti sono state tagliate o riscritte",
    checkpoint_mismatch: "sono ricomparse voci rimosse dopo il periodo di conservazione",
  },
  checkedAt: "Verificato: {when}",
  verifiedThrough: "Verificato fino alla voce {position}",
  purgedThrough: "Le voci fino alla {position} sono state rimosse dopo il periodo di conservazione",
};
