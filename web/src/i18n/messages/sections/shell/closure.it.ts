/** `closure.*` texts of closing and deleting a business or an account, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { closureEn } from "./closure.en";

export const closureIt: Translation<typeof closureEn> = {
  banner: {
    label: "Chiusura dell'attività",
    title: "Questa attività è in chiusura",
    countdown: {
      one: "Tutto il suo contenuto verrà eliminato definitivamente tra {count} giorno, il {date}",
      other: "Tutto il suo contenuto verrà eliminato definitivamente tra {count} giorni, il {date}",
    },
    due: "I 30 giorni sono trascorsi: l'eliminazione inizia entro un'ora.",
    deleting: "L'attività è in fase di eliminazione. Non è più possibile fermarla.",
    unpaid: "È stata chiusa perché l'abbonamento è scaduto senza pagamento.",
    keep: "Mantieni l'attività",
    pay: "Paga per mantenerla",
    open: "Dettagli della chiusura",
    kept: "L'attività è di nuovo aperta",
  },
  zone: {
    title: "Chiudi questa attività",
    description:
      "Per quando l'attività smette di usare l'assistente. Un titolare può ripensarci entro 30 giorni; dopodiché l'attività viene eliminata definitivamente.",
    willPause: "L'assistente smette di rispondere ai clienti e tutti i canali vengono scollegati.",
    willStopCharges: "Gli addebiti automatici si interrompono: non viene più fatturato nulla.",
    willDelete:
      "Dopo 30 giorni, tutto il contenuto dell'attività viene eliminato definitivamente: conversazioni, clienti, prenotazioni, registrazioni, file e conoscenze.",
    willKeep: "Le fatture emesse e il registro attività vengono conservati per il tempo richiesto dalla legge.",
    exportFirst: "Prima scarica una copia completa dei dati",
    action: "Chiudi l'attività…",
    dialogTitle: "Chiudere l'attività?",
    dialogDescription:
      "L'assistente smette subito di rispondere e i canali vengono scollegati. L'attività verrà eliminata definitivamente tra 30 giorni, a meno che un titolare non decida di mantenerla.",
    confirm: "Chiudi l'attività",
    closing: "Chiusura…",
    closed: "L'attività è in chiusura",
    pendingTitle: "L'attività è in chiusura",
    closedBy: "Chiusa da {name} il {date}",
    closedOn: "Chiusa il {date}",
    unpaidHint: "È stata chiusa perché l'abbonamento è scaduto senza pagamento: paga in Fatturazione, poi mantieni l'attività qui.",
    keepHint: "Mantenendola, i canali tornano attivi; riattiva l'assistente quando vuoi.",
    keep: "Mantieni l'attività",
    billing: "Apri Fatturazione",
    export: "Scarica i dati",
    deletingTitle: "L'attività è in fase di eliminazione",
    deletingDescription:
      "L'eliminazione è iniziata e non è più possibile fermarla. I titolari riceveranno il certificato di eliminazione in Account → Sicurezza.",
  },
  account: {
    title: "Elimina il tuo account",
    description:
      "Ti disconnette ovunque ed elimina i tuoi metodi di accesso (passkey, app di autenticazione, codici di recupero), le impostazioni delle notifiche e le notifiche dell'app. Esci da tutte le attività di cui fai parte; i loro dati restano a loro.",
    ownerNote: "L'ultimo titolare di un'attività deve prima chiuderla (Impostazioni → Attività) o nominare titolare un altro membro.",
    platformNote: "I membri del team della piattaforma escono dal team (Amministrazione → Team) prima di eliminare il proprio account.",
    action: "Elimina l'account…",
    dialogTitle: "Eliminare il tuo account?",
    dialogDescription: "L'operazione non può essere annullata. Potrai registrarti di nuovo in seguito con la stessa e-mail o lo stesso telefono, come nuovo account.",
    confirm: "Elimina l'account",
    deleting: "Eliminazione…",
    lastOwner: "Sei l'ultimo titolare di {names}. Prima chiudi l'attività da Impostazioni → Attività oppure nomina titolare un altro membro.",
    lastBrandOwner: "Sei l'unico titolare del brand {names}. Prima nomina un'altra persona titolare del brand.",
    lastOwnerUnnamed: "Sei l'ultimo titolare di un'attività o di un brand. Prima chiudila oppure nomina titolare un'altra persona.",
    platformTeam: "I membri del team della piattaforma escono dal team (Amministrazione → Team) prima di eliminare il proprio account.",
  },
  deletions: {
    title: "Attività eliminate",
    description: "Le attività di cui eri titolare che sono state chiuse ed eliminate. Ogni certificato indica cosa è stato eliminato, quando e cosa la legge impone di conservare.",
    reasonOwner: "Chiusa da un titolare",
    reasonUnpaid: "Chiusa dopo la scadenza dell'abbonamento senza pagamento",
    inProgress: "In fase di eliminazione",
    completedOn: "Eliminata il {date}",
    startedOn: "Eliminazione iniziata il {date}",
    certificate: "Certificato (PDF)",
    downloading: "Download in corso…",
  },
};
