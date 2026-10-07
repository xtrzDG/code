/** `billingLifecycle.*` texts of Settings → Billing: why owners cancel, the offers instead, the seasonal pause, in Georgian. */

import type { Translation } from "../../../translate";
import type { billingLifecycleEn } from "./billingLifecycle.en";

export const billingLifecycleKa: Translation<typeof billingLifecycleEn> = {
  reasons: {
    too_expensive: "ძალიან ძვირია",
    seasonal_break: "სეზონის შემდეგ ვიხურებით",
    not_enough_use: "ახლა ცოტა კლიენტი გვწერს ან გვირეკავს",
    missing_feature: "საჭირო ფუნქცია აკლია",
    answer_quality: "პასუხები საკმარისად კარგი არ არის",
    switched_provider: "სხვა სერვისზე გადავდივართ",
    closing_business: "ბიზნესს ვხურავთ",
    somethingElse: "სხვა",
  },
  cancel: {
    reasonLegend: "რა არის მთავარი მიზეზი?",
    reasonHint: "ეს გაგვაუმჯობესებს, თქვენ კი შეიძლება გაუქმებაზე უკეთესი ვარიანტი იპოვოთ.",
    detailsLabel: "გსურთ რამის დამატება?",
    detailsPlaceholder: "საკუთარი სიტყვებით",
    continue: "გაგრძელება",
    offerTitle: "სანამ წახვალთ",
    cancelAnyway: "არა, მაინც გავაუქმოთ",
    back: "უკან",
  },
  offerKinds: {
    pause: "სეზონური პაუზა",
    downgrade: "უფრო იაფი ტარიფი",
    credit: "ერთჯერადი ფასდაკლება",
  },
  offers: {
    pause: {
      title: "გაუქმების ნაცვლად აიღეთ სეზონური პაუზა",
      description:
        "პაუზის ერთი თვე ღირს {price}: ასისტენტი მოთხოვნების მიღებას აგრძელებს, არხები ჩართული რჩება, სრული რეჟიმი კი თავად დაბრუნდება.",
      confirm: { one: "პაუზა {count} თვით", other: "პაუზა {count} თვით" },
    },
    downgrade: {
      title: "შეინარჩუნეთ ასისტენტი უფრო იაფად",
      description:
        "„{plan}“ ღირს {price}. პასუხები, არხები და პარამეტრები უცვლელი რჩება; ახალი ფასი შემდეგი ინვოისიდან მოქმედებს.",
      confirm: "„{plan}“-ზე გადასვლა",
    },
    credit: {
      title: "დარჩით და {amount} ჩვენზეა",
      description: "თქვენს ბალანსზე ჩავრიცხავთ {amount}-ს — ეს თანხა შემდეგ ინვოისს გამოაკლდება.",
      confirm: "ფასდაკლების მიღება",
    },
    taken: {
      pause: "პაუზა დაგეგმილია",
      downgrade: "ტარიფი შეიცვალა",
      credit: "ფასდაკლება ჩაირიცხა ბალანსზე",
    },
  },
  pause: {
    title: "სეზონური პაუზა",
    description:
      "სეზონის შემდეგ იხურებით? გაუქმების ნაცვლად დააპაუზეთ: ასისტენტი მოთხოვნებს მიიღებს, არხები ჩართული დარჩება, სრული რეჟიმი კი თავად დაბრუნდება.",
    price: "{price} თვეში — ტარიფის {percent}%",
    monthsLegend: "რამდენი ხნით",
    months: { one: "{count} თვე", other: "{count} თვე" },
    window: "{start}-დან {until}-მდე",
    submit: "პაუზა {date}-დან",
    allowance: "{window} პაუზაზე იყო {months}.",
    allowanceMonths: { one: "{used} თვე {cap}-დან", other: "{used} თვე {cap}-დან" },
    allowanceWindow: { one: "ბოლო {window} თვეში", other: "ბოლო {window} თვეში" },
    scheduledTitle: "პაუზა დაგეგმილია",
    scheduled:
      "{start}-დან {until}-მდე ასისტენტი მხოლოდ მოთხოვნებს იღებს. ავტომატური გადახდები გამორთულია; სრული ფასით გადახდა პაუზის შემდეგ განახლდება.",
    callOff: "პაუზის გაუქმება",
    calledOff: "პაუზა გაუქმდა",
    pausedTitle: "პაუზაზეა {date}-მდე",
    paused:
      "ასისტენტი მხოლოდ მოთხოვნებს იღებს, არხები ჩართულია. პაუზის ყოველი თვე ტარიფის {percent}% ღირს.",
    resume: "სრული რეჟიმის დაბრუნება",
    resumeTitle: "დავაბრუნოთ სრული რეჟიმი ახლავე?",
    resumeDescription:
      "ასისტენტი კვლავ პასუხობს კლიენტებს და იღებს ჯავშნებს. თუ პაუზის ეს თვე უკვე გადახდილია, სრული რეჟიმი მის ბოლოს დაბრუნდება; თუ არა — ახლავე, და შემდეგი პერიოდის გადახდა მოგიწევთ.",
    resumed: "სრული რეჟიმი ბრუნდება",
    plansHint: "პაუზისას ტარიფი არ იცვლება; შესაცვლელად დააბრუნეთ სრული რეჟიმი.",
    unavailable: {
      not_active: "პაუზა შესაძლებელია გადახდილი ყოველთვიური გამოწერისთვის.",
      not_monthly: "წლიური ტარიფის დაპაუზება შეუძლებელია.",
      allowance_used: "ბოლო 12 თვეში 4 თვის პაუზა უკვე გამოყენებულია; ხელახლა დაპაუზება მოგვიანებით შეგეძლებათ.",
    },
  },
  facts: {
    pause: "სეზონური პაუზა",
  },
  errors: {
    offerGone: "ეს შეთავაზება აღარ არის ხელმისაწვდომი. დახურეთ ფანჯარა და სცადეთ ხელახლა.",
    pauseGone: "ახლა დაპაუზება შეუძლებელია. მიზეზის სანახავად განაახლეთ გვერდი.",
  },
};
