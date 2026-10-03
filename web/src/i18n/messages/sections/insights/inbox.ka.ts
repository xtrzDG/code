/** `inbox.*` texts of the team inbox list, in Georgian. */

import type { Translation } from "../../../translate";
import type { inboxEn } from "./inbox.en";

export const inboxKa: Translation<typeof inboxEn> = {
  title: "შემოსული",
  viewsLabel: "რომელი საუბრები გამოჩნდეს",
  views: {
    needs_person: "ადამიანის დახმარება",
    requests: "მოთხოვნები",
    mine: "ჩემი",
    unassigned: "დაუნიშნავი",
    all: "ყველა",
  },
  viewCount: {
    one: "{count} საუბარი",
    other: "{count} საუბარი",
  },
  empty: {
    needs_person: {
      title: "ადამიანს არავინ ელოდება",
      description: "როცა ასისტენტი საუბარს თქვენს გუნდს გადასცემს, ის მაშინვე აქ გამოჩნდება.",
    },
    requests: {
      title: "ღია მოთხოვნები არ არის",
      description: "ბანკეტები, ჯგუფური ვიზიტები და სხვა მოთხოვნები, რომლებიც ასისტენტმა მიიღო, აქ ელოდება, სანამ ვინმე არ მიხედავს.",
    },
    mine: {
      title: "თქვენზე არაფერია დანიშნული",
      description: "საუბრები, რომლებიც თქვენ აიღეთ ან თქვენ დაგენიშნათ, აქ ელოდება, სანამ გუნდის ყურადღება სჭირდება.",
    },
    unassigned: {
      title: "ყველა საუბარს ჰყავს პასუხისმგებელი",
      description: "აქ ჩნდება საუბრები, რომლებსაც გუნდი სჭირდება, მაგრამ პასუხისმგებელი ჯერ არ ჰყავს.",
    },
    all: {
      title: "საუბრები ჯერ არ არის",
      description: "საუბრები აქ გამოჩნდება, როგორც კი კლიენტები ასისტენტს მისწერენ ან დაურეკავენ.",
    },
  },
  showAll: "ყველა საუბრის ნახვა",
  loading: "შემოსული იტვირთება…",
  listLabel: "საუბრები",
  searchLabel: "ძიება ყველა საუბარში",
  searchPlaceholder: "ძიება: სახელი, ტელეფონი ან ტექსტი",
  filters: {
    open: "ფილტრები",
    openWithCount: "ფილტრები ({count})",
    title: "ფილტრები",
    description: "პერიოდი, სტატუსი და სატესტო საუბრები ვრცელდება ყველა საუბარზე და ძიებაზე.",
    show: "საუბრების ჩვენება",
    clear: "ფილტრების გასუფთავება",
    includeTest: "სატესტო საუბრების ჩვენება",
  },
  results: "ნაპოვნია მოთხოვნით „{search}“",
  clearSearch: "ძიების გასუფთავება",
  row: {
    unassigned: "არავინაა დანიშნული",
    assignedTo: "პასუხისმგებელი: {name}",
    you: "თქვენ",
    notes: {
      one: "{count} შენიშვნა",
      other: "{count} შენიშვნა",
    },
    request: "მოთხოვნა: {type}",
    waiting: "ელოდება {time}-დან",
  },
  assign: {
    open: "დანიშვნა",
    menuLabel: "ვინ უძღვება ამ საუბარს",
    handledBy: "პასუხისმგებელი: {name}",
    handledByYou: "პასუხისმგებელი თქვენ ხართ",
    automatically: "ავტომატურად დაინიშნა",
    nobody: "პასუხისმგებელი ჯერ არ ჰყავს",
    takeIt: "ჩემზე აღება",
    unassign: "დანიშვნის მოხსნა",
    you: "თქვენ",
    teammate: "გუნდის წევრი",
    waiting: {
      one: "{count} ელოდება",
      other: "{count} ელოდება",
    },
    loading: "გუნდი იტვირთება…",
    assigned: "ახლა ამ საუბარს {name} უძღვება",
    taken: "ახლა ამ საუბარს თქვენ უძღვებით",
    cleared: "ახლა არავინაა დანიშნული",
    conflict: "ვიღაცამ ახლახან შეცვალა, ვინ უძღვება ამ საუბარს. გაჩვენებთ, როგორაა ახლა.",
    colleague: "ამ საუბარს კოლეგა უძღვება. სთხოვეთ მფლობელს, რომ თქვენ გადმოგცეთ.",
    notMember: "ეს ადამიანი გუნდში აღარ არის.",
  },
};
