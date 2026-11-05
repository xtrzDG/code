"use client";

/** The inbox's keyboard shortcuts ("?"): each key with what it does, and what "Resolved" changes. */

import { Modal } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { SHORTCUT_KEYS } from "../../_lib/inboxShortcuts";

export function ShortcutsSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useI18n();
  return (
    <Modal open={open} onClose={onClose} title={t("inboxTriage.keys.title")} description={t("inboxTriage.keys.description")} size="sm">
      <dl className="divide-y divide-line">
        {SHORTCUT_KEYS.map(({ keys, action }) => (
          <div key={action} className="flex items-center justify-between gap-4 py-2.5">
            <dt className="text-sm text-ink">{t(`inboxTriage.keys.actions.${action}`)}</dt>
            <dd className="flex shrink-0 gap-1">
              {keys.map((key) => (
                <kbd
                  key={key}
                  className="min-w-7 rounded-md border border-line-strong bg-surface-muted px-1.5 py-0.5 text-center font-mono text-xs text-ink"
                >
                  {key}
                </kbd>
              ))}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-sm text-ink-muted">{t("inboxTriage.keys.resolveNote")}</p>
    </Modal>
  );
}
