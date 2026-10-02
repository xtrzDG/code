/** `setup.*` texts: "Create an AI assistant", before the assistant exists, in Georgian. */

import type { Translation } from "../../../translate";
import type { setupEn } from "./setup.en";

export const setupKa: Translation<typeof setupEn> = {
  navEntry: "AI ასისტენტის შექმნა",
  navEntryHint: "ნაბიჯ-ნაბიჯ, დაახლოებით 10 წუთი",
  eyebrow: "{business}",
  title: "მოდით, შევქმნათ თქვენი AI ასისტენტი",
  description:
    "მოგვიყევით თქვენს ბიზნესზე რამდენიმე მარტივ ნაბიჯში. ჩვენ ავაწყობთ ასისტენტს, რომელიც დღე და ღამე უპასუხებს კლიენტებს, მიიღებს ჯავშნებს და დაგიძახებთ, როცა ადამიანია საჭირო.",
  start: "AI ასისტენტის შექმნა",
  continue: "შექმნის გაგრძელება",
  progress: "დასრულებულია {done} ნაბიჯი {total}-დან",
  duration: "დაახლოებით 10 წუთი. შეგიძლიათ ნებისმიერ დროს შეჩერდეთ და დაბრუნდეთ.",
  stagesLabel: "როგორ მიმდინარეობს",
  stages: {
    business: {
      title: "მოგვიყევით ბიზნესზე",
      description: "კონტაქტები, სამუშაო საათები და თქვენი შეთავაზება.",
    },
    rules: {
      title: "ასწავლეთ თქვენი წესები",
      description: "ჯავშნები, პასუხები ხშირ კითხვებზე და როდის დაგიძახოთ.",
    },
    meet: {
      title: "გაიცანით თქვენი ასისტენტი",
      description: "გამოსცადეთ ჩატში, შემდეგ ჩართეთ კლიენტებისთვის.",
    },
  },
  staffTitle: "ასისტენტი იქმნება",
  staffDescription:
    "„{business}“-ის მფლობელი მას აწყობს. საუბრები, ჯავშნები და მოთხოვნები აქ გამოჩნდება, როგორც კი ასისტენტი მზად იქნება.",
  create: "ჩემი ასისტენტის შექმნა",
};
