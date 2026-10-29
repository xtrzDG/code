/** `adminTeam.*` texts of the platform admin team page, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { adminTeamEn } from "./adminTeam.en";

export const adminTeamIt: Translation<typeof adminTeamEn> = {
  nav: "Team",
  title: "Team di amministrazione",
  description:
    "Chi può aprire le pagine di amministrazione e cosa può fare ogni ruolo. Ogni modifica viene annotata nel registro di audit.",
  roles: {
    super: "Super admin",
    support_readonly: "Assistenza (sola lettura)",
    billing: "Fatturazione",
  },
  roleHints: {
    super: "Tutto: clienti, operazioni, metriche, il team; modifiche nel pannello di un cliente quando il titolare lo consente.",
    support_readonly: "Clienti e stato di salute della piattaforma; apre il pannello di un cliente per un'ora, in sola lettura.",
    billing: "Clienti, il loro account (prova gratuita, sconti, credito, pagamenti manuali, piano), note e metriche di crescita; non apre mai il pannello di un cliente.",
  },
  you: "Tu",
  notSignedIn: "Non ha ancora effettuato l'accesso",
  addedBy: "Aggiunto da {name} il {date}",
  addedOn: "Aggiunto dalla pagina Team il {date}",
  bootstrapped: "Dalle liste PLATFORM_ADMIN_* il {date}",
  role: "Ruolo",
  roleFor: "Ruolo di {name}",
  changed: "Ruolo cambiato",
  remove: "Rimuovi",
  removeLabel: "Rimuovi {name} dal team",
  removeTitle: "Rimuovere {name} dal team di amministrazione?",
  removeDescription: "Perde l'accesso alle pagine di amministrazione alla prossima richiesta.",
  removed: "Rimosso dal team",
  add: "Aggiungi una persona",
  addTitle: "Aggiungi una persona al team di amministrazione",
  addDescription:
    "Avrà accesso alle pagine di amministrazione al prossimo accesso con questo numero di telefono o e-mail, e dovrà configurare un'app di autenticazione.",
  by: "Accede con",
  byPhone: "Numero di telefono",
  byEmail: "E-mail",
  phone: "Numero di telefono",
  email: "E-mail",
  added: "Aggiunto al team",
  lastSuper: "Il team ha bisogno di almeno un super admin: assegna prima il ruolo a qualcun altro.",
};
