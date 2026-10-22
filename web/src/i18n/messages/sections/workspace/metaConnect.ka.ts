/**
 * `metaConnect.*` ქართულად: „Facebook-ით გაგრძელება“ WhatsApp-ის,
 * Instagram-ისა და Messenger-ისთვის, გვერდის არჩევა, Meta-ს უარი მარტივი
 * სიტყვებით, კომენტარებზე პასუხები Instagram-ის ბარათზე და Meta-ს ბარათი
 * დაყენებისას.
 */

import type { Translation } from "../../../translate";
import type { metaConnectEn } from "./metaConnect.en";

export const metaConnectKa: Translation<typeof metaConnectEn> = {
  continue: "Facebook-ით გაგრძელება",
  intro: {
    whatsapp:
      "შედით Facebook-ით და მის ფანჯარაში აირჩიეთ ან შექმენით WhatsApp Business ანგარიში და ნომერი. ნომერს ჩვენ თვითონ დავაკავშირებთ.",
    instagram:
      "შედით Facebook-ით და აირჩიეთ გვერდი, რომელსაც Instagram-ის პროფესიული ანგარიში უკავშირდება. დანარჩენს ჩვენ გავაკეთებთ.",
    messenger: "შედით Facebook-ით და აირჩიეთ გვერდი, რომლის Messenger-ის ჩატებსაც ასისტენტი უპასუხებს.",
  },
  orManual: "უკვე გაქვთ იდენტიფიკატორები და გასაღები? მათი ხელით შეყვანა ისევ შეიძლება.",
  preparing: "Facebook-ს ვამზადებთ…",
  starting: "ვიწყებთ…",
  openWindow: "Facebook-ის ფანჯრის გახსნა",
  openHint: "ბრაუზერი დაჭერას ითხოვს: Facebook-ში შესვლა ახალ ფანჯარაში გაიხსნება.",
  waiting: "დაასრულეთ Facebook-ის ფანჯარაში. ეს ფანჯარა დაელოდება.",
  finishing: "ვაკავშირებთ…",
  notices: {
    cancelled: "Facebook-ის ფანჯარა ბოლომდე მისვლამდე დაიხურა. სცადეთ თავიდან, როცა მზად იქნებით.",
    failed: "Facebook-მა დაკავშირება ვერ დაასრულა. სცადეთ თავიდან ან შეიყვანეთ მონაცემები ხელით.",
    unavailable:
      "Facebook-ით შესვლა ვერ ჩაიტვირთა (შესაძლოა, რეკლამის ბლოკერი უშლის). სცადეთ მოგვიანებით ან შეიყვანეთ მონაცემები ხელით.",
  },
  pages: {
    title: "აირჩიეთ გვერდი",
    hint: "გვერდები, რომლებსაც Facebook-ზე მართავთ.",
    instagramHint: "Instagram-ის დაკავშირება მხოლოდ იმ გვერდით შეიძლება, რომელსაც Instagram-ის პროფესიული ანგარიში უკავშირდება.",
    none: "Facebook-მა თქვენი არცერთი გვერდი არ აჩვენა. დაიწყეთ თავიდან და Facebook-ის ფანჯარაში მონიშნეთ ბიზნესის გვერდი.",
    instagram: "Instagram: @{username}",
    instagramNoName: "Instagram დაკავშირებულია",
    noInstagram: "Instagram დაკავშირებული არ არის",
    connect: "ამ გვერდის დაკავშირება",
    connecting: "ვაკავშირებთ…",
  },
  refusals: {
    meta_link_expired: "Facebook-ით ეს შესვლა უკვე დასრულდა. დაიწყეთ თავიდან.",
    meta_not_configured: "ამ სერვერზე Facebook-ით შესვლა მოწყობილი არ არის. შეიყვანეთ მონაცემები ხელით.",
    meta_permission_missing: "Facebook-მა ყველა საჭირო ნებართვა არ მოგვცა. დაიწყეთ თავიდან და ყველა ველი მონიშნული დატოვეთ.",
    whatsapp_account_missing: "Facebook-მა WhatsApp Business ანგარიში არ დააბრუნა. დაიწყეთ თავიდან და აირჩიეთ ან შექმენით ის.",
    whatsapp_number_missing: "ამ WhatsApp Business ანგარიშს ჯერ ნომერი არ აქვს. დაამატეთ ის Facebook-ის ფანჯარაში.",
    whatsapp_pin_mismatch:
      "ამ ნომერზე ორსაფეხურიანი შემოწმება სხვა PIN-კოდით არის ჩართული. გამორთეთ ის WhatsApp Manager-ში და სცადეთ თავიდან.",
    meta_page_not_found: "Facebook-მა ამ გვერდზე წვდომა არ მოგვცა. დაიწყეთ თავიდან და მონიშნეთ ის Facebook-ის ფანჯარაში.",
    instagram_account_missing:
      "ამ გვერდს Instagram-ის პროფესიული ანგარიში არ უკავშირდება. დააკავშირეთ ის Instagram-ის პარამეტრებში ან აირჩიეთ სხვა გვერდი.",
  },
  commentReplies: {
    title: "პასუხები კომენტარებზე",
    toggle: "საკვანძო სიტყვიან კომენტარებზე პასუხი Direct-ში",
    description:
      "როცა ვინმე პოსტის ქვეშ კომენტარში თქვენს საკვანძო სიტყვას დაწერს, ასისტენტი მას Direct-ში ერთ შეტყობინებას გაუგზავნის. თითოეულ ადამიანს — დღეში არაუმეტეს ერთისა, საათში კი სულ არაუმეტეს 60-ისა.",
    unavailable: "კომენტარებზე პასუხები სერვისის შემდეგი განახლებიდან ამუშავდება. მანამდე პარამეტრები შენახულია.",
    summaryOn: "ჩართულია სიტყვებზე: {keywords}",
    summaryOff: "გამორთულია",
    keywords: "საკვანძო სიტყვები",
    keywordsHint: "სიტყვა ან მოკლე ფრაზა; თითოეულის შემდეგ დააჭირეთ Enter-ს. 20-მდე.",
    keywordInput: "ახალი საკვანძო სიტყვა",
    addKeyword: "დამატება",
    removeKeyword: "„{keyword}“-ის წაშლა",
    replyText: "შეტყობინება Direct-ში",
    replyHint: "1000 სიმბოლომდე. კლიენტს შეუძლია უპასუხოს და ასისტენტი საუბარს გააგრძელებს.",
    save: "შენახვა",
    saving: "ვინახავთ…",
    savedToast: "კომენტარებზე პასუხები შენახულია",
    errors: {
      keywordsMissing: "დაამატეთ ერთი საკვანძო სიტყვა მაინც",
      replyMissing: "დაწერეთ შეტყობინება",
      keyword: "50 სიმბოლომდე, ერთ სტრიქონში",
      tooMany: "არაუმეტეს 20 საკვანძო სიტყვისა",
    },
  },
  tunnel: {
    title: "WhatsApp, Instagram და Messenger",
    text: "დააკავშირეთ ისინი თქვენი Facebook ანგარიშით ახლავე ან მოგვიანებით, „არხების“ გვერდზე.",
    connect: "{channel}-ის დაკავშირება",
    connected: "დაკავშირებულია",
  },
};
