/** `assistantControls.*` texts of Settings → General's assistant controls card, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { assistantControlsEn } from "./assistantControls.en";

export const assistantControlsIt: Translation<typeof assistantControlsEn> = {
  title: "Controlli dell'assistente",
  description: "Fermate subito l'assistente quando sbaglia: la modifica vale dal messaggio successivo.",
  handOver: {
    label: "Passa ogni cliente al team",
    hint: "I nuovi messaggi aspettano il vostro team nella posta in arrivo e le chiamate vanno al vostro numero di inoltro.",
  },
  actions: {
    title: "Cosa può fare l'assistente",
    hint: "Un'azione disattivata viene rifiutata: l'assistente prende una richiesta o passa il cliente a un collega.",
    allOn: "Tutte attive",
    someOff: "Alcune disattivate",
    create_booking: "Creare prenotazioni",
    reschedule_booking: "Spostare prenotazioni",
    cancel_booking: "Annullare prenotazioni",
    join_waitlist: "Mettere i clienti in lista d'attesa",
    create_lead: "Prendere richieste e ordini",
    send_link: "Inviare link",
    send_payment_link: "Inviare link di pagamento dell'acconto",
  },
  ownerOnly: "Solo i proprietari possono modificarlo.",
  handedOver: "Ora ogni cliente va al vostro team",
  resumed: "L'assistente risponde di nuovo da solo",
  actionOff: "Azione disattivata",
  actionOn: "Azione attivata",
};
