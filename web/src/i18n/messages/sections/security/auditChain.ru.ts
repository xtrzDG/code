/** `auditChain.*` по-русски: проверка журнала действий на подмену. */

import type { Translation } from "../../../translate";
import type { auditChainEn } from "./auditChain.en";

export const auditChainRu: Translation<typeof auditChainEn> = {
  title: "Проверка на подмену",
  status: {
    unchecked: "Ещё не проверен",
    intact: "Не изменён",
    broken: "Изменён",
  },
  verdict: {
    unchecked: "Каждая запись скреплена с предыдущей. Первая ежедневная проверка пройдёт в течение суток.",
    intact: "Каждая запись скреплена с предыдущей, и ежедневная проверка нашла все записи такими, какими они были записаны.",
    broken: "Ежедневная проверка нашла запись {position} не такой, какой она была записана: {problem}. Команда платформы уже получила тревогу.",
  },
  problems: {
    hash_mismatch: "её изменили",
    link_broken: "запись перед ней изменили, удалили или добавили",
    position_gap: "запись перед ней удалили",
    head_lost: "последние записи обрезали или переписали",
    checkpoint_mismatch: "записи, удалённые по сроку хранения, снова на месте",
  },
  checkedAt: "Проверено {when}",
  verifiedThrough: "Проверено до записи {position}",
  purgedThrough: "Записи до {position} удалены по сроку хранения",
};
