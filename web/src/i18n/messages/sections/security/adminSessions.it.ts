/** `adminSessions.*` texts of the admin's client page, team sign-ins, in Italian. */

import type { Translation } from "../../../translate";
import type { adminSessionsEn } from "./adminSessions.en";

export const adminSessionsIt: Translation<typeof adminSessionsEn> = {
  title: "Accessi del team",
  description:
    "Chi del team di questo cliente ha effettuato l'accesso e su quanti dispositivi. Se un telefono viene perso o un account potrebbe essere stato violato, chiudi tutte le sessioni di quella persona: dovrà accedere di nuovo.",
  roles: {
    owner: "Titolare",
    staff: "Staff",
    agency: "Agenzia",
  },
  unnamed: "Membro senza nome",
  devices: {
    one: "Accesso su {count} dispositivo",
    other: "Accesso su {count} dispositivi",
  },
  notSignedIn: "Nessun accesso attivo",
  lastUsed: "Ultimo utilizzo: {date}",
  end: "Chiudi le sessioni",
  endLabel: "Chiudi le sessioni di {name}",
  endTitle: "Chiudere tutte le sessioni di {name}?",
  endDescription:
    "Tutti i browser e i telefoni di {name} dovranno accedere di nuovo. Il registro di controllo della piattaforma annota che l'hai fatto tu.",
  ended: {
    one: "{count} sessione chiusa",
    other: "{count} sessioni chiuse",
  },
};
