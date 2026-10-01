"use client";

import { Badge, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { VERSION_STATUS_TONES, type AssistantVersionStatus } from "@/lib/assistant";

export const VERSION_STATUS_LABELS: Record<AssistantVersionStatus, MessageKey> = {
  draft: "assistant.status.draft",
  testing: "assistant.status.testing",
  ready: "assistant.status.ready",
  tests_failed: "assistant.status.tests_failed",
  published: "assistant.status.published",
  archived: "assistant.status.archived",
};

export function VersionStatusBadge({ status }: { status: AssistantVersionStatus }) {
  const { t } = useI18n();
  return (
    <Badge tone={VERSION_STATUS_TONES[status]} icon={status === "testing" ? <Spinner size="sm" className="-ml-0.5 [&_svg]:size-3" /> : undefined}>
      {t(VERSION_STATUS_LABELS[status])}
    </Badge>
  );
}
