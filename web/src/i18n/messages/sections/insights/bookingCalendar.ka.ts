/** `bookingCalendar.*`: the bookings calendar, in Georgian. */

import type { Translation } from "../../../translate";
import type { bookingCalendarEn } from "./bookingCalendar.en";

export const bookingCalendarKa: Translation<typeof bookingCalendarEn> = {
  views: {
    label: "ჯავშნების ჩვენება",
    list: "სია",
    day: "დღე",
    week: "კვირა",
    nights: "ღამეები",
  },
  toolbar: {
    label: "კალენდრის თარიღები",
    previous: { day: "წინა დღე", week: "წინა კვირა", nights: "ადრინდელი ღამეები" },
    next: { day: "შემდეგი დღე", week: "შემდეგი კვირა", nights: "მომდევნო ღამეები" },
    today: "დღეს",
    date: "თარიღი",
    includeTest: "სატესტო ჯავშნების ჩვენება",
  },
  loading: "კალენდარი იტვირთება…",
  truncated: "ამ პერიოდში იმაზე მეტი ჯავშანია, ვიდრე კალენდარი ერთად აჩვენებს. გახსენით უფრო მოკლე პერიოდი ან სია.",
  legend: "ჯავშნის სტატუსი",
  moveHint: "გადაათრიეთ ჯავშანი სხვა დროზე ან ადგილზე. ან აირჩიეთ და გადაიტანეთ ისრებით: Enter — გადატანა, Escape — გაუქმება.",
  day: {
    label: "{date}-ის ჯავშნები ადგილების მიხედვით",
    time: "დრო",
    closed: "დაკეტილია",
    closedDay: "მთელი დღე დაკეტილია",
    newAt: "ახალი ჯავშანი: {place}",
    newAtTime: "ახალი ჯავშანი: {place}, {time}",
    booked: "დაკავებულია {percent}",
    now: "ახლა {time}",
    noPlacesTitle: "დროით დასაჯავშნი ადგილები არ არის",
    noPlacesDescription: "დაამატეთ მაგიდები, ოსტატები ან დარბაზები, რომლებსაც დროით ჯავშნიან, და დღე თითოეულს ცალკე სვეტად აჩვენებს.",
    toPlaces: "ადგილების დამატება",
  },
  block: {
    label: "{name}, {time}, {place}, {status}",
    test: "ტესტი",
    moving: "გადაგვაქვს…",
  },
  move: {
    pending: "გადავიტანოთ: {place}, {time}? Enter — გადატანა, Escape — გაუქმება.",
    pendingStay: "გადავიტანოთ: {place}, {date}-დან? Enter — გადატანა, Escape — გაუქმება.",
    moved: "გადატანილია: {place}, {time}",
    movedStay: "გადატანილია: {place}, {date}-დან",
    undone: "ჯავშანი ძველ ადგილას დაბრუნდა",
    changed: "ეს ჯავშანი ახლახან სხვამ შეცვალა: კალენდარი მას ახლანდელი სახით აჩვენებს.",
    cancelled: "გადატანა გაუქმდა",
  },
  week: {
    label: "ადგილების დატვირთვა, {range}",
    place: "ადგილი",
    allPlaces: "ყველა ადგილი",
    closed: "დაკეტილია",
    free: "თავისუფალია",
    share: "დაკავებულია {percent}",
    rooms: { one: "დაკავებულია {booked} ნომერი {open}-დან", other: "დაკავებულია {booked} ნომერი {open}-დან" },
    cell: "{place}, {date}: {load}, {count}",
    legendTitle: "დატვირთვა",
    quiet: "თავისუფალი",
    full: "სავსე",
  },
  nights: {
    label: "ნომრები ღამეების მიხედვით, {range}",
    room: "ნომერი",
    taken: "დაკავებულია {booked} {open}-დან",
    newStay: "ახალი განთავსება: {place}, {date}-ის ღამე",
    noRoomsTitle: "ღამეებით დასაჯავშნი ნომრები არ არის",
    noRoomsDescription: "დაამატეთ ნომრები ან ნომრების ტიპები, რომლებსაც ღამეებით ჯავშნიან, და აქ თითოეული ცალკე რიგად გამოჩნდება.",
  },
};
