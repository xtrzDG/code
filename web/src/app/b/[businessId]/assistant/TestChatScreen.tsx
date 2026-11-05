"use client";

import { useSyncExternalStore } from "react";

import { useApplyChanges } from "@/components/assistant/ApplyChangesContext";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconChat, IconSparkles } from "@/components/icons";
import { Button, Card, EmptyState, ErrorState, LoadingRegion } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { sortVersions } from "@/lib/assistant/versions";

import { useAssistant } from "./_components/AssistantContext";
import { TestChatSkeleton } from "./_components/AssistantSkeletons";
import { TestChat } from "./_components/chat/TestChat";

const subscribeNever = () => () => {};

/**
 * Assistant -> Test chat: the owner writes as a customer to any version.
 * Test conversations are sandboxed (no billing, no staff notifications);
 * each reply shows the tools the assistant called.
 */
export function TestChatScreen({ initialVersionId }: { initialVersionId: string | null }) {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const { versions } = useAssistant();
  const applyChanges = useApplyChanges();
  const list = sortVersions(versions.data ?? []);
  // The chat restores its conversation from this tab's storage, so it is rendered in the browser only.
  const isBrowser = useSyncExternalStore(subscribeNever, () => true, () => false);

  if (!isBrowser || (versions.isLoading && !versions.data)) {
    return (
      <LoadingRegion label={t("common.loading")}>
        <TestChatSkeleton />
      </LoadingRegion>
    );
  }
  if (versions.error && !versions.data) {
    return (
      <Card>
        <ErrorState error={versions.error} onRetry={versions.reload} />
      </Card>
    );
  }
  if (list.length === 0) {
    return (
      <Card>
        <EmptyState
          icon={<IconChat className="size-6" />}
          title={t("assistant.chat.noVersionsTitle")}
          description={isOwner ? t("assistant.chat.noVersionsDescription") : t("assistant.versions.emptyStaff")}
          action={
            isOwner ? (
              <Button leadingIcon={<IconSparkles className="size-4" aria-hidden />} onClick={applyChanges.open} aria-haspopup="dialog">
                {t("applyChanges.sheet.apply")}
              </Button>
            ) : undefined
          }
        />
      </Card>
    );
  }

  return <TestChat key={business.id} versions={list} initialVersionId={initialVersionId} />;
}
