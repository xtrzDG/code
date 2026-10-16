/**
 * `assistant.comparison.*` texts: an update's checks against the live
 * update's, in Georgian.
 */

import type { Translation } from "../../../translate";
import type { assistantComparisonEn } from "./assistantComparison.en";

export const assistantComparisonKa: Translation<typeof assistantComparisonEn> = {
  comparison: {
    title: "შედარება მოქმედ განახლება {number}-თან",
    description: "შედარდება მხოლოდ ის სცენარები, რომლებიც ორივე განახლებამ ითამაშა.",
    shared: "შედარებული სცენარები: {count}",
    averageScore: "საშუალო შეფასება",
    averageWas: "მოქმედი: {score}",
    newFailures: "ახალი პრობლემები",
    fixed: "გამოსწორდა",
    newFailuresHint: "ეს სცენარები მოქმედ განახლებაზე გადიოდა, ახლა კი არ გადის.",
    fixedHint: "ეს სცენარები მოქმედ განახლებაზე არ გადიოდა, ახლა კი გადის.",
    scoreDrops: "შეფასებები დაეცა",
    scoreRises: "შეფასებები გაიზარდა",
    criteria: "კრიტერიუმების მიხედვით",
    scenario: "{name} · {language}",
    scoreMove: "{from} → {to}",
    outcomeMove: "იყო: {from}, ახლა: {to}",
    noChanges: "მოქმედ განახლებასთან შედარებით არაფერი შეცვლილა: ახალი პრობლემები არ არის და არც ერთი შეფასება ნახევარი ქულით ან მეტით არ შეცვლილა.",
    noShared: "ამ გაშვებასა და მოქმედი განახლების გაშვებას ჯერ საერთო სცენარები არ აქვს.",
    plays: { one: "გავლილი გათამაშებები: {passed} / {played}", other: "გავლილი გათამაშებები: {passed} / {played}" },
    playsHint: "მნიშვნელოვანი სცენარები რამდენჯერმე თამაშდება და ყოველ ჯერზე უნდა გაიაროს.",
  },
};
