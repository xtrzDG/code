/** `conversationMedia.*` in Italian (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { conversationMediaEn } from "./conversationMedia.en";

export const conversationMediaIt: Translation<typeof conversationMediaEn> = {
  label: "Allegati",
  kinds: {
    audio: "Messaggio vocale",
    image: "Foto",
    location: "Posizione",
    contact: "Scheda contatto",
    sticker: "Sticker",
    file: "File",
  },
  voice: {
    transcript: "Trascrizione",
    play: "Riproduci",
    playLabel: "Riproduci il messaggio vocale",
    playerLabel: "Messaggio vocale del cliente",
    playerUnsupported: "Il tuo browser non può riprodurre l'audio qui.",
    loading: "Caricamento…",
    missing: "Questo messaggio vocale non è più disponibile: è stato eliminato alla scadenza del periodo di conservazione o insieme ai dati del cliente.",
    error: "Impossibile caricare il messaggio vocale. Riprova tra un minuto.",
    retry: "Riprova",
  },
  photo: {
    alt: "Foto inviata dal cliente",
    altWithCaption: "Foto inviata dal cliente: {caption}",
    open: "Apri la foto",
    viewerTitle: "Foto del cliente",
    unavailable: "Impossibile mostrare la foto: è stata eliminata, oppure la tua sessione è scaduta.",
  },
  place: {
    openMap: "Apri nelle mappe",
    openMapLabel: "Apri nelle mappe: {place} (si apre in una nuova scheda)",
    unnamed: "Posizione condivisa",
  },
  deleted: "Il file è stato eliminato alla scadenza del periodo di conservazione.",
  problems: {
    unsupported_kind: "L'assistente non riesce a leggere questo contenuto e ha chiesto al cliente di scrivere un messaggio.",
    too_large: "Troppo grande da aprire: al cliente è stato chiesto di scrivere un messaggio.",
    too_long: "Troppo lungo da trascrivere: al cliente è stato chiesto di scrivere un messaggio.",
    unavailable: "L'app di messaggistica non aveva più questo file: al cliente è stato chiesto di scrivere un messaggio.",
    unrecognized_format: "Formato che l'assistente non legge: al cliente è stato chiesto di scrivere un messaggio.",
    not_understood: "Non è stato possibile distinguere le parole: al cliente è stato chiesto di scrivere un messaggio.",
  },
};
