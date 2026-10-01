"use client";

import { IconChat } from "@/components/icons";
import { Card, EmptyState } from "@/components/ui";
import { useI18n } from "@/i18n/client";

export function NoConversationSelected() {
  const { t } = useI18n();
  return (
    <Card>
      <EmptyState
        icon={<IconChat className="size-6" />}
        title={t("conversations.selectTitle")}
        description={t("conversations.selectDescription")}
      />
    </Card>
  );
}
