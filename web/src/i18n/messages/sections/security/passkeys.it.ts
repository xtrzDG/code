/** `passkeys.*` texts of passkeys in Account → Security, at sign-in and step-up, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { passkeysEn } from "./passkeys.en";

export const passkeysIt: Translation<typeof passkeysEn> = {
  title: "Passkey",
  description:
    "Conferma che sei tu con l'impronta digitale, il volto o il PIN del dispositivo invece di un codice. Una passkey funziona solo su questo sito, quindi non può essere rubata con il phishing.",
  recommended: "Il secondo fattore più sicuro: aggiungi una passkey su ogni dispositivo che usi.",
  unavailable:
    "Le passkey non sono ancora configurate su questo server. Usa l'app di autenticazione qui sotto.",
  unsupported:
    "Questo browser non supporta le passkey. Apri il pannello in un altro browser o usa l'app di autenticazione.",
  empty: "Ancora nessuna passkey.",
  add: "Aggiungi una passkey",
  adding: "In attesa del tuo dispositivo…",
  added: "Passkey aggiunta",
  addedOn: "Aggiunta: {date}",
  lastUsed: "Ultimo utilizzo: {date}",
  neverUsed: "Non ancora usata",
  synced: "Sincronizzata tra i tuoi dispositivi",
  suspended:
    "Rifiutata: una copia di questa passkey potrebbe essere in uso. Rimuovila e aggiungila di nuovo.",
  name: "Nome",
  rename: "Rinomina",
  renameLabel: "Rinomina {name}",
  renameTitle: "Rinomina la passkey",
  renameHint: "Ad esempio, il dispositivo o il gestore di password che la conserva.",
  renamed: "Passkey rinominata",
  save: "Salva",
  remove: "Rimuovi",
  removeLabel: "Rimuovi {name}",
  removeTitle: "Rimuovere questa passkey?",
  removeDescription:
    "Non potrai più accedere con questa passkey. Rimuovila anche dal dispositivo.",
  removed: "Passkey rimossa",
  signIn: {
    use: "Usa una passkey",
    waiting: "In attesa della tua passkey…",
    description: "Conferma con la passkey di questo dispositivo o del tuo telefono.",
    useCode: "Usa invece un codice",
    usePasskey: "Usa invece una passkey",
  },
  enrollment: {
    description:
      "Gli amministratori accedono con un secondo fattore. La passkey è il più sicuro: aggiungine una ora oppure configura un'app di autenticazione.",
    add: "Aggiungi una passkey",
    useApp: "Configura invece un'app di autenticazione",
  },
  stepUp: {
    use: "Conferma con una passkey",
    description:
      "Conferma con la passkey di questo dispositivo o del tuo telefono. Non viene inviato nulla.",
    orCode: "oppure inserisci un codice",
  },
  errors: {
    cancelled: "La richiesta della passkey è stata annullata o è scaduta. Riprova.",
    alreadyAdded: "Questo dispositivo conserva già una passkey per il tuo account.",
    wrongSite:
      "Le passkey funzionano solo all'indirizzo abituale del pannello. Aprilo da lì e riprova.",
    unsupported:
      "Questo browser non supporta le passkey. Prova un altro browser o usa un codice.",
    rejected: "Non è stato possibile confermare la passkey. Riprova.",
    suspended:
      "Questa passkey è stata rifiutata: una sua copia potrebbe essere in uso. Accedi in un altro modo, poi rimuovila.",
    unavailable: "Le passkey non sono disponibili qui. Usa invece un codice.",
  },
};
