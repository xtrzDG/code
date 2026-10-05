/** `privacyRetention.*` texts: Settings → Privacy → retention, in Russian. */

import type { Translation } from "../../../translate";
import type { privacyRetentionEn } from "./privacyRetention.en";

export const privacyRetentionRu: Translation<typeof privacyRetentionEn> = {
  title: "Сколько хранятся данные",
  description:
    "Данные клиентов удаляются автоматически, когда проходят эти сроки. Уведомление о конфиденциальности вашего чата называет клиентам те же сроки.",
  conversations: {
    label: "Разговоры",
    hint: "Считается от последнего сообщения разговора. Затем удаляются его сообщения, заметки команды, расшифровки и записи звонков; у бронирований, заявок и обращений остаётся только то, что не относится к личным данным.",
  },
  modelRecords: {
    label: "Записи обращений помощника к ИИ",
    hint: "Точный текст, отправленный модели ИИ, — хранится для проверки ответов. Удаляется у нас и в журнале качества (Langfuse). Не дольше 30 дней.",
  },
  periods: {
    days: { one: "{count} день", few: "{count} дня", many: "{count} дней", other: "{count} дня" },
    months: { one: "{count} месяц", few: "{count} месяца", many: "{count} месяцев", other: "{count} месяца" },
    years: { one: "{count} год", few: "{count} года", many: "{count} лет", other: "{count} года" },
    recommended: "{period} (рекомендуем)",
    maximum: "{period} (максимум)",
  },
  recordings: "Записи звонков хранятся {period}.",
  changeRecordings: "Изменить в разделе «Общие»",
  processorsTitle: "Копии у наших субподрядчиков",
  processors: {
    langfuse: "Langfuse: журнал обращений помощника к ИИ",
    elevenlabs: "ElevenLabs: телефонные звонки (запись и расшифровка)",
  },
  processorsDeleted: "удаляются вместе с нашими — по этим срокам и когда вы удаляете данные клиента:",
  processorsNone:
    "Langfuse и ElevenLabs на этой платформе не используются, поэтому копий данных ваших клиентов у них нет.",
  messagingApps:
    "Переписка в WhatsApp, Messenger, Instagram и Telegram остаётся в приложении клиента: удалить её там может только сам клиент.",
  lastCleanupTitle: "Последняя очистка",
  lastCleanup: "{date}",
  nothingDue: "Удалять было нечего.",
  noCleanupYet: "Первая очистка пройдёт этой ночью.",
  removed: {
    one: "Удалена {count} запись",
    few: "Удалено {count} записи",
    many: "Удалено {count} записей",
    other: "Удалено {count} записи",
  },
  counts: {
    deleted_messages: "сообщения",
    deleted_llm_turns: "записи обращений к ИИ",
    deleted_notes: "заметки команды",
    deleted_media: "файлы клиентов",
    deleted_missed_calls: "пропущенные звонки",
    erased_calls: "звонки",
    anonymized_leads: "заявки",
    anonymized_bookings: "бронирования",
    anonymized_handoffs: "обращения",
  },
  save: "Сохранить сроки",
  saved: "Сроки хранения сохранены",
  shorterTitle: "Удалить старые данные этой ночью?",
  shorterDescription:
    "С более короткими сроками ночная очистка безвозвратно удалит всё, что выходит за них (разговоры — {conversations}, записи обращений к ИИ — {modelRecords}). Отменить это нельзя.",
  shorterConfirm: "Сократить и удалить",
};
