/** `dpaNotice.*` in German: a new data processing agreement (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { dpaNoticeEn } from "./dpaNotice.en";

export const dpaNoticeDe: Translation<typeof dpaNoticeEn> = {
  label: "Neuer Auftragsverarbeitungsvertrag",
  title: "Der Auftragsverarbeitungsvertrag hat eine neue Version ({version})",
  due: "Sie ersetzt die Version, die Sie akzeptiert haben. Lesen und akzeptieren Sie sie bis {date}: Um Änderungen am Assistenten zu übernehmen, ist die aktuelle Version nötig.",
  overdue:
    "Sie ersetzt die Version, die Sie akzeptiert haben, und war bis {date} fällig: Um Änderungen am Assistenten zu übernehmen, ist die aktuelle Version nötig. Lesen und akzeptieren Sie sie deshalb jetzt.",
  action: "Lesen und akzeptieren",
};
