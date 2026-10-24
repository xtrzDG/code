/**
 * `quality.*` texts of production quality: the nightly judge's scores of
 * real conversations on the admin client page and on a conversation's
 * card, in Georgian.
 */

import type { Translation } from "../../../translate";
import type { qualityEn } from "./quality.en";

export const qualityKa: Translation<typeof qualityEn> = {
  admin: {
    title: "საუბრების ხარისხი, 30 დღე",
    description: "ყოველ ღამე AI-მსაჯი რეალური საუბრების მცირე შერჩევას შემოწმების ხუთი კრიტერიუმით აფასებს. მხოლოდ შეფასებები, კლიენტების ტექსტის გარეშე.",
    empty: "ბოლო 30 დღეში არც ერთი საუბარი არ შეფასებულა.",
    average: "საშუალო, 30 დღე",
    lastWeek: "ბოლო 7 დღე",
    previousWeek: "მანამდე 7 დღე: {score}",
    judged: "შეფასებული საუბრები",
    dropping: "{percent}%-ით დაბლა",
    droppingNote: "ბოლო კვირა წინაზე {percent}%-ით დაბლა შეფასდა. ნახეთ ქვემოთ ყველაზე დაბალი საუბრები და კლიენტის ბოლო განახლება.",
    scoreValue: "{score} / 5",
    trendLabel: "საშუალო შეფასება დღეების მიხედვით, ბოლო 30 დღე",
    noScoresDay: "{date}: არ შეფასებულა",
    dayValue: "{date}: {score} / 5, საუბრები: {count}",
    showTable: "ცხრილად ჩვენება",
    day: "დღე",
    count: "შეფასდა",
    lowestTitle: "ყველაზე დაბალი შეფასების საუბრები",
    lowestCaption: "30 დღის ხუთი ყველაზე დაბალი შეფასება",
    judgedAt: "შეფასდა",
    channel: "არხი",
    language: "ენა",
    score: "შეფასება",
    weak: "სუსტი მხარეები",
    noWeak: "4-ზე დაბალი არ არის",
  },
  conversation: {
    title: "AI-მსაჯის შეფასება",
    description: "ეს საუბარი ღამის ხარისხის შერჩევაში მოხვდა.",
    judgedAt: "შეფასდა {date}",
    notes: "შენიშვნები",
  },
};
