/** `privacyNotice.*`: the platform's default privacy notice for a business's chat, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { privacyNoticeEn } from "./privacyNotice.en";

export const privacyNoticeIt: Translation<typeof privacyNoticeEn> = {
  title: "Informativa sulla privacy",
  subtitle: "Come {business} tratta ciò che Lei scrive nella chat",
  whoTitle: "Chi risponde",
  who: "{business} risponde ai messaggi con un assistente AI, sul proprio sito web, su questa pagina e nelle app di messaggistica. Assistant Workshop fornisce l'assistente e tratta i Suoi messaggi per conto di {business}, che decide come vengono utilizzati.",
  whatTitle: "Cosa viene conservato",
  whatMessages: "Ciò che scrive nella chat e le risposte dell'assistente.",
  whatContacts: "Il Suo nome, numero di telefono o indirizzo e-mail, se li fornisce (ad esempio per una prenotazione o per essere richiamato).",
  whatBrowser: "Una chiave casuale nella memoria del Suo browser, così la chat riprende da dove l'ha lasciata. La chat non imposta cookie.",
  whatTechnical: "Dati tecnici come il Suo indirizzo IP, conservati per poco tempo per proteggere la chat dagli abusi.",
  whyTitle: "Perché",
  why: "Per rispondere alle Sue domande, ricevere prenotazioni e richieste e passare la conversazione al personale di {business} quando chiede di parlare con una persona o quando l'assistente non può aiutarLa.",
  sharedTitle: "Chi lo vede",
  shared: "Il personale di {business}. Per scrivere le risposte, il testo della conversazione viene elaborato dal fornitore del modello AI su cui funziona l'assistente, esclusivamente per questo scopo.",
  keptTitle: "Per quanto tempo",
  kept:
    "{business} conserva le conversazioni per {conversations} dall'ultimo messaggio, dopodiché vengono cancellate automaticamente, e i registri delle elaborazioni AI dell'assistente per {modelRecords}. Può chiedere in qualsiasi momento che i Suoi dati vengano cancellati.",
  callsTitle: "Chiamate",
  callsRecorded: "Quando chiama {business}, risponde il suo assistente AI. La chiamata viene registrata e trascritta; il personale di {business} può ascoltare la registrazione e leggere la trascrizione.",
  callsNotice: "All'inizio della chiamata l'assistente avvisa che la chiamata viene registrata.",
  callsConsent: "All'inizio della chiamata l'assistente avvisa che la chiamata viene registrata e che Lei può rifiutare la registrazione.",
  callsDecline: "Può dire in qualsiasi momento che non desidera che la chiamata venga registrata. La chiamata prosegue; al termine l'audio viene cancellato e si conserva solo una trascrizione scritta, senza numeri di telefono, indirizzi e-mail, numeri di carta o di conto.",
  callsKept: "{business} conserva le registrazioni e le trascrizioni delle chiamate per {recordings}, dopodiché vengono cancellate automaticamente.",
  rightsTitle: "Le Sue scelte",
  rights: "Può chiedere a {business} quali dati conserva su di Lei e chiedere di correggerli o cancellarli: scriva nella chat o contatti direttamente l'attività. L'assistente può sbagliare, quindi verifichi i dettagli importanti (prezzi, orari) con l'attività.",
  platformNote: "Questa è l'informativa predefinita della piattaforma Assistant Workshop. {business} può pubblicarne una propria.",
  backToChat: "Torna alla chat",
};
