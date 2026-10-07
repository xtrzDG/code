/** `adminSpend.*` texts in Russian (typed against adminSpend.en.ts). */

import type { Translation } from "../../../translate";
import type { adminSpendEn } from "./adminSpend.en";

export const adminSpendRu: Translation<typeof adminSpendEn> = {
  title: "Расходы сегодня",
  description: "Сколько платформа должна провайдерам за {day} (UTC). Расходы, о которых провайдер ещё не сообщил, считаются по плановым ценам.",
  total: "Всего за сегодня",
  weekMean: "В среднем за день в предыдущие 7 дней: {amount}",
  spike: "Намного выше обычного",
  budget: "{percent}% дневного бюджета {amount}",
  budgetLabel: "Использовано дневного бюджета",
  noBudget: "Дневной бюджет не задан (PLATFORM_DAILY_SPEND_BUDGET_USD).",
  providersLabel: "Расходы по провайдерам",
  providers: {
    language_model: "Модель ИИ",
    voice: "Голосовой агент",
    telephony: "Телефонные звонки",
    whatsapp: "Шаблоны WhatsApp",
    transcription: "Расшифровка голосовых",
  },
  brakedTitle: "Клиенты, превысившие лимит расходов",
  brakedNone: "Сегодня ни один клиент не превысил лимит расходов.",
  levels: {
    soft_limit: "Модель дешевле",
    hard_limit: "Только заявки",
  },
  brakedLine: "{spend} из {limit}, с {time}",
};
