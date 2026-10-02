/**
 * `workspace.*` texts of shared by channels, billing, settings and the admin,
 * in Georgian.
 */

import type { Translation } from "../../../translate";
import type { workspaceCommonEn } from "./common.en";

export const workspaceCommonKa: Translation<typeof workspaceCommonEn> = {
  copy: "კოპირება",
  copied: "დაკოპირდა",
  copyFailed: "კოპირება ვერ მოხერხდა. მონიშნეთ ტექსტი და დააკოპირეთ ხელით.",
  ownerOnlyChange: "ამის შეცვლა მხოლოდ მფლობელს შეუძლია. დათვალიერება შეგიძლიათ.",
  ownerOnlyTitle: "მხოლოდ მფლობელისთვის",
  ownerOnlyDescription: "ამ ნაწილს მხოლოდ ბიზნესის მფლობელი ხედავს.",
  refresh: "განახლება",
  loadMore: "მეტის ჩვენება",
  usage: {
    notIncluded: "არ შედის",
  },
  plans: {
    chat: "ჩატი",
    voice_and_chat: "ხმა + ჩატი",
    plus: "პლუსი",
  },
};
