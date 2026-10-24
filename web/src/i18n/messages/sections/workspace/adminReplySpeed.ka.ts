/** `adminReplySpeed.*` texts of the reply-speed card on the admin's client page, in Georgian. */

import type { Translation } from "../../../translate";
import type { adminReplySpeedEn } from "./adminReplySpeed.en";

export const adminReplySpeedKa: Translation<typeof adminReplySpeedEn> = {
  title: "პასუხის სისწრაფე, 7 დღე",
  description: "რამდენ ხანს ელოდნენ მომხმარებლები — პირველი უპასუხო შეტყობინებიდან ასისტენტის პასუხამდე.",
  median: "ჩვეულებრივ (მედიანა)",
  p95: "20-დან 19 პასუხი ამაზე სწრაფად",
  replies: "გაზომილი პასუხები",
  slowNote: "ყოველი ოცი პასუხიდან ერთზე მეტი 15 წამზე დიდხანს გაგრძელდა. შეამოწმეთ მოდელის პროვაიდერი და ბიზნესის ინსტრუმენტები.",
  empty: "ბოლო 7 დღეში გაზომილი პასუხი არ არის. ჩატები ამ ვერსიიდან იზომება; ზარები და სატესტო ჩატი — არა.",
  tableCaption: "პასუხის სისწრაფე არხების მიხედვით",
  channel: "არხი",
  channelReplies: "პასუხები",
  channelMedian: "მედიანა",
  channelP95: "95%",
  seconds: "{value} წმ",
  minutes: "{value} წთ",
  issueLabel: "ნელი პასუხები",
};
