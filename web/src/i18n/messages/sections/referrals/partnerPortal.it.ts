/** `partnerPortal.*` in Italian (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { partnerPortalEn } from "./partnerPortal.en";

export const partnerPortalIt: Translation<typeof partnerPortalEn> = {
  title: "Area partner",
  description: "I tuoi link, le attività che hanno portato e quanto hai guadagnato.",
  rate: "La tua commissione: {rate} di ogni fattura pagata da quelle attività, al netto delle imposte.",
  paused: "La tua collaborazione è in pausa: i nuovi pagamenti non generano commissioni finché il team della piattaforma non la riattiva.",
  legal: "Il tuo contratto e le modalità di pagamento si concordano con il team della piattaforma.",
  links: {
    title: "I tuoi link",
    description: "Crea un link per ogni posto in cui lo condividi: il tag mostra da dove arrivano le iscrizioni.",
    none: "Non hai ancora codici: li aggiunge il team della piattaforma.",
    source: "Dove lo condividi",
    sourcePlaceholder: "Instagram",
    sourceHint: "Facoltativo. Lettere latine, cifre, punti, trattini e trattini bassi.",
    sourceInvalid: "Usa solo lettere latine, cifre, punti, trattini e trattini bassi.",
    code: "Codice",
    qrLabel: "Codice QR del link con {code}",
    showQr: "Codice QR",
    hideQr: "Nascondi il codice QR",
  },
  totals: {
    title: "Commissioni",
    businesses: "Attività portate",
    paying: "Hanno già pagato",
    accrued: "Da pagare",
    paid: "Pagato",
  },
  businesses: {
    title: "Le attività che hai portato",
    empty: "Ancora nessuna attività. Condividi il tuo link per portare la prima.",
    signedUp: "Iscrizione",
    firstPaid: "Primo pagamento",
    notYet: "Non ancora",
    unnamed: "Attività",
  },
  commissions: {
    title: "Commissioni per fattura",
    empty: "Ancora nessuna commissione: compaiono quando paga un’attività che hai portato.",
    base: "Fattura al netto delle imposte",
    status: "Stato",
    statuses: {
      accrued: "Da pagare",
      paid: "Pagata",
    },
  },
  showMore: "Mostra altro",
  loading: "Caricamento…",
};
