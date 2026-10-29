/** `returnVisits.*` in Italian: Bookings → Return visits (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { returnVisitsEn } from "./returnVisits.en";

export const returnVisitsIt: Translation<typeof returnVisitsEn> = {
  loading: "Caricamento dei richiami…",
  rules: {
    rebook: "Un invito a tornare",
    recall: "Un promemoria per un controllo periodico",
    pre_arrival: "Un messaggio prima dell’arrivo",
  },
  ruleHints: {
    rebook: "Inviato il numero di giorni scelto dopo l’ultima visita del cliente, a meno che non abbia già prenotato di nuovo.",
    recall: "Inviato il numero di giorni scelto dopo l’ultima visita, per un controllo o un servizio periodico.",
    pre_arrival: "Inviato il numero di giorni scelto prima dell’inizio di una prenotazione, con un promemoria della data.",
  },
  settings: {
    title: "Messaggi di richiamo",
    description: "Un messaggio per far tornare i clienti, sul loro canale e nella loro lingua. Non viene inviato nulla finché non lo attivi.",
    toggle: "Invia messaggi di richiamo",
    rule: "Cosa inviare",
    daysAfter: "Giorni dopo l’ultima visita",
    daysBefore: "Giorni prima dell’arrivo",
    suggested: {
      one: "Di solito, per il tuo tipo di attività: “{rule}” dopo {count} giorno.",
      other: "Di solito, per il tuo tipo di attività: “{rule}” dopo {count} giorni.",
    },
    suggestedBefore: {
      one: "Di solito, per il tuo tipo di attività: “{rule}” {count} giorno prima.",
      other: "Di solito, per il tuo tipo di attività: “{rule}” {count} giorni prima.",
    },
    useSuggested: "Usa questo",
    audience: "Chi può riceverlo",
    audiences: {
      all_customers: "Tutti i clienti individuati dalla regola",
      segment: "Solo i clienti di un segmento",
    },
    segment: "Segmento",
    chooseSegment: "Scegli un segmento",
    noSegments: "Non ci sono ancora segmenti salvati.",
    toSegments: "Creane uno in Clienti → Segmenti",
    cap: "Al massimo al mese",
    capHint: "Raggiunto questo numero, i messaggi si fermano per il resto del mese.",
    monthSent: { one: "{count} messaggio inviato questo mese, su {cap}", other: "{count} messaggi inviati questo mese, su {cap}" },
    honours:
      "Non lo ricevono mai i clienti che hanno scritto STOP, che sono nella lista “non contattare” o che sono bloccati. Un cliente riceve al massimo un messaggio di questo tipo ogni due settimane, e nessuno dopo aver prenotato di nuovo.",
    whatsapp:
      "Su WhatsApp, un cliente che non scrive da 24 ore riceve il modello approvato dalla piattaforma per inviti e promemoria; un messaggio prima dell’arrivo attende una conversazione aperta.",
    save: "Salva",
    saved: "Messaggi di richiamo salvati",
    errors: {
      days: "I giorni devono essere un numero intero da 1 a 730.",
      cap: "Il limite mensile deve essere un numero intero da 1 a 2000.",
      segment: "Scegli un segmento oppure scrivi a tutti i clienti individuati dalla regola.",
    },
  },
  recent: {
    title: "Gli ultimi 30 giorni",
    sent: "Inviati",
    booked: "Hanno prenotato di nuovo",
    skipped: "Non inviati",
  },
  preview: {
    title: "Cosa leggono i clienti",
    description: "Il messaggio in ogni lingua della tua attività, con la data compilata come sarebbe oggi.",
  },
  messages: {
    title: "Ultimi messaggi",
    description: "Chi ha ricevuto un messaggio e chi ha prenotato di nuovo dopo.",
    empty: "Ancora nessun messaggio",
    emptyDescription: "Quando i messaggi sono attivi, un controllo orario scrive ai clienti a cui spettano.",
    customer: "Cliente",
    status: {
      sent: "Inviato",
      booked: "Ha prenotato di nuovo",
      skipped: "Non inviato",
    },
    skipReasons: {
      opted_out: "ha chiesto di non ricevere messaggi",
      no_contact: "il cliente è sconosciuto o cancellato",
      no_channel: "non c’è un canale per raggiungerlo",
      window_closed: "la finestra di 24 ore è chiusa e non c’è un modello",
    },
    notSentBecause: "Non inviato: {reason}",
    sentAt: "Inviato {time}",
    bookedAt: "Prenotato {time}",
    openConversation: "Apri la conversazione",
  },
};
