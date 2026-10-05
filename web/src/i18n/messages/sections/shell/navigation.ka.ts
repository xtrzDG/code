/** `navigation.*` texts: sections of a business, the sidebar and the phone tab bar, in Georgian. */

import type { Translation } from "../../../translate";
import type { navigationEn } from "./navigation.en";

export const navigationKa: Translation<typeof navigationEn> = {
  sections: {
    overview: "მიმოხილვა",
    // "შემოსული", not "შემოსულები": the word fits the phone tab bar on one line.
    inbox: "შემოსული",
    bookings: "ჯავშნები",
    assistant: "ასისტენტი",
    settings: "პარამეტრები",
  },
  descriptions: {
    overview: "როგორ მუშაობს თქვენი ასისტენტი და რა საჭიროებს დღეს თქვენს ყურადღებას.",
    inbox: "ყველა საუბარი ერთ ადგილას: კლიენტები, რომლებსაც ადამიანი სჭირდებათ, მოთხოვნები და ვინ რას უძღვება გუნდში.",
    bookings: "ჯავშნები სტატუსებით; შეგიძლიათ ხელითაც დაამატოთ.",
    assistant: "გამოსცადეთ ასისტენტი, ასწავლეთ, აირჩიეთ, სად უპასუხოს, და გამოიყენეთ ცვლილებები.",
    settings: "თქვენი ბიზნესი, გუნდი, შეტყობინებები, სწრაფი პასუხები, ზარები, შეფასებები, ტარიფი, კონფიდენციალურობა და მოქმედებების ჟურნალი.",
    assistantTest: "მისწერეთ ისე, როგორც კლიენტი მისწერდა. რეალურ კლიენტებთან არაფერი გაიგზავნება.",
    assistantProfile: "რა იცის ასისტენტმა ბიზნესზე: ადგილი, შეთავაზება, საათები და ჯავშნები, ადამიანები და წესები. ცვლილებები წერისას ინახება.",
    assistantVersions: "ასისტენტის ყველა განახლება: როდის მივიდა კლიენტებამდე, მისი შემოწმებები და დაბრუნების შესაძლებლობა.",
    assistantChecks: "კითხვები და ის, რაც პასუხმა უნდა გააკეთოს; მათ ყოველი „ცვლილებების გამოყენება“ სვამს.",
  },
  pages: {
    overviewDashboard: "დაფა",
    overviewReports: "ანგარიშები",
    assistantTest: "გამოცდა",
    assistantKnowledge: "ცოდნა",
    assistantProfile: "ბიზნესის პროფილი",
    assistantChannels: "არხები",
    assistantVersions: "ისტორია",
    assistantChecks: "ჩემი შემოწმებები",
    settingsGeneral: "ბიზნესი",
    settingsTeam: "გუნდი",
    settingsNotifications: "შეტყობინებები",
    settingsQuickReplies: "სწრაფი პასუხები",
    settingsCalls: "ზარები",
    settingsReviews: "შეფასებები",
    settingsBilling: "ტარიფი და გადახდა",
    settingsPrivacy: "კონფიდენციალურობა",
    settingsAudit: "მოქმედებების ჟურნალი",
  },
  sectionPages: "„{section}“-ის გვერდები",
  advanced: "დამატებით",
  collapse: "მენიუს ჩაკეცვა",
  expand: "მენიუს გაშლა",
  tabBar: "განყოფილებები",
  more: "მეტი",
  waiting: {
    one: "{count} ელოდება",
    other: "{count} ელოდება",
  },
  ownerOnlyTitle: "ეს გვერდი მფლობელებისთვისაა",
  ownerOnlyDescription: "თქვენი როლი „{business}“-ში ამ გვერდს არ ხსნის. თუ აქ რამის შეცვლაა საჭირო, მიმართეთ მფლობელს.",
  toOverview: "მიმოხილვაზე გადასვლა",
};
