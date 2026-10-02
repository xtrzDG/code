"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { Badge, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";

import type { ManagerContact } from "../../_lib/contacts";
import { CHANNEL_LABELS } from "./contactTexts";

/** One manager contact: name, address, channel and language; edit and remove for owners. */
export function ContactRow({ contact, onEdit, onRemove }: { contact: ManagerContact; onEdit: () => void; onRemove: () => void }) {
  const { t, locale } = useI18n();
  const { isOwner } = useBusiness();
  return (
    <li className="flex items-start gap-3 px-5 py-4 sm:px-6">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-ink" dir="auto">
          {contact.name}
        </p>
        <p className="mt-0.5 truncate text-sm text-ink-muted" dir="ltr">
          {contact.address}
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          <Badge tone="accent">{t(CHANNEL_LABELS[contact.channel])}</Badge>
          <Badge>{languageName(contact.language, locale)}</Badge>
        </div>
      </div>
      {isOwner ? (
        <div className="flex shrink-0 flex-col items-end gap-1 sm:flex-row">
          <Button
            variant="ghost"
            size="sm"
            aria-label={t("settings.contacts.editLabel", { name: contact.name })}
            onClick={onEdit}
          >
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
