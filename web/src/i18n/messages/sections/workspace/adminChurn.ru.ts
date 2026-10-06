/** `adminChurn.*` texts of the platform admin's Metrics page, in Russian. */

import type { Translation } from "../../../translate";
import type { adminChurnEn } from "./adminChurn.en";

export const adminChurnRu: Translation<typeof adminChurnEn> = {
  title: "Почему владельцы уходят",
  description:
    "Отмены за период по причине, которую выбрал владелец, принятые вместо отмены предложения, сезонные паузы и сообщения через 14 и 30 дней после отмены.",
  empty: "За этот период нет отмен, предложений и пауз.",
  stats: {
    cancellations: "Отменили",
    saved: "Остались с предложением",
    pausesScheduled: "Пауз запланировано",
    pausesEnded: "Пауз завершилось",
    winBackSent: "Сообщений о возвращении",
    returned: "Вернулись после него",
  },
  reason: "Причина",
  cancelled: "Отменили",
  tookOffer: "Приняли предложение",
  noReason: "Не спрашивали (до вопроса)",
  offersTitle: "Принятые предложения",
  commentsTitle: "Словами владельцев",
  openClient: "Открыть клиента",
};
