/** `coachMarks.*` texts of the one-time tips on the Inbox, the Assistant and Channels, in Georgian. */

import type { Translation } from "../../../translate";
import type { coachMarksEn } from "./coachMarks.en";

export const coachMarksKa: Translation<typeof coachMarksEn> = {
  label: "მინიშნება",
  gotIt: "გასაგებია",
  readGuide: "ინსტრუქციის წაკითხვა",
  inbox: {
    title: "თქვენი გუნდის შემოსული",
    body: "ზემოთ არის საუბრები, სადაც ადამიანია საჭირო. გახსენით საუბარი, რომ უპასუხოთ, კოლეგას გადასცეთ ან დატოვოთ შენიშვნა, რომელსაც მხოლოდ გუნდი ხედავს.",
  },
  assistant: {
    title: "ჯერ აქ გამოსცადეთ ასისტენტი",
    body: "მისწერეთ ისე, როგორც კლიენტი მისწერდა. რასაც ასისტენტს ასწავლით, ჯერ აქ ჩანს, კლიენტები კი მოგვიანებით მიიღებენ.",
  },
  channels: {
    title: "დააკავშირეთ არხები, სადაც კლიენტები წერენ",
    body: "დაიწყეთ იმ არხით, რომელსაც კლიენტები ყველაზე ხშირად იყენებენ. ყოველ ბარათზე ჩანს, მუშაობს თუ არა არხი და როდის მოვიდა ბოლო შეტყობინება.",
  },
};
