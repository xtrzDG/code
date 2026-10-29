"use client";

import { IconChat } from "@/components/icons";
import { EmptyState } from "@/components/ui";
import { useI18n } from "@/i18n/client";

/** The conversation column before one is chosen (large screens; phones show the list instead). */
export function NoConversationSelected() {
  const { t } = useI18n();
  return (
    <div className="flex h-full min-h-80 items-center justify-center rounded-2xl border border-dashed border-line bg-[radial-gradient(ellipse_at_center,color-mix(in_oklab,var(--accent-solid)_9%,transparent),transparent_65%)]">
      <EmptyState
        icon={<IconChat className="size-6" />}
        title={t("conversations.selectTitle")}
        description={t("conversations.selectDescription")}
      />
    </div>
  );
}
