/** `securityNudge.*` texts in Russian: the owner's second-factor banner. */

import type { Translation } from "../../../translate";
import type { securityNudgeEn } from "./securityNudge.en";

export const securityNudgeRu: Translation<typeof securityNudgeEn> = {
  title: "Защитите данные клиентов: включите второй фактор",
  description:
    "С ключом доступа или приложением-аутентификатором украденного кода входа недостаточно, чтобы открыть ваш кабинет.",
  teamGrew:
    "Ваша команда выросла: данные клиентов видит больше людей. Включите второй фактор.",
  action: "Включить",
  dismiss: "Не сейчас",
};
