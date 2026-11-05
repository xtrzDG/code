/** `dataExports.*` texts of the full data export and the CSV buttons, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { dataExportsEn } from "./dataExports.en";

export const dataExportsIt: Translation<typeof dataExportsEn> = {
  csv: {
    button: "Esporta CSV",
    bookingsHint: "Le prenotazioni mostrate dai filtri, come foglio di calcolo (CSV)",
    inboxLabel: "Esporta queste conversazioni in CSV",
    inboxHint: "La vista e il canale scelti, con tutti i messaggi",
    tableLabel: "Scarica {table} in CSV",
    saved: "Il file è stato scaricato",
    tables: {
      bookings: "Prenotazioni",
      leads: "Lead",
      contacts: "Clienti",
      conversations: "Conversazioni",
      audit_log: "Registro delle attività",
    },
  },
  full: {
    title: "Esporta i tuoi dati",
    description:
      "Tutto ciò che conserviamo per la tua attività in un unico file ZIP: clienti, conversazioni con ogni messaggio, chiamate, prenotazioni, lead, servizi, chiamate perse, feedback e registro delle attività, in JSON e come fogli di calcolo (CSV).",
    start: "Prepara l'esportazione completa",
    started: "Stiamo preparando l'esportazione",
    working: "Preparazione dell'archivio in corso. Ci vuole qualche minuto: puoi lasciare questa pagina e tornare più tardi.",
    history: "Esportazioni recenti",
    empty: "Ancora nessuna esportazione. Preparane una quando ti serve una copia dei tuoi dati.",
    requested: "Richiesta il {date}",
    readyUntil: "Conservata fino al {date}",
    download: "Scarica ZIP",
    downloadLabel: "Scarica ZIP: esportazione richiesta il {date}",
    downloadStarted: "Il download è iniziato",
    downloadsLeft: { one: "Resta {count} download su {total}", other: "Restano {count} download su {total}" },
    usedUp: "Questa esportazione è stata scaricata tre volte. Preparane una nuova per un'altra copia.",
    gone: "Questa esportazione non è più conservata. Preparane una nuova.",
    sizeKb: "{size} KB",
    sizeMb: "{size} MB",
    records: { one: "{count} record", other: "{count} record" },
    failed: "Non è stato possibile creare l'archivio. Preparalo di nuovo; se non riesce ancora, scrivi all'assistenza.",
    status: {
      queued: "In attesa",
      running: "In preparazione",
      ready: "Pronta",
      expired: "Eliminata",
      failed: "Non riuscita",
    },
    linkNote:
      "Ogni download crea un link monouso che funziona per 10 minuti e solo per te. Un'esportazione si può scaricare tre volte entro un giorno, e ogni titolare viene avvisato di chi l'ha scaricata, da quale dispositivo e da quale indirizzo.",
    erasedNote: "I clienti i cui dati sono stati cancellati non compaiono in nessuna esportazione.",
  },
  tables: {
    title: "Tabelle come fogli di calcolo",
    description:
      "Una tabella in CSV, per Excel, Numbers o Google Sheets. Anche Prenotazioni e Conversazioni si esportano con i filtri che scegli lì.",
  },
};
