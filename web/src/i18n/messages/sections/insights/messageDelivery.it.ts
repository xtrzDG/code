/** `messageDelivery.*` in Italian (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { messageDeliveryEn } from "./messageDelivery.en";

export const messageDeliveryIt: Translation<typeof messageDeliveryEn> = {
  label: "Consegna",
  states: {
    sending: "Invio…",
    retrying: "Non ancora consegnato, nuovo tentativo",
    delivered: "Consegnato",
    failed: "Non consegnato",
  },
  nextAttempt: "prossimo tentativo alle {time}",
  reasons: {
    rate_limited: "l'app di messaggistica ha chiesto di attendere",
    provider_unavailable: "l'app di messaggistica non ha risposto",
    recipient_refused: "l'app di messaggistica l'ha rifiutato (il cliente potrebbe aver bloccato l'attività, oppure la finestra di 24 ore si è chiusa)",
    template_rejected: "WhatsApp non ha accettato il modello di messaggio",
    channel_disconnected: "il canale non è più collegato",
    credential_rejected: "l'accesso al canale non funziona più: ricollegalo in Canali",
    not_configured: "nessun canale può recapitare questo messaggio",
    expired: "il momento giusto è passato prima che potesse partire",
  },
};
