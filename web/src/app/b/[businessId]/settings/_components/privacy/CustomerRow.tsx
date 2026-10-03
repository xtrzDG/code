"use client";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Badge, Button } from "@/components/ui";
import { CHANNEL_NAMES } from "@/components/workspace/channelNames";
import { IconDownload } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { listFormat } from "@/lib/intl/formatters";

import type { ContactSummary } from "../../_lib/customers";

/** One customer: name or "erased", phone, channels, counts and last activity; export and erase. */
export function CustomerRow({
  contact,
  name,
  isExporting,
  onExport,
  onErase,
}: {
  contact: ContactSummary;
  /** The name to show (name, else phone, else "unnamed"). */
  name: string;
  isExporting: boolean;
  onExport: () => void;
  onErase: () => void;
}) {
  const { t, tp, locale } = useI18n();
  const format = useBusinessFormat();
  const { isOwner } = useBusiness();
  const isErased = Boolean(contact.erased_at);
  const channels = (contact.channels ?? []).map((channel) => t(CHANNEL_NAMES[channel]));
  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
      <div className="min-w-0 flex-1 basis-56">
        <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
          {isErased ? (
            <span className="text-ink-muted">{t("settings.customers.erasedName")}</span>
          ) : (
            <span dir="auto" className="break-words">
              {name}
            </span>
          )}
          {isErased ? <Badge tone="neutral">{t("settings.customers.erased")}</Badge> : null}
          {!isErased && contact.is_phone_verified ? <Badge tone="success">{t("settings.customers.verifiedPhone")}</Badge> : null}
        </p>
        <p className="mt-0.5 text-xs text-ink-muted">
          {[
            contact.name && contact.phone_number ? contact.phone_number : null,
            channels.length > 0 ? listFormat(locale, { type: "unit" }).format(channels) : null,
            contact.conversation_count > 0 ? tp("settings.requests.conversations", contact.conversation_count) : null,
            contact.booking_count > 0 ? tp("settings.customers.bookings", contact.booking_count) : null,
            contact.lead_count > 0 ? tp("settings.customers.leads", contact.lead_count) : null,
            isErased && contact.erased_at
              ? t("settings.customers.erasedOn", { date: format.dateTime(contact.erased_at) })
              : t("settings.customers.lastActivity", { date: format.dateTime(contact.last_activity_at) }),
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
        <p className="mt-0.5 font-mono text-[11px] break-all text-ink-subtle">{contact.id}</p>
      </div>
      {isOwner && !isErased ? (
        <div className="flex flex-wrap gap-1">
          <Button
            variant="ghost"
            size="sm"
            leadingIcon={<IconDownload className="size-4" aria-hidden />}
            isLoading={isExporting}
            aria-label={t("settings.requests.exportLabel", { name })}
            onClick={onExport}
          >
            {t("settings.requests.export")}
          </Button>
          <Button
            variant="danger-ghost"
            size="sm"
            aria-label={t("settings.requests.deleteLabel", { name })}
            onClick={onErase}
          >
            {t("settings.requests.delete")}
          </Button>
        </div>
      ) : null}
    </li>
  );
}
