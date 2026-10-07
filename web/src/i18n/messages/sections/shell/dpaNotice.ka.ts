/** `dpaNotice.*` ქართულად (იხ. dpaNotice.en.ts). */

import type { Translation } from "../../../translate";
import type { dpaNoticeEn } from "./dpaNotice.en";

export const dpaNoticeKa: Translation<typeof dpaNoticeEn> = {
  label: "მონაცემთა დამუშავების ახალი შეთანხმება",
  title: "მონაცემთა დამუშავების შეთანხმების ახალი ვერსია ({version})",
  due: "ის ცვლის თქვენ მიერ მიღებულ ვერსიას. წაიკითხეთ და მიიღეთ {date}-მდე: ასისტენტის ცვლილებების გამოსაყენებლად მიმდინარე ვერსიაა საჭირო.",
  overdue:
    "ის ცვლის თქვენ მიერ მიღებულ ვერსიას და მისი მიღების ვადა {date} იყო. ასისტენტის ცვლილებების გამოსაყენებლად მიმდინარე ვერსიაა საჭირო — წაიკითხეთ და მიიღეთ ახლავე.",
  action: "წაკითხვა და მიღება",
};
