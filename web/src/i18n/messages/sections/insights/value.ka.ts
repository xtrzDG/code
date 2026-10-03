/** `value.*` texts: ასისტენტის ღირებულება მიმოხილვაზე, საშუალო ჩეკი, ცვლილებები და თანამშრომლის დღის რიგი, ქართულად. */

import type { Translation } from "../../../translate";
import type { valueEn } from "./value.en";

export const valueKa: Translation<typeof valueEn> = {
  hero: {
    title: "რა გააკეთა ასისტენტმა",
    reports: "ანგარიშები",
    bookingsLabel: "ასისტენტის გაკეთებული ჯავშნები",
    requestsLabel: "ასისტენტის მიღებული მოთხოვნები",
    bookingsHint: "საუბრებში გაკეთებული და გაუუქმებელი",
    requestsHint: "მის მიერ ჩაწერილი შეკვეთები და მოთხოვნები",
    formula: "{count} × საშუალო ჩეკი {check}",
    noMoney: "მიუთითეთ საშუალო ჩეკი, რომ ნახოთ, რა ღირს ეს.",
    afterHours: { one: "{count} არასამუშაო საათებში", other: "{count} არასამუშაო საათებში" },
    afterHoursHint: "საუბრები, როცა დაკეტილი იყავით",
    hoursSaved: { one: "დაზოგილია თანამშრომლების ~{count} საათი", other: "დაზოგილია თანამშრომლების ~{count} საათი" },
    minutesSaved: { one: "დაზოგილია თანამშრომლების ~{count} წუთი", other: "დაზოგილია თანამშრომლების ~{count} წუთი" },
    savedHint: "თქვენ ნაცვლად დაწერილი პასუხები: {replies}, მიღებული ზარები: {calls}",
    conversations: { one: "{count} საუბარი", other: "{count} საუბარი" },
    conversationsHint: "კლიენტები, რომლებმაც მოგწერეს ან დაგირეკეს",
  },
  check: {
    owner: "საშუალო ჩეკი {money}",
    typical: "საშუალო ჩეკი {money}, ტიპური თქვენი ტიპის ბიზნესისთვის",
    none: "საშუალო ჩეკი არ არის მითითებული, ამიტომ ფულადი შეფასება არ არის",
    set: "საშუალო ჩეკის მითითება",
    change: "შეცვლა",
    inputLabel: "საშუალო ჩეკი, {currency}",
    useTypical: "ტიპური {money}-ის დაბრუნება",
    saved: "საშუალო ჩეკი შენახულია",
    cleared: "ისევ ტიპური ჩეკი გამოიყენება",
    positive: "შეიყვანეთ ნულზე მეტი თანხა.",
    hint: "რამდენს მოაქვს საშუალოდ ერთ ჯავშანს. მისით ჯავშნები ფულად გადაიანგარიშება; მოგვიანებით მას თქვენი მომსახურების რეალური ფასები ჩაანაცვლებს.",
  },
  delta: {
    firstPeriod: "პირველი პერიოდი",
    firstPeriodHint: "წინა პერიოდში აქტივობა არ ყოფილა: შესადარებელი ჯერ არაფერია",
    up: "ზრდა {change} — {against}",
    down: "კლება {change} — {against}",
    same: "უცვლელი — {against}",
    againstDay: "წინა დღესთან შედარებით",
    againstDays: { one: "წინა {count} დღესთან შედარებით", other: "წინა {count} დღესთან შედარებით" },
  },
  queue: {
    title: "თქვენი დღევანდელი რიგი",
    mine: "თქვენზე მიბმული",
    mineHint: "საუბრები, რომლებსაც თქვენ უძღვებით",
    requests: "ახალი მოთხოვნები",
    requestsHint: "მოთხოვნები, რომლებიც ჯერ არავის დაუმუშავებია",
    bookings: "დღევანდელი ჯავშნები",
    bookingsHint: "ჯერ წინაა: {upcoming} · დასადასტურებელია: {unconfirmed}",
    bookingsLoading: "დღევანდელი ჯავშნები",
  },
};
