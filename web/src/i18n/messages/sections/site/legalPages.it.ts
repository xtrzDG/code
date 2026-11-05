/** `legalPages.*` texts of the public legal and contact pages, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { legalPagesEn } from "./legalPages.en";

export const legalPagesIt: Translation<typeof legalPagesEn> = {
  nav: {
    terms: "Termini di servizio",
    privacy: "Informativa sulla privacy",
    dpa: "Accordo sul trattamento dei dati",
    security: "Sicurezza",
    contact: "Contatti",
  },
  descriptions: {
    terms: "Le condizioni alle quali le attività usano la piattaforma di assistenti AI: il servizio, il pagamento, la prova gratuita, la responsabilità e la cessazione del contratto.",
    privacy: "Quali dati personali dei titolari e del loro team tratta la piattaforma, perché, per quanto tempo e come esercitare i tuoi diritti.",
    dpa: "L'accordo sul trattamento dei dati che ogni attività accetta prima di andare online: come vengono trattati i dati dei clienti per suo conto e da quali sub-responsabili.",
    security: "Come la piattaforma protegge i dati: crittografia, controllo degli accessi, backup, monitoraggio e come segnalare una vulnerabilità.",
    contact: "Chi fornisce la piattaforma di assistenti AI e come parlare con una persona: canali di assistenza e dati del gestore.",
  },
  footerLabel: "Note legali e contatti",
  draftTitle: "Bozza",
  draftText: "Questo testo non è ancora stato rivisto da un avvocato e i campi tra parentesi quadre sono ancora da compilare. Lo pubblichiamo perché tu possa leggere cosa offrirà il servizio; nella forma attuale non è ancora in vigore.",
  document: {
    upcoming: "Una nuova versione entra in vigore il {date}; è già pubblicata.",
    otherLanguage: "Questo testo non è ancora disponibile nella tua lingua; viene mostrato in {language}.",
  },
  unavailable: "Al momento non è stato possibile caricare il testo. Riprova più tardi.",
  dpaLead: "Ogni attività sulla piattaforma accetta questo accordo nel proprio pannello prima di andare online; descrive come vengono trattati i dati dei clienti per conto dell'attività.",
  related: "Altri documenti",
  contactTitle: "Contatti",
  contactLead: "Chi fornisce il servizio e come parlare con una persona.",
  operatorTitle: "Gestore",
  legalName: "Ragione sociale",
  address: "Indirizzo",
  taxId: "Codice fiscale o partita IVA",
  country: "Paese",
  email: "E-mail",
  operatorMissing: "L'indirizzo e i dati di registrazione del gestore saranno pubblicati qui prima che il servizio sia aperto ai clienti.",
  supportTitle: "Scrivici",
  supportWhatsApp: "WhatsApp",
  supportTelegram: "Telegram",
  supportEmail: "E-mail",
  supportMissing: "I contatti dell'assistenza compariranno qui prima che il servizio sia aperto ai clienti.",
  securityReportTitle: "Hai trovato una vulnerabilità?",
  securityReportText: "Segnalacela in privato; come farlo è spiegato nel nostro security.txt.",
  securityReportLink: "Apri le regole per i ricercatori di sicurezza",
};
