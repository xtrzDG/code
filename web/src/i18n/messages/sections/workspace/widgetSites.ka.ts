/** `widgetSites.*` texts in Georgian (typed against widgetSites.en.ts). */

import type { Translation } from "../../../translate";
import type { widgetSitesEn } from "./widgetSites.en";

export const widgetSitesKa: Translation<typeof widgetSitesEn> = {
  title: "საიტები, სადაც ჩატი მუშაობს",
  description:
    "ჩატის კოდი მუშაობს ნებისმიერ საიტზე, სადაც ჩასვამენ. ჩამოწერეთ თქვენი საიტები და ჩატი მხოლოდ მათზე იმუშავებს: კოდის ასლით ვერავინ გაუშვებს თქვენს ასისტენტს და თქვენს ტარიფს.",
  anySite: "ნებისმიერი საიტი",
  sites: { one: "{count} საიტი", other: "{count} საიტი" },
  listLabel: "დაშვებული საიტები",
  empty: "სია ჯერ არ არის: ჩატი ნებისმიერ საიტზე მუშაობს.",
  addLabel: "საიტის მისამართი",
  addHint: "როგორც ბრაუზერის მისამართის ზოლში. მისამართი www.-ით და მის გარეშე, http და https ერთ საიტად ითვლება.",
  placeholder: "https://cafe-batumi.ge",
  add: "დამატება",
  remove: "{site}-ის წაშლა",
  invalid: "ეს საიტის მისამართი არ არის. შეიყვანეთ ისე, როგორც ბრაუზერის მისამართის ზოლში, მაგალითად cafe-batumi.ge.",
  duplicate: "ეს საიტი უკვე სიაშია.",
  full: { one: "სიაში შეიძლება იყოს {count} საიტამდე.", other: "სიაში შეიძლება იყოს {count} საიტამდე." },
  alwaysAllowed: "თქვენი ჩატის გვერდი და გადახედვა კაბინეტში ყოველთვის მუშაობს.",
  ownerOnly: "სიის შეცვლა მხოლოდ მფლობელს შეუძლია.",
  save: "სიის შენახვა",
  saving: "ინახება…",
  unsaved: "არ არის შენახული",
  savedToast: "საიტების სია შენახულია",
  clearedToast: "ჩატი კვლავ ნებისმიერ საიტზე მუშაობს",
};
