import type { Translation } from "../../../translate";
import type { legalConsentEn } from "./legalConsent.en";

/** `legalConsent.*` in Russian: the code step's acceptance line and the texts' dialog. */
export const legalConsentRu: Translation<typeof legalConsentEn> = {
  line: "Продолжая, вы принимаете {terms} и подтверждаете, что прочитали {privacy}.",
  terms: "Условия использования",
  privacy: "Политику конфиденциальности",
  cookies: "Заявление о файлах cookie",
  documentUpcoming: "С {date} действует новая версия.",
  otherLanguage: "Этот текст ещё не переведён на ваш язык; он показан на языке: {language}.",
  loading: "Загружаем текст…",
};
