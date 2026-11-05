/** `billingLifecycle.*` texts of Settings → Billing (why owners cancel, the offers instead, the seasonal pause), in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { billingLifecycleEn } from "./billingLifecycle.en";

export const billingLifecycleIt: Translation<typeof billingLifecycleEn> = {
  reasons: {
    too_expensive: "Costa troppo",
    seasonal_break: "Siamo chiusi per la stagione",
    not_enough_use: "Al momento ci scrivono o chiamano troppo pochi clienti",
    missing_feature: "Non fa una cosa di cui abbiamo bisogno",
    answer_quality: "Le risposte non sono abbastanza buone",
    switched_provider: "Passiamo a un altro servizio",
    closing_business: "Chiudiamo l'attività",
    somethingElse: "Altro",
  },
  cancel: {
    reasonLegend: "Qual è il motivo principale?",
    reasonHint: "Ci aiuta a migliorare, e forse c'è qualcosa che fa al caso tuo meglio della disdetta.",
    detailsLabel: "Vuoi aggiungere qualcosa?",
    detailsPlaceholder: "Con parole tue",
    continue: "Continua",
    offerTitle: "Prima di andare",
    cancelAnyway: "No, disdici comunque",
    back: "Indietro",
  },
  offerKinds: {
    pause: "Pausa stagionale",
    downgrade: "Piano più economico",
    credit: "Credito una tantum",
  },
  offers: {
    pause: {
      title: "Prenditi invece una pausa stagionale",
      description:
        "Un mese in pausa costa {price}: l'assistente continua a raccogliere richieste, i tuoi canali restano collegati e il servizio completo torna da solo.",
      confirm: { one: "Metti in pausa per {count} mese", other: "Metti in pausa per {count} mesi" },
    },
    downgrade: {
      title: "Tieni il tuo assistente spendendo meno",
      description:
        "“{plan}” costa {price}. Risposte, canali e impostazioni restano come sono; il nuovo prezzo vale dalla prossima fattura.",
      confirm: "Passa a “{plan}”",
    },
    credit: {
      title: "Resta, e {amount} li offriamo noi",
      description: "Accreditiamo {amount} sul tuo account; verranno scalati dalla prossima fattura.",
      confirm: "Accetta il credito",
    },
    taken: {
      pause: "La pausa è programmata",
      downgrade: "Il piano è cambiato",
      credit: "Il credito è sul tuo account",
    },
  },
  pause: {
    title: "Pausa stagionale",
    description:
      "Chiudi per la stagione? Metti in pausa invece di disdire: l'assistente continua a raccogliere richieste, i tuoi canali restano collegati e il servizio completo torna da solo.",
    price: "{price} al mese, il {percent}% del tuo piano",
    monthsLegend: "Per quanto tempo",
    months: { one: "{count} mese", other: "{count} mesi" },
    window: "Dal {start} al {until}",
    submit: "Metti in pausa dal {date}",
    allowance: "Pausa usata: {months} ({window}).",
    allowanceMonths: { one: "{used} mese su {cap}", other: "{used} mesi su {cap}" },
    allowanceWindow: { one: "ultimo mese", other: "ultimi {window} mesi" },
    scheduledTitle: "Pausa programmata",
    scheduled:
      "Dal {start} al {until} l'assistente accetta solo richieste. I pagamenti automatici sono sospesi; i pagamenti a prezzo pieno riprendono dopo la pausa.",
    callOff: "Annulla la pausa",
    calledOff: "La pausa è annullata",
    pausedTitle: "In pausa fino al {date}",
    paused:
      "L'assistente accetta solo richieste; i tuoi canali restano collegati. Ogni mese di pausa viene fatturato al {percent}% del tuo piano.",
    resume: "Riprendi il servizio completo",
    resumeTitle: "Riprendere ora il servizio completo?",
    resumeDescription:
      "L'assistente torna a rispondere ai clienti e ad accettare prenotazioni. Se questo mese di pausa è già pagato, il servizio completo torna alla sua fine; altrimenti subito, e il periodo successivo va pagato.",
    resumed: "Il servizio completo sta tornando",
    plansHint: "Durante la pausa il piano resta invariato; riprendi il servizio completo per cambiarlo.",
    unavailable: {
      not_active: "La pausa è possibile solo con un abbonamento mensile pagato.",
      not_monthly: "Un piano annuale non si può mettere in pausa.",
      allowance_used: "Negli ultimi dodici mesi hai già usato quattro mesi di pausa; potrai metterla di nuovo più avanti.",
    },
  },
  facts: {
    pause: "Pausa stagionale",
  },
  errors: {
    offerGone: "Questa offerta non è più disponibile. Chiudi la finestra e riprova.",
    pauseGone: "Al momento la pausa non è possibile. Ricarica la pagina per vedere perché.",
  },
};
