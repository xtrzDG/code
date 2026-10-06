/** `dataTasks.*` texts in Georgian (typed against dataTasks.en.ts). */

import type { Translation } from "../../../translate";
import type { dataTasksEn } from "./dataTasks.en";

export const dataTasksKa: Translation<typeof dataTasksEn> = {
  title: "მონაცემთა დავალებები გამოშვების შემდეგ",
  description:
    "დოკუმენტების ახალ ვერსიაზე გადატანა და საძიებო სვეტების შევსება, რომლებსაც პაკეტური ვორკერი თავად ასრულებს {size}-სტრიქონიან პაკეტებად. შემდეგი გამოშვება მხოლოდ მაშინ გადადის, როცა ყველა დავალება დასრულებულია.",
  open: {
    one: "{count} დავალება დაუსრულებელია",
    other: "{count} დავალება დაუსრულებელია",
  },
  allDone: "ყველა დავალება დასრულებულია",
  failed: "შეცდომით: {count}",
  stalled: "დღეზე მეტხანს გაჭედილი: {count}",
  settled: "სხვა გამოშვების ვორკერი არ მუშაობს: დავალებები სრულდება.",
  waiting: "ველოდებით {releases} გამოშვების ვორკერების გაჩერებას (დაახლოებით {time}).",
  waitingUnnamed: "ველოდებით უსახელო გამოშვების ვორკერების გაჩერებას (დაახლოებით {time}).",
  none: "ამ გამოშვებას მონაცემთა დავალებები არ აქვს.",
  openCaption: "დაუსრულებელი მონაცემთა დავალებები",
  doneCaption: "დასრულებული მონაცემთა დავალებები",
  showDone: {
    one: "{count} დასრულებული დავალების ჩვენება",
    other: "{count} დასრულებული დავალების ჩვენება",
  },
  hideDone: "დასრულებული დავალებების დამალვა",
  columns: {
    task: "დავალება",
    status: "მდგომარეობა",
    progress: "მსვლელობა",
    when: "როდის",
    actions: "მოქმედებები",
  },
  kinds: {
    migrate_documents: "დოკუმენტების გადაწერა {version} ვერსიაზე",
    backfill_lookup: "საძიებო სვეტის შევსება",
  },
  statuses: {
    pending: "ელოდება",
    running: "მიმდინარეობს",
    done: "დასრულდა",
    failed: "შეცდომა",
  },
  lists: {
    customers: "კლიენტების სია",
    knowledge: "ცოდნის სია",
  },
  holdsBack: "აფერხებს: {lists}",
  rows: "{scanned} დაახლოებით {estimate} სტრიქონიდან",
  rowsUnknown: "გადახედილი სტრიქონები: {scanned}",
  changed: "შეიცვალა: {count}, პაკეტები: {batches}",
  failedRows: "ვერ განახლდა სტრიქონები: {count} ({keys})",
  dueSince: "ელოდება {time}-დან",
  doneAt: "დასრულდა {time}",
  lastBatch: "ბოლო პაკეტი {time}",
  isStalled: "გაჭედილია",
  retry: "თავიდან გავლა",
  retried: "დავალება ცხრილს თავიდან გადის.",
  indexing: {
    title: "ჯერ კიდევ ინდექსირდება",
    body: "ბოლო გამოშვების შემდეგ მონაცემების განახლება ჯერ კიდევ მიმდინარეობს, ამიტომ რამდენიმე წუთის განმავლობაში ზოგიერთი ძველი ჩანაწერი შეიძლება სიაში არ ჩანდეს.",
  },
};
