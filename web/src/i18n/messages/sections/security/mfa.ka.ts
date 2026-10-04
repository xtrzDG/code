/** `mfa.*` texts in Georgian: second step of sign-in, authenticator setup, recovery codes, confirmation. */

import type { Translation } from "../../../translate";
import type { mfaEn } from "./mfa.en";

export const mfaKa: Translation<typeof mfaEn> = {
  secondStep: {
    title: "ორსაფეხურიანი შესვლა",
    description:
      "გახსენით ავთენტიფიკატორის აპი და შეიყვანეთ 6-ციფრიანი კოდი, რომელსაც ის Assistant Workshop-ისთვის აჩვენებს.",
    code: "კოდი აპიდან",
    recoveryDescription:
      "შეიყვანეთ შენახული აღდგენის კოდებიდან ერთ-ერთი. თითოეული კოდი ერთხელ მუშაობს.",
    recoveryCode: "აღდგენის კოდი",
    recoveryHint: "12 ასო და ციფრი, მაგალითად {example}",
    useRecovery: "შესვლა აღდგენის კოდით",
    useApp: "შესვლა აპით",
    verify: "შესვლა",
    verifying: "ვამოწმებთ…",
    startOver: "თავიდან შესვლა",
  },
  enrollment: {
    title: "ჩართეთ ორსაფეხურიანი შესვლა",
    description:
      "პლატფორმის ადმინისტრატორები შესვლისას ავთენტიფიკატორის აპის კოდსაც იყენებენ. დააყენეთ ახლავე: ერთ წუთს წაიღებს, შემდეგ შესვლისას მხოლოდ კოდი დაგჭირდებათ.",
    start: "დაყენება",
    starting: "ვამზადებთ…",
  },
  setup: {
    title: "დააყენეთ ავთენტიფიკატორის აპი",
    stepInstall:
      "დააყენეთ ტელეფონზე ავთენტიფიკატორის აპი: Google Authenticator, Microsoft Authenticator, 1Password ან სხვა.",
    stepScan: "დაასკანერეთ ეს QR-კოდი აპით ან ხელით შეიყვანეთ გასაღები.",
    stepCode: "შეიყვანეთ 6-ციფრიანი კოდი, რომელსაც აპი აჩვენებს.",
    qrLabel: "QR-კოდი ავთენტიფიკატორის აპისთვის",
    key: "გასაღები",
    copyKey: "გასაღების კოპირება",
    keyCopied: "გასაღები დაკოპირდა",
    code: "კოდი აპიდან",
    confirm: "ჩართვა",
    confirming: "ვრთავთ…",
  },
  recovery: {
    title: "შეინახეთ აღდგენის კოდები",
    description:
      "თუ ტელეფონი დაიკარგება, შედით ამ კოდებიდან ერთ-ერთით აპის ნაცვლად. თითოეული კოდი ერთხელ მუშაობს. ისინი მხოლოდ ახლა ჩანს: შეინახეთ პაროლების მენეჯერში ან ამობეჭდეთ.",
    copy: "კოპირება",
    copied: "კოდები დაკოპირდა",
    download: "ჩამოტვირთვა",
    fileHeading:
      "Assistant Workshop-ის აღდგენის კოდები ანგარიშისთვის {account}. თითოეული კოდი ერთხელ მუშაობს.",
    saved: "კოდები უსაფრთხო ადგილას შევინახე",
    continue: "გაგრძელება",
  },
  stepUp: {
    title: "დაადასტურეთ, რომ ეს თქვენ ხართ",
    description: "ამ მოქმედებას ახალი დადასტურება სჭირდება.",
    totp: "შეიყვანეთ კოდი ავთენტიფიკატორის აპიდან.",
    loginCode: "კოდი გამოვგზავნეთ მისამართზე {destination}. შეიყვანეთ აქ.",
    sending: "კოდს ვაგზავნით…",
    code: "კოდი",
    confirm: "დადასტურება",
    confirming: "ვამოწმებთ…",
    resend: "ახალი კოდის გაგზავნა",
    confirmed: "დადასტურდა. ვასრულებთ.",
  },
  errors: {
    wrongCode: "კოდი არასწორია ან უკვე გამოყენებულია. სცადეთ უახლესი კოდი.",
    expired: "შესვლის დრო ამოიწურა. დაიწყეთ თავიდან.",
    tooManyAttempts: "ძალიან ბევრი არასწორი კოდი. შედით თავიდან.",
    stepUpRequired: "დაადასტურეთ, რომ ეს თქვენ ხართ: შეიყვანეთ კოდი.",
    mfaRequired: "აქ ავთენტიფიკატორის აპით შესვლაა საჭირო.",
    codeFormat: "შეიყვანეთ 6 ციფრი",
  },
};
