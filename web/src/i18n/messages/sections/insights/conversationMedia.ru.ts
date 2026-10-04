/** `conversationMedia.*` in Russian (typed against the English reference). */

import type { Translation } from "../../../translate";
import type { conversationMediaEn } from "./conversationMedia.en";

export const conversationMediaRu: Translation<typeof conversationMediaEn> = {
  label: "Вложения",
  kinds: {
    audio: "Голосовое сообщение",
    image: "Фото",
    location: "Место",
    contact: "Контакт",
    sticker: "Стикер",
    file: "Файл",
  },
  voice: {
    title: "Голосовое сообщение",
    duration: "Голосовое сообщение, {duration}",
    transcript: "Расшифровка",
    noTranscript: "Расшифровки нет.",
    play: "Слушать",
    playLabel: "Прослушать голосовое сообщение",
    playerLabel: "Голосовое сообщение клиента",
    playerUnsupported: "Ваш браузер не может воспроизвести здесь аудио.",
    loading: "Загрузка…",
    missing: "Это голосовое сообщение больше недоступно: оно удалено по истечении срока хранения или вместе с данными клиента.",
    error: "Не удалось загрузить голосовое сообщение. Попробуйте через минуту.",
    retry: "Повторить",
  },
  photo: {
    alt: "Фото от клиента",
    altWithCaption: "Фото от клиента: {caption}",
    open: "Открыть фото",
    viewerTitle: "Фото от клиента",
    unavailable: "Фото не удалось показать: оно удалено или ваша сессия закончилась.",
  },
  place: {
    openMap: "Открыть на карте",
    openMapLabel: "Открыть {place} на карте (в новой вкладке)",
    unnamed: "Отправленное место",
  },
  deleted: "Файл удалён по истечении срока хранения.",
  problems: {
    unsupported_kind: "Помощник не умеет это читать и попросил клиента написать текстом.",
    too_large: "Файл слишком большой: клиента попросили написать текстом.",
    too_long: "Слишком длинное, чтобы распознать: клиента попросили написать текстом.",
    unavailable: "Мессенджер уже не отдаёт этот файл: клиента попросили написать текстом.",
    unrecognized_format: "Формат, который помощник не читает: клиента попросили написать текстом.",
    not_understood: "Слов разобрать не удалось: клиента попросили написать текстом.",
  },
  auditNote: "Прослушивание голосовых сообщений и просмотр фото записываются в журнал аудита.",
};
