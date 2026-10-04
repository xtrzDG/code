/** `messageDelivery.*` in Russian (typed against the English reference). */

import type { Translation } from "../../../translate";
import type { messageDeliveryEn } from "./messageDelivery.en";

export const messageDeliveryRu: Translation<typeof messageDeliveryEn> = {
  label: "Доставка",
  states: {
    sending: "Отправляется…",
    retrying: "Пока не доставлено, пробуем ещё раз",
    delivered: "Доставлено",
    failed: "Не доставлено",
  },
  nextAttempt: "следующая попытка в {time}",
  reasons: {
    rate_limited: "мессенджер попросил подождать",
    provider_unavailable: "мессенджер не ответил",
    recipient_refused: "мессенджер не принял сообщение (клиент мог заблокировать бизнес, или 24-часовое окно закрылось)",
    template_rejected: "WhatsApp не принял шаблон сообщения",
    channel_disconnected: "канал больше не подключён",
    credential_rejected: "доступ канала перестал работать: подключите его заново в разделе «Каналы»",
    not_configured: "это сообщение нечем отправить",
    expired: "время для него прошло, прежде чем его удалось отправить",
  },
};
