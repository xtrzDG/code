import type { Translation } from "../../../translate";
import type { adminReplyGuardEn } from "./adminReplyGuard.en";

/** `adminReplyGuard.*` по-русски. */
export const adminReplyGuardRu: Translation<typeof adminReplyGuardEn> = {
  title: "Проверка ответов, 7 дней",
  description:
    "Ответы, которые проверка задержала, потому что цифр, утверждений или контактов не было в данных бизнеса, и сообщения, которые пытались подменить инструкцию помощника.",
  checked: "Проверено ответов",
  heldBack: "Задержано",
  heldBackShare: "{share} ответов",
  rewritten: "Переписано",
  handedOff: "Передано сотруднику",
  injectionFlags: "Попытки подмены инструкции",
  heldBackNote:
    "Проверка задержала каждый шестой ответ или чаще. Проверьте факты и цены бизнеса: помощнику не хватает того, о чём спрашивают клиенты.",
  probedNote:
    "Кто-то снова и снова пытается подменить инструкцию помощника. После трёх попыток контакт останавливается на сутки; посмотрите разговоры.",
  empty: "За последние 7 дней проверенных ответов нет.",
  issueLabel: "Всплеск проверок ответов",
};
