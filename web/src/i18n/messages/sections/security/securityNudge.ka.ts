/** `securityNudge.*` texts in Georgian: the owner's second-factor banner. */

import type { Translation } from "../../../translate";
import type { securityNudgeEn } from "./securityNudge.en";

export const securityNudgeKa: Translation<typeof securityNudgeEn> = {
  title: "დაიცავით კლიენტების მონაცემები: ჩართეთ მეორე ფაქტორი",
  description:
    "წვდომის გასაღებით ან ავთენტიფიკატორის აპით მოპარული შესვლის კოდი თქვენს კაბინეტს ვერ გახსნის.",
  teamGrew:
    "თქვენი გუნდი გაიზარდა: კლიენტების მონაცემებს მეტი ადამიანი ხედავს. ჩართეთ მეორე ფაქტორი.",
  action: "ჩართვა",
  dismiss: "ახლა არა",
  dismissLabel: "მეორე ფაქტორის შეხსენების დამალვა",
};
