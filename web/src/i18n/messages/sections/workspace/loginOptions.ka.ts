/** `loginOptions.*` texts of the sign-in code channels, in Georgian. */

import type { Translation } from "../../../translate";
import type { loginOptionsEn } from "./loginOptions.en";

export const loginOptionsKa: Translation<typeof loginOptionsEn> = {
  channelLabel: "კოდის გამოგზავნა",
  noPhoneChannels: "ამ ქვეყნის ნომრებზე შესვლის კოდის გაგზავნა ახლა შეუძლებელია.",
  useEmail: "შესვლა ელფოსტით",
  nothingAvailable: "შესვლა დროებით მიუწვდომელია: კოდის მიწოდების საშუალება ჯერ არ არის. სცადეთ მოგვიანებით.",
  restricted: "ამ ქვეყანაში რეგისტრაცია ჯერ მიუწვდომელია.",
};
