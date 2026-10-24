/** `setupGuide.*`: the Overview's setup guide, the progress ring and the milestone toasts, in Russian. */

import type { Translation } from "../../../translate";
import type { setupGuideEn } from "./setupGuide.en";

export const setupGuideRu: Translation<typeof setupGuideEn> = {
  titleSetup: "Настройте помощника",
  titleLive: "Приведите первых клиентов",
  descriptionSetup: "Каждый шаг открывается там, где вы остановились. Помощник начнёт отвечать клиентам после публикации.",
  liveSince: "Отвечает клиентам с {date}",
  minutesLeft: {
    one: "осталось около {count} минуты",
    few: "осталось около {count} минут",
    many: "осталось около {count} минут",
    other: "осталось около {count} минуты",
  },
  continueSetup: "Продолжить настройку",
  afterLaunchHint: "После запуска: проверка с телефона, второй канал и ссылка для клиентов.",
  minutes: "{count} мин",
  optional: "по желанию",
  skip: "Пропустить",
  unskip: "Вернуть",
  skipLabel: "Пропустить «{step}»",
  unskipLabel: "Вернуть «{step}»",
  status: {
    next: "Следующий",
    skipped: "Пропущен",
  },
  phone: {
    description: "Наведите камеру телефона на код и напишите помощнику так, как написал бы клиент.",
    qrAlt: "QR-код ссылки {link}",
    copyLink: "Скопировать ссылку",
    unavailable: "Страница чата выключена. Включите чат на сайте в разделе «Каналы» или напишите с телефона в подключённый мессенджер.",
    orTelegram: "Или в Telegram:",
    listening: "Ждём ваше сообщение…",
    hint: "Шаг засчитается, когда придёт ваше сообщение.",
    success: "Работает: ваше сообщение дошло до помощника.",
    hide: "Скрыть",
  },
  finished: {
    title: "Всё готово",
    description: "Помощник отвечает клиентам, и они знают, где его найти.",
    dismiss: "Убрать карточку",
  },
  wins: {
    title: "Достигнуто",
    first_conversation: "Первый разговор с клиентом",
    first_booking: "Первая бронь",
    first_after_hours_booking: "Первая бронь в нерабочее время",
  },
  ring: {
    title: "Настройка",
    label: "Настройка выполнена на {percent}%",
    short: "{percent}%",
  },
  celebrations: {
    first_conversation: {
      title: "Написал первый клиент",
      description: "Помощник ответил. Разговор — во входящих.",
    },
    first_booking: {
      title: "Первая бронь",
      description: "Помощник сам записал клиента.",
    },
    first_after_hours_booking: {
      title: "Бронь, пока вы не работали",
      description: "Клиент записался в нерабочее время, и отвечать никому не пришлось.",
    },
    openInbox: "Открыть входящие",
    openBookings: "Открыть брони",
    close: "Закрыть",
  },
};
