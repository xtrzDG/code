/** `workspaceCommon.*` texts shared by channels, billing, settings and the admin, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { workspaceCommonEn } from "./common.en";

export const workspaceCommonIt: Translation<typeof workspaceCommonEn> = {
  copy: "Copia",
  copied: "Copiato",
  copyFailed: "Impossibile copiare. Seleziona il testo e copialo a mano.",
  ownerOnlyChange: "Solo il titolare può modificarlo. Puoi comunque dare un'occhiata.",
  ownerOnlyTitle: "Solo per il titolare",
  ownerOnlyDescription: "Solo il titolare dell'attività può vedere questa sezione.",
  loadMore: "Mostra altro",
  usage: {
    notIncluded: "Non incluso",
  },
  plans: {
    chat: "Chat",
    voice_and_chat: "Voce + chat",
    plus: "Plus",
  },
};
