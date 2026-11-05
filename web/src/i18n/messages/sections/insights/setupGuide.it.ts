/** `setupGuide.*` in Italian: the setup guide card and milestones (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { setupGuideEn } from "./setupGuide.en";

export const setupGuideIt: Translation<typeof setupGuideEn> = {
  titleSetup: "Configura il tuo assistente",
  titleLive: "Attira i primi clienti",
  descriptionSetup: "Ogni passo riprende da dove ti eri fermato. L'assistente risponde ai clienti una volta pubblicato.",
  liveSince: "Risponde ai clienti dal {date}",
  minutesLeft: { one: "ancora circa {count} minuto", other: "ancora circa {count} minuti" },
  continueSetup: "Continua la configurazione",
  afterLaunchHint: "Dopo il lancio: una prova dal tuo telefono, un secondo canale e il link per i clienti.",
  minutes: "{count} min",
  optional: "facoltativo",
  skip: "Salta",
  unskip: "Ripristina",
  skipLabel: "Salta “{step}”",
  unskipLabel: "Ripristina “{step}”",
  status: {
    next: "Prossimo",
    skipped: "Saltato",
  },
  phone: {
    description: "Inquadra il codice con la fotocamera del telefono e scrivi all'assistente come farebbe un cliente.",
    qrAlt: "Codice QR di {link}",
    copyLink: "Copia link",
    unavailable: "La pagina della chat è disattivata. Attiva la chat del sito in Canali, oppure scrivi dal telefono a un'app di messaggistica collegata.",
    orTelegram: "Oppure su Telegram:",
    listening: "In attesa del tuo messaggio…",
    hint: "Il passo è completato quando arriva il tuo messaggio.",
    success: "Funziona: il tuo messaggio è arrivato all'assistente.",
    hide: "Nascondi",
  },
  finished: {
    title: "Tutto pronto",
    description: "L'assistente risponde ai clienti, e loro sanno dove trovarlo.",
    dismiss: "Nascondi questa scheda",
  },
  wins: {
    title: "Traguardi",
    first_conversation: "Prima conversazione con un cliente",
    first_booking: "Prima prenotazione",
    first_after_hours_booking: "Prima prenotazione fuori orario",
  },
  ring: {
    title: "Configurazione",
    label: "Configurazione {percent}% completata",
    short: "{percent}%",
  },
  celebrations: {
    first_conversation: {
      title: "Il primo cliente ti ha scritto",
      description: "L'assistente ha risposto. Trovi la conversazione in Conversazioni.",
    },
    first_booking: {
      title: "La prima prenotazione",
      description: "L'assistente ha preso una prenotazione da solo.",
    },
    first_after_hours_booking: {
      title: "Una prenotazione mentre eri chiuso",
      description: "Un cliente ha prenotato fuori orario, e nessuno ha dovuto rispondere.",
    },
    openInbox: "Apri Conversazioni",
    openBookings: "Apri le prenotazioni",
    close: "Chiudi",
  },
};
