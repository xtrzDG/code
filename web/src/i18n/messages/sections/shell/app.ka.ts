/** `app.*` texts: the installed app and the page shown without a connection, in Georgian. */

import type { Translation } from "../../../translate";
import type { appEn } from "./app.en";

export const appKa: Translation<typeof appEn> = {
  shortName: "ასისტენტები",
  offlineTitle: "ინტერნეტთან კავშირი არ არის",
  offlineDescription: "კაბინეტს ინტერნეტი სჭირდება. ის ისევ გაიხსნება, როგორც კი კავშირი აღდგება.",
  offlineRetry: "ხელახლა ცდა",
};
