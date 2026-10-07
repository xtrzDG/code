/** `partnerPortal.*` texts of /partner, in Russian. */

import type { Translation } from "../../../translate";
import type { partnerPortalEn } from "./partnerPortal.en";

export const partnerPortalRu: Translation<typeof partnerPortalEn> = {
  title: "Кабинет партнёра",
  description: "Ваши ссылки, приведённые по ним бизнесы и ваш заработок.",
  rate: "Ваша комиссия: {rate} от каждого счёта, который оплачивают эти бизнесы, без налога.",
  paused: "Партнёрство приостановлено: новые оплаты не приносят комиссию, пока команда платформы его не возобновит.",
  legal: "Договор и способ выплат согласуются с командой платформы.",
  links: {
    title: "Ваши ссылки",
    description: "Сделайте ссылку для каждого места, где вы ею делитесь: метка покажет, откуда пришли регистрации.",
    none: "Кодов пока нет: их добавляет команда платформы.",
    source: "Где вы делитесь",
    sourcePlaceholder: "Instagram",
    sourceHint: "Необязательно. Латинские буквы, цифры, точки, дефисы и подчёркивания.",
    sourceInvalid: "Только латинские буквы, цифры, точки, дефисы и подчёркивания.",
    code: "Код",
    qrLabel: "QR-код ссылки с кодом {code}",
    showQr: "QR-код",
    hideQr: "Скрыть QR-код",
  },
  totals: {
    title: "Комиссии",
    businesses: "Приведено бизнесов",
    paying: "Уже оплатили",
    accrued: "К выплате",
    paid: "Выплачено",
  },
  businesses: {
    title: "Приведённые бизнесы",
    empty: "Пока никого. Поделитесь ссылкой, чтобы привести первый бизнес.",
    signedUp: "Регистрация",
    firstPaid: "Первая оплата",
    notYet: "Ещё нет",
    unnamed: "Бизнес",
  },
  commissions: {
    title: "Комиссия по счетам",
    empty: "Комиссий пока нет: они появятся, когда приведённый бизнес заплатит.",
    base: "Счёт без налога",
    status: "Статус",
    statuses: {
      accrued: "К выплате",
      paid: "Выплачено",
    },
  },
  showMore: "Показать ещё",
  loading: "Загрузка…",
};
