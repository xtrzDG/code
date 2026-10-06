/** `billingLifecycle.*` texts of Settings → Billing: why owners cancel, the offers instead, the seasonal pause, in Russian. */

import type { Translation } from "../../../translate";
import type { billingLifecycleEn } from "./billingLifecycle.en";

export const billingLifecycleRu: Translation<typeof billingLifecycleEn> = {
  reasons: {
    too_expensive: "Слишком дорого",
    seasonal_break: "Мы закрываемся на межсезонье",
    not_enough_use: "Сейчас мало обращений от клиентов",
    missing_feature: "Не хватает нужной функции",
    answer_quality: "Ответы недостаточно хороши",
    switched_provider: "Переходим на другой сервис",
    closing_business: "Закрываем бизнес",
    somethingElse: "Другое",
  },
  cancel: {
    reasonLegend: "Какая главная причина?",
    reasonHint: "Это поможет нам стать лучше, а вам — возможно, найти вариант удобнее отмены.",
    detailsLabel: "Хотите что-то добавить?",
    detailsPlaceholder: "Своими словами",
    continue: "Продолжить",
    offerTitle: "Прежде чем уйти",
    cancelAnyway: "Нет, всё равно отменить",
    back: "Назад",
  },
  offerKinds: {
    pause: "Сезонная пауза",
    downgrade: "Тариф дешевле",
    credit: "Разовая скидка",
  },
  offers: {
    pause: {
      title: "Возьмите сезонную паузу вместо отмены",
      description:
        "Месяц паузы стоит {price}: помощник продолжает принимать заявки, каналы остаются подключены, а полный режим вернётся сам.",
      confirm: {
        one: "Пауза на {count} месяц",
        few: "Пауза на {count} месяца",
        many: "Пауза на {count} месяцев",
        other: "Пауза на {count} месяца",
      },
    },
    downgrade: {
      title: "Оставьте помощника дешевле",
      description:
        "«{plan}» стоит {price}. Ответы, каналы и настройки останутся как есть; новая цена — со следующего счёта.",
      confirm: "Перейти на «{plan}»",
    },
    credit: {
      title: "Останьтесь — {amount} за наш счёт",
      description: "Мы зачислим {amount} на ваш баланс — эта сумма вычтется из следующего счёта.",
      confirm: "Получить скидку",
    },
    taken: {
      pause: "Пауза запланирована",
      downgrade: "Тариф изменён",
      credit: "Скидка зачислена на баланс",
    },
  },
  pause: {
    title: "Сезонная пауза",
    description:
      "Закрываетесь на межсезонье? Поставьте паузу вместо отмены: помощник продолжит принимать заявки, каналы останутся подключены, а полный режим вернётся сам.",
    price: "{price} в месяц — {percent}% тарифа",
    monthsLegend: "На сколько",
    months: {
      one: "{count} месяц",
      few: "{count} месяца",
      many: "{count} месяцев",
      other: "{count} месяца",
    },
    window: "С {start} по {until}",
    submit: "Пауза с {date}",
    allowance: "На паузе было {used} из {cap} мес. за последние {window} мес.",
    scheduledTitle: "Пауза запланирована",
    scheduled:
      "С {start} по {until} помощник только принимает заявки. Автоплатежи выключены; оплата по полной цене начнётся снова после паузы.",
    callOff: "Отменить паузу",
    calledOff: "Пауза отменена",
    pausedTitle: "На паузе до {date}",
    paused:
      "Помощник только принимает заявки, каналы подключены. Каждый месяц паузы стоит {percent}% тарифа.",
    resume: "Вернуть полный режим",
    resumeTitle: "Вернуть полный режим сейчас?",
    resumeDescription:
      "Помощник снова отвечает клиентам и принимает записи. Если этот месяц паузы уже оплачен, полный режим вернётся в его конце; иначе — сейчас, и нужно будет оплатить следующий период.",
    resumed: "Полный режим возвращается",
    plansHint: "На паузе тариф не меняется; чтобы сменить его, верните полный режим.",
    unavailable: {
      not_active: "Пауза доступна для оплаченной помесячной подписки.",
      not_monthly: "Годовой тариф нельзя поставить на паузу.",
      allowance_used: "За последние 12 месяцев уже было 4 месяца паузы; поставить её снова можно будет позже.",
    },
  },
  facts: {
    pause: "Сезонная пауза",
  },
  errors: {
    offerGone: "Это предложение больше недоступно. Закройте окно и попробуйте снова.",
    pauseGone: "Сейчас поставить паузу нельзя. Обновите страницу, чтобы увидеть причину.",
  },
};
