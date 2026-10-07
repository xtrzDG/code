/** `privacyRetention.*` texts: Settings → Privacy → retention, in Georgian. */

import type { Translation } from "../../../translate";
import type { privacyRetentionEn } from "./privacyRetention.en";

export const privacyRetentionKa: Translation<typeof privacyRetentionEn> = {
  title: "რამდენ ხანს ინახება მონაცემები",
  description:
    "კლიენტების მონაცემები ავტომატურად იშლება ამ ვადების გასვლის შემდეგ. თქვენი ჩატის კონფიდენციალურობის შეტყობინება კლიენტებს იმავე ვადებს ატყობინებს.",
  conversations: {
    label: "საუბრები",
    hint: "აითვლება საუბრის ბოლო შეტყობინებიდან. შემდეგ იშლება მისი შეტყობინებები, გუნდის ჩანაწერები, ზარების ტრანსკრიფციები და ჩანაწერები; ჯავშნებს, მოთხოვნებსა და მიმართვებს რჩება მხოლოდ ის, რაც პერსონალური არ არის.",
  },
  modelRecords: {
    label: "ასისტენტის AI მიმართვების ჩანაწერები",
    hint: "AI მოდელისთვის გაგზავნილი ზუსტი ტექსტი, რომელიც პასუხების შესამოწმებლად ინახება. იშლება ჩვენთან და ხარისხის ჟურნალში (Langfuse). არაუმეტეს 30 დღისა.",
  },
  periods: {
    days: { one: "{count} დღე", other: "{count} დღე" },
    months: { one: "{count} თვე", other: "{count} თვე" },
    years: { one: "{count} წელი", other: "{count} წელი" },
    recommended: "{period} (რეკომენდებული)",
    maximum: "{period} (მაქსიმუმი)",
  },
  recordings: "ზარების ჩანაწერები ინახება {period}.",
  changeRecordings: "შეცვლა „ზოგადში“",
  processorsTitle: "ასლები ჩვენს ქვედამმუშავებლებთან",
  processors: {
    langfuse: "Langfuse: ასისტენტის AI მიმართვების ჟურნალი",
    elevenlabs: "ElevenLabs: სატელეფონო ზარები (აუდიო და ტრანსკრიფცია)",
  },
  processorsDeleted: "იშლება ჩვენსას ერთად — ამ ვადებით და როცა კლიენტის მონაცემებს შლით:",
  processorsNone:
    "Langfuse და ElevenLabs ამ პლატფორმაზე არ გამოიყენება, ამიტომ მათთან თქვენი კლიენტების მონაცემების ასლები არ ინახება.",
  messagingApps:
    "მიმოწერა WhatsApp-ში, Messenger-ში, Instagram-სა და Telegram-ში რჩება კლიენტის აპლიკაციაში: იქ მისი წაშლა მხოლოდ კლიენტს შეუძლია.",
  lastCleanupTitle: "ბოლო გასუფთავება",
  lastCleanup: "{date}",
  nothingDue: "წასაშლელი არაფერი იყო.",
  noCleanupYet: "პირველი გასუფთავება ამაღამ ჩატარდება.",
  removed: { one: "წაიშალა {count} ჩანაწერი", other: "წაიშალა {count} ჩანაწერი" },
  counts: {
    deleted_messages: "შეტყობინებები",
    deleted_llm_turns: "AI მიმართვების ჩანაწერები",
    deleted_notes: "გუნდის ჩანაწერები",
    deleted_media: "კლიენტების ფაილები",
    deleted_missed_calls: "გამოტოვებული ზარები",
    erased_calls: "ზარები",
    anonymized_leads: "მოთხოვნები",
    anonymized_bookings: "ჯავშნები",
    anonymized_handoffs: "მიმართვები",
  },
  shorterTitle: "წაიშალოს ძველი მონაცემები ამაღამ?",
  shorterDescription:
    "უფრო მოკლე ვადებით ამაღამდელი გასუფთავება სამუდამოდ წაშლის ყველაფერს, რაც მათ სცდება (საუბრები — {conversations}, AI მიმართვების ჩანაწერები — {modelRecords}). ამის გაუქმება შეუძლებელია.",
  shorterConfirm: "შემოკლება და წაშლა",
  qualitySampling: {
    label: "ხარისხის შემოწმება რეალურ საუბრებზე",
    hint: "ყოველ ღამე დასრულებული საუბრების მცირე ნიმუშს (სატესტო ჩატების გარეშე) აფასებს იგივე AI მომწოდებელი, რომელიც პასუხებს წერს — ასე სუსტი პასუხები ასისტენტის ხარისხში ჩანს. გამორთეთ, რომ თქვენი კლიენტების საუბრები ამ შემოწმებებში არ მოხვდეს.",
  },
};
