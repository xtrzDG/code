import type { Translation } from "../../../translate";
import type { legalConsentEn } from "./legalConsent.en";

/** `legalConsent.*` in Georgian: the code step's acceptance line and the texts' dialog. */
export const legalConsentKa: Translation<typeof legalConsentEn> = {
  line: "გაგრძელებით თქვენ იღებთ {terms} და ადასტურებთ, რომ გაეცანით {privacy}.",
  terms: "მომსახურების პირობებს",
  privacy: "კონფიდენციალურობის პოლიტიკას",
  cookies: "განცხადება ქუქი-ფაილების შესახებ",
  documentUpcoming: "{date}-დან მოქმედებს ახალი ვერსია.",
  otherLanguage: "ეს ტექსტი თქვენს ენაზე ჯერ არ არის თარგმნილი; ნაჩვენებია ენაზე: {language}.",
  loading: "ტექსტი იტვირთება…",
};
