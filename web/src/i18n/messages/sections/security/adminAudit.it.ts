/** `adminAudit.*` texts of /admin/audit, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { adminAuditEn } from "./adminAudit.en";

export const adminAuditIt: Translation<typeof adminAuditEn> = {
  nav: "Audit",
  title: "Audit",
  description: "La verifica giornaliera contro le manomissioni di ogni registro attività e il registro della piattaforma: accessi non riusciti, blocchi, uscite e rotazioni delle chiavi.",
  chains: {
    title: "Verifica anti-manomissione",
    platform: "Registro della piattaforma",
    intact: "Registri invariati",
    broken: "Registri modificati",
    allIntact: "Le ultime verifiche hanno trovato il registro di ogni attività esattamente com'era stato scritto.",
    brokenList: "Registri risultati modificati",
    business: "Attività",
    entry: "Voce",
    problem: "Problema",
    checked: "Verificato",
    platformName: "Piattaforma",
  },
  log: {
    title: "Registro della piattaforma",
    description: "Voci non legate a nessuna attività, dalla più recente. L'indirizzo a cui è stato inviato un codice di accesso compare solo come impronta cifrata, mai in chiaro.",
    filters: "Filtra il registro della piattaforma",
    event: "Evento",
    allEvents: "Tutti gli eventi",
    when: "Quando",
    what: "Cosa",
    who: "Chi",
    address: "Indirizzo di rete",
    entry: "Voce",
    empty: "Ancora nessuna voce",
    emptyFiltered: "Nessuna voce per questo evento",
    unknownPerson: "Persona sconosciuta",
    system: "Sistema",
    restricted: "Il registro della piattaforma mostra gli accessi di tutti con i relativi indirizzi di rete, quindi lo vedono solo gli amministratori autorizzati a leggere il registro di sicurezza.",
  },
  events: {
    login_failed: "Codice errato",
    otp_locked: "Codice bloccato",
    mfa_locked: "Secondo passaggio bloccato",
    logout: "Uscita",
    key_rotation: "Rotazione della chiave",
  },
};
