"use client";

/** One passkey in Account → Security: its name, dates and state, rename and remove. */

import type { PasskeyView } from "@/api/types";
import { IconKey } from "@/components/icons";
import { useViewerFormat } from "@/components/time/ViewerTimeZone";
import { Badge, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";

export function PasskeyRow({
  passkey,
  onRename,
  onRemove,
}: {
  passkey: PasskeyView;
  onRename: (passkey: PasskeyView) => void;
  onRemove: (passkey: PasskeyView) => void;
}) {
  const { t } = useI18n();
  const viewer = useViewerFormat();
  const details = [
    t("passkeys.addedOn", { date: viewer.date(passkey.created_at) }),
    passkey.last_used_at
      ? t("passkeys.lastUsed", { date: viewer.dateTime(passkey.last_used_at) })
      : t("passkeys.neverUsed"),
  ];

  return (
    <li className="flex flex-wrap items-start gap-3 py-4 first:pt-0 last:pb-0">
      <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-full bg-surface-muted text-ink-muted">
        <IconKey className="size-4" aria-hidden />
      </span>
      <div className="min-w-0 flex-1 space-y-1">
        <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
          <span className="break-words">{passkey.name}</span>
          {passkey.is_synced ? (
            <Badge tone="neutral">{t("passkeys.synced")}</Badge>
          ) : null}
        </p>
        <p className="text-sm text-ink-muted">{details.join(" · ")}</p>
        {passkey.clone_suspected_at ? (
          <p className="text-sm text-danger" role="note">
            {t("passkeys.suspended")}
          </p>
        ) : null}
      </div>
      <div className="flex shrink-0 gap-2">
        <Button
          variant="ghost"
          size="sm"
          aria-label={t("passkeys.renameLabel", { name: passkey.name })}
          onClick={() => onRename(passkey)}
        >
          {t("passkeys.rename")}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          aria-label={t("passkeys.removeLabel", { name: passkey.name })}
          onClick={() => onRemove(passkey)}
        >
          {t("passkeys.remove")}
        </Button>
      </div>
    </li>
  );
}
