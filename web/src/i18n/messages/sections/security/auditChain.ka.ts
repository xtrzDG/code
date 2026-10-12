/** `auditChain.*` ქართულად: ქმედებების ჟურნალის შემოწმება ცვლილებაზე. */

import type { Translation } from "../../../translate";
import type { auditChainEn } from "./auditChain.en";

export const auditChainKa: Translation<typeof auditChainEn> = {
  title: "ცვლილების შემოწმება",
  status: {
    unchecked: "ჯერ არ შემოწმებულა",
    intact: "ხელუხლებელია",
    broken: "შეცვლილია",
  },
  verdict: {
    unchecked: "ყოველი ჩანაწერი წინასთანაა დაკავშირებული. პირველი ყოველდღიური შემოწმება ერთი დღის განმავლობაში ჩატარდება.",
    intact: "ყოველი ჩანაწერი წინასთანაა დაკავშირებული და ყოველდღიურმა შემოწმებამ ყველა ჩანაწერი ისეთივე იპოვა, როგორიც ჩაიწერა.",
    broken: "ყოველდღიურმა შემოწმებამ ჩანაწერი {position} ისეთი ვერ იპოვა, როგორიც ჩაიწერა: {problem}. პლატფორმის გუნდმა უკვე მიიღო შეტყობინება.",
  },
  problems: {
    hash_mismatch: "ის შეცვალეს",
    link_broken: "მის წინა ჩანაწერი შეცვალეს, წაშალეს ან დაამატეს",
    position_gap: "მის წინა ჩანაწერი წაშალეს",
    head_lost: "ბოლო ჩანაწერები მოჭრეს ან გადაწერეს",
    checkpoint_mismatch: "შენახვის ვადის გასვლის შემდეგ წაშლილი ჩანაწერები ისევ ადგილზეა",
  },
  checkedAt: "შემოწმდა {when}",
  verifiedThrough: "შემოწმებულია ჩანაწერ {position}-მდე",
  purgedThrough: "ჩანაწერები {position}-მდე წაიშალა შენახვის ვადის გასვლის შემდეგ",
};
