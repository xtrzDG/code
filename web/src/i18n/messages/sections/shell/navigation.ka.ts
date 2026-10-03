/** `navigation.*` texts: sections of a business, the sidebar and the phone tab bar, in Georgian. */

import type { Translation } from "../../../translate";
import type { navigationEn } from "./navigation.en";

export const navigationKa: Translation<typeof navigationEn> = {
  sections: {
    overview: "მიმოხილვა",
    messages: "მიმოწერა",
    bookings: "ჯავშნები",
    assistant: "ასისტენტი",
    settings: "პარამეტრები",
  },
  descriptions: {
    overview: "როგორ მუშაობს თქვენი ასისტენტი და რა საჭიროებს დღეს თქვენს ყურადღებას.",
    messages: "ყველა საუბარი, ადამიანის მომლოდინე საუბრები და კლიენტების მოთხოვნები ერთ ადგილას.",
    bookings: "ჯავშნები სტატუსებით; შეგიძლიათ ხელითაც დაამატოთ.",
    assistant: "გამოსცადეთ ასისტენტი, ასწავლეთ, აირჩიეთ, სად უპასუხოს, და გამოიყენეთ ცვლილებები.",
    settings: "თქვენი ბიზნესი, გუნდი, შეტყობინებები, ზარები, ტარიფი, კონფიდენციალურობა და მოქმედებების ჟურნალი.",
    assistantTest: "მისწერეთ ისე, როგორც კლიენტი მისწერდა. რეალურ კლიენტებთან არაფერი გაიგზავნება.",
    assistantProfile: "კონტაქტები, სამუშაო საათები, თქვენი შეთავაზება, დაჯავშნის წესები და როდის დაუძახოს ადამიანს — ანკეტა, რომლითაც ასისტენტი მუშაობს.",
    assistantVersions: "ასისტენტის ყველა განახლება შემოწმებებით, გამოქვეყნებითა და დაბრუნების შესაძლებლობით.",
  },
  pages: {
    overviewDashboard: "დაფა",
    overviewReports: "ანგარიშები",
    messagesAll: "ყველა საუბარი",
    messagesHandoffs: "ადამიანის დახმარება",
    messagesLeads: "მოთხოვნები",
    assistantTest: "გამოცდა",
    assistantKnowledge: "ცოდნა",
    assistantProfile: "საათები და წესები",
    assistantChannels: "არხები",
    assistantVersions: "განახლებები და შემოწმებები",
    settingsGeneral: "ბიზნესი",
    settingsTeam: "გუნდი",
    settingsNotifications: "შეტყობინებები",
    settingsCalls: "ზარები",
    settingsBilling: "ტარიფი და გადახდა",
    settingsPrivacy: "კონფიდენციალურობა",
    settingsAudit: "მოქმედებების ჟურნალი",
  },
  sectionPages: "„{section}“-ის გვერდები",
  applyChanges: "ცვლილებების გამოყენება",
  applyChangesHint: "განახლების მომზადება ანკეტიდან და ცოდნიდან, შემოწმება და გამოქვეყნება, თუ შემოწმებები გაიარა.",
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
