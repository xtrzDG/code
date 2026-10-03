"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconSend, IconTelegram } from "@/components/icons";
import { Badge, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import { formatContactAddress } from "@/lib/phone";

import type { ManagerContact } from "../../_lib/contacts";
import { isEverything, preferencesSummary, type NotificationContact } from "../../_lib/notifications";
import { CHANNEL_LABELS } from "./contactTexts";
import { DeliveryLine } from "./DeliveryLine";

/**
 * One staff contact: name, address (a Telegram chat by its @username,
 * never its chat id), channel, language and choices; how notifications reach it; and
 * for owners "Send a test", edit and remove.
 */
export function ContactRow({
  contact,
  status,
  isChecking,
  onTest,
  onEdit,
  onRemove,
}: {
  contact: ManagerContact;
  status: NotificationContact | undefined;
  isChecking: boolean;
  onTest: (status: NotificationContact) => void;
  onEdit: () => void;
  onRemove: () => void;
}) {
  const { t, locale } = useI18n();
  const { isOwner } = useBusiness();
  const username = status?.telegram_username ?? contact.telegram_username ?? null;
  return (
    <li className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-start sm:px-6">
      <div className="min-w-0 flex-1 space-y-2">
        <div>
          <p className="text-sm font-medium text-ink" dir="auto">
            {contact.name}
          </p>
          {contact.channel === "telegram" ? (
            // A Telegram chat is shown by its @username, never by its chat id.
            <p className="mt-0.5 flex min-w-0 items-center gap-1.5 text-sm text-ink-muted">
              <IconTelegram className="size-3.5 shrink-0" aria-hidden />
              <span className="truncate" dir={username ? "ltr" : "auto"}>
                {username ? t("notifications.contacts.telegramLinked", { username }) : t("notifications.contacts.telegramChat")}
              </span>
            </p>
          ) : (
            <p className="mt-0.5 truncate text-sm text-ink-subtle" dir="ltr">
              {formatContactAddress(contact.channel, contact.address)}
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone="accent">{t(CHANNEL_LABELS[contact.channel])}</Badge>
          <Badge>{languageName(contact.language, locale)}</Badge>
          {!isEverything(contact.preferences) ? <Badge tone="info">{preferencesSummary(t, contact.preferences)}</Badge> : null}
        </div>
        {status ? <DeliveryLine status={status} /> : null}
      </div>
      {isOwner ? (
        <div className="flex shrink-0 flex-wrap items-center gap-1 sm:justify-end">
          {status ? (
            <Button
              variant="secondary"
              size="sm"
              leadingIcon={<IconSend className="size-4" aria-hidden />}
              aria-label={t("notifications.contacts.testLabel", { name: contact.name })}
              isLoading={isChecking}
              onClick={() => onTest(status)}
            >
              {t("notifications.contacts.test")}
            </Button>
          ) : null}
          <Button variant="ghost" size="sm" aria-label={t("settings.contacts.editLabel", { name: contact.name })} onClick={onEdit}>
            {t("settings.contacts.edit")}
          </Button>
          <Button
            variant="danger-ghost"
            size="sm"
            aria-label={t("settings.contacts.removeLabel", { name: contact.name })}
            onClick={onRemove}
          >
            {t("settings.contacts.remove")}
          </Button>
        </div>
      ) : null}
    </li>
  );
}
