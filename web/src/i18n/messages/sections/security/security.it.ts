/** `security.*` texts of Account → Security and the team's two-factor requirement, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { securityEn } from "./security.en";

export const securityIt: Translation<typeof securityEn> = {
  title: "Sicurezza",
  description: "Come accedi al pannello.",
  menu: "Sicurezza",
  back: "Alle mie attività",
  required: {
    business:
      "Questa attività chiede a tutto il team di accedere con un'app di autenticazione. Configurala qui sotto, poi continua.",
    admin:
      "Le pagine di amministrazione richiedono un accesso con un'app di autenticazione. Configurala qui sotto o conferma con essa, poi continua.",
    continue: "Continua",
  },
  app: {
    title: "App di autenticazione",
    description:
      "Dopo il codice di accesso, il pannello chiede anche un codice da un'app sul tuo telefono. Chi ottiene il tuo codice di accesso non può comunque entrare.",
    on: "Attivata",
    off: "Disattivata",
    pending: "Configurazione non completata",
    since: "Attivata: {date}",
    lastUsed: "Ultimo codice: {date}",
    setUp: "Configura",
    finishSetup: "Completa la configurazione",
    remove: "Disattiva",
    removeTitle: "Disattivare l'app di autenticazione?",
    removeDescription:
      "All'accesso verrà chiesto di nuovo solo il codice di accesso, e i tuoi codici di recupero smetteranno di funzionare.",
    removeAdmin:
      "Come amministratore della piattaforma, al prossimo accesso ti verrà chiesto di configurarla di nuovo.",
    removed: "L'app di autenticazione è disattivata",
    adminRequired: "Gli amministratori della piattaforma accedono sempre con un'app di autenticazione.",
    turnedOn: "L'app di autenticazione è attiva",
  },
  codes: {
    title: "Codici di recupero",
    description:
      "Per un telefono o una chiave di sicurezza smarriti: ogni codice sostituisce una volta il tuo secondo fattore.",
    left: {
      one: "Resta {count} codice non usato",
      other: "Restano {count} codici non usati",
    },
    none: "Nessun codice non usato rimasto. Generane di nuovi.",
    renew: "Genera nuovi codici",
    renewTitle: "Generare nuovi codici di recupero?",
    renewDescription: "I tuoi codici attuali smettono subito di funzionare.",
    renewing: "Preparazione…",
  },
  session: {
    title: "Questa sessione",
    twoFactor: "Accesso effettuato con un codice di accesso e un secondo fattore.",
    oneFactor: "Accesso effettuato solo con un codice di accesso.",
    upgrade: "Conferma con il secondo fattore",
    upgraded: "Questa sessione ora risulta autenticata con due fattori",
  },
  team: {
    title: "Verifica in due passaggi per il team",
    description:
      "Chiunque apra questa attività deve accedere con un'app di autenticazione oltre al codice di accesso.",
    toggle: "Richiedi un'app di autenticazione",
    on: "Obbligatoria per tutti",
    off: "Non obbligatoria",
    without: {
      one: "{count} persona non ha ancora un'app di autenticazione: non potrà aprire l'attività finché non la configura in Account → Sicurezza.",
      other:
        "{count} persone non hanno ancora un'app di autenticazione: non potranno aprire l'attività finché non la configurano in Account → Sicurezza.",
    },
    everyone: "Tutti hanno un'app di autenticazione.",
    ownFirst:
      "Prima accedi con la tua app di autenticazione: configurala o conferma con essa in Account → Sicurezza.",
    openSecurity: "Apri Sicurezza",
    ownerOnly: "Solo un titolare può modificare questa impostazione.",
    saved: "Salvato",
  },
};
