/** `platformBrakes.*` texts of the admin System page's platform brakes and payment reconciliation cards, in Italian. */

import type { Translation } from "../../../translate";
import type { platformBrakesEn } from "./platformBrakes.en";

export const platformBrakesIt: Translation<typeof platformBrakesEn> = {
  brakes: {
    title: "Freni della piattaforma",
    description:
      "La pausa ferma subito tutti gli assistenti: i clienti leggono, nella loro lingua, che un collega prende in carico la richiesta e le chiamate passano al telefono dello staff dell'attività. Lo stop del budget giornaliero fa lo stesso fino alla mezzanotte UTC.",
    states: {
      running: "Gli assistenti rispondono",
      paused: "Tutti gli assistenti sono in pausa",
      stopped: "Stop del budget giornaliero attivo",
    },
    pausedSince: "In pausa dal {time}",
    reason: "Motivo:",
    budget:
      "Oggi è stato speso il {percent}% del budget giornaliero; gli assistenti si fermano al {stop}%.",
    noBudget:
      "Nessun budget giornaliero impostato: niente ferma gli assistenti.",
    pause: "Metti in pausa tutti gli assistenti",
    resume: "Riattiva tutti gli assistenti",
    pauseTitle: "Mettere in pausa tutti gli assistenti?",
    pauseDescription:
      "L'assistente di ogni attività smette subito di rispondere. I clienti passano al team e le chiamate al telefono dello staff finché non riattivi. Il registro di audit conserva il tuo motivo.",
    resumeTitle: "Riattivare tutti gli assistenti?",
    resumeDescription:
      "L'assistente di ogni attività torna subito a rispondere. Il registro di audit conserva il tuo motivo.",
    paused: "Tutti gli assistenti sono in pausa",
    resumed: "Gli assistenti rispondono di nuovo",
  },
  reconciliation: {
    title: "Riconciliazione dei pagamenti",
    description:
      "Una volta al giorno i pagamenti dell'ultima settimana vengono confrontati con Flitt e Stripe. Una differenza non viene mai corretta in automatico: verificala presso il provider.",
    notYet: "Nessuna riconciliazione eseguita oggi o ieri.",
    summary:
      "Eseguita {time}: {checked} pagamenti confrontati, {unreadable} non leggibili.",
    allMatch: "Ogni pagamento corrisponde al provider",
    differs: "Differenze trovate",
    client: "Cliente",
    provider: "Provider",
    recorded: "Qui",
    atProvider: "Presso il provider",
    kind: "Differenza",
    providers: {
      flitt: "Flitt",
      stripe: "Stripe",
    },
    statuses: {
      created: "Creato",
      processing: "In elaborazione",
      approved: "Pagato",
      declined: "Rifiutato",
      expired: "Scaduto",
      reversed: "Rimborsato",
    },
    kinds: {
      paid_at_provider: "Pagato presso il provider, non pagato qui",
      failed_at_provider: "Non riuscito presso il provider, pagato qui",
      reversed_at_provider: "Rimborsato presso il provider, pagato qui",
    },
  },
};
