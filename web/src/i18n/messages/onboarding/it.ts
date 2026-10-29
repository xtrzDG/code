import type { Translation } from "../../translate";
import type { onboardingEn } from "./en";
import { profileEditIt } from "./profileEdit.it";

/** Texts of the business profile in Italian (a draft awaiting a native speaker's review). Keys as in en.ts. */
export const onboardingIt: Translation<typeof onboardingEn> = {
  onboarding: {
    choose: "Scegli…",
    gaps: {
      times: { one: "{count} volta", other: "{count} volte" },
      notReady: { one: "Manca {count} dato obbligatorio", other: "Mancano {count} dati obbligatori" },
    },
    week: {
      closed: "Chiuso",
      opens: "Apre",
      closes: "Chiude",
      addInterval: "Aggiungi una pausa o un secondo turno",
      removeInterval: "Rimuovi l’intervallo",
      overnight: "fino alle {time} del giorno dopo",
      roundTheClock: "Aperto 24 ore su 24",
      copyToAll: "Copia il lunedì su tutti i giorni",
    },
    offer: {
      kinds: {
        faq: "Domanda e risposta",
        policy: "Regola",
        menu_item: "Piatto del menù",
        service: "Servizio",
        room_type: "Tipo di camera",
        package: "Pacchetto",
        vehicle: "Veicolo",
        product: "Prodotto",
      },
    },
    booking: {
      noBookings: "Il tuo settore non prevede prenotazioni: l’assistente raccoglie le richieste e le passa al responsabile.",
      resourceKinds: {
        table: "Tavolo",
        room: "Camera",
        staff: "Professionista",
        arena: "Campo o sala",
        bay: "Postazione di servizio",
        vehicle: "Veicolo",
        slot: "Fascia oraria",
      },
    },
    resources: {
      namePlaceholder: "Ad esempio: Campo 1",
    },
  },
  profileEdit: profileEditIt,
};
