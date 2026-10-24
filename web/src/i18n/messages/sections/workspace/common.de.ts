/** `workspaceCommon.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { workspaceCommonEn } from "./common.en";

export const workspaceCommonDe: Translation<typeof workspaceCommonEn> = {
  copy: "Kopieren",
  copied: "Kopiert",
  copyFailed: "Kopieren nicht möglich. Markieren Sie den Text und kopieren Sie ihn von Hand.",
  ownerOnlyChange: "Nur der Inhaber kann das ändern. Sie können sich umsehen.",
  ownerOnlyTitle: "Nur für den Inhaber",
  ownerOnlyDescription: "Nur der Inhaber des Unternehmens kann diesen Bereich sehen.",
  loadMore: "Mehr anzeigen",
  usage: {
    notIncluded: "Nicht enthalten",
  },
  plans: {
    chat: "Chat",
    voice_and_chat: "Sprache + Chat",
    plus: "Plus",
  },
};
