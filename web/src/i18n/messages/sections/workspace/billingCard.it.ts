/** `billingCard.*` texts of Settings → Billing (the card on file, payment retries, the trial's "Save card" prompt), in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { billingCardEn } from "./billingCard.en";

export const billingCardIt: Translation<typeof billingCardEn> = {
  title: "Carta per i pagamenti",
  description: "I pagamenti automatici dell'abbonamento vengono addebitati su questa carta.",
  endingIn: "Carta che termina con {digits}",
  expires: "Scade il {date}",
  noExpiry: "Scadenza non comunicata",
  expiryStates: {
    expired: "Scaduta",
    expiring: "In scadenza",
  },
  facts: {
    provider: "Servizio di pagamento",
    savedAt: "Salvata il",
  },
  noCard: "Ancora nessuna carta salvata",
  noCardTrial: "Salva una carta e l'abbonamento prosegue da solo alla fine della prova gratuita.",
  noCardPaid: "Salva una carta così i prossimi pagamenti vanno a buon fine da soli.",
  cardWithoutDetails: "Una carta è salvata presso {provider}. I suoi dati compariranno qui dopo il prossimo pagamento.",
  expiredHint: "Questa carta è scaduta. Salvane una nuova prima del prossimo pagamento.",
  expiringHint: "Questa carta scade a breve. Salvane una nuova così il prossimo pagamento va a buon fine.",
  noCharge: "Salvare una carta non comporta addebiti: il servizio di pagamento si limita a verificarla.",
  payToSave: "Pagando la fattura aperta salvi la carta con cui paghi.",
  setupFeeNow: "Salvando la carta viene addebitato subito il costo una tantum di configurazione di {amount}. I pagamenti mensili iniziano alla fine della prova gratuita.",
  retryUsesNewCard: "Il prossimo tentativo addebita la carta che salvi.",
  save: "Salva carta",
  update: "Aggiorna carta",
  opening: "Apertura…",
  retry: {
    title: "Il pagamento automatico non è andato a buon fine",
    declined: "La carta è stata rifiutata. Riproveremo noi in automatico.",
    outcomes: {
      claimed: "Tentativo {attempt} di {total} in corso.",
      approved: "Il tentativo {attempt} di {total} è andato a buon fine. Il pagamento è in fase di conferma.",
      declined: "Il tentativo {attempt} di {total} è stato rifiutato.",
      processing: "Il tentativo {attempt} di {total} è in elaborazione.",
      failed: "Il tentativo {attempt} di {total} non ha raggiunto il servizio di pagamento.",
      not_possible: "Il tentativo {attempt} di {total} non è stato possibile: non c'è una carta salvata da addebitare.",
      skipped: "Il tentativo {attempt} di {total} è stato saltato.",
    },
    next: "Prossimo tentativo: {date}",
    noMore: "Non ci sono altri tentativi. Dal {date} l'assistente accetta solo richieste.",
  },
  trialPrompt: {
    title: { one: "Resta {count} giorno di prova gratuita", other: "Restano {count} giorni di prova gratuita" },
    body: "Nessun addebito fino al {date}: salva ora una carta e l'assistente continuerà a rispondere dopo la prova gratuita.",
    bodyWithSetupFee: "Salva ora una carta: servirà a pagare il costo una tantum di configurazione di {amount} e dal {date} riceverà i pagamenti mensili. L'assistente continuerà a rispondere dopo la prova gratuita.",
  },
  returned: {
    title: "Salvataggio della carta",
    pending: "La carta comparirà qui appena il servizio di pagamento la conferma, di solito entro un minuto.",
    savedTitle: "Carta salvata",
    saved: "Da ora i pagamenti automatici vengono addebitati su questa carta.",
  },
  errors: {
    cannotSave: "Al momento non è possibile salvare una carta. Paga invece la fattura aperta: così salvi la carta con cui paghi.",
  },
};
