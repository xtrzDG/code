"use client";

/**
 * A Channels page of its own (website chat, call forwarding, sharing): the
 * way back to all channels above it, and its part once the channels have
 * loaded (with their skeleton and error as on the channels page).
 */

import Link from "next/link";
import type { ReactNode } from "react";

import { sectionQueries } from "@/api/sectionQueries";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconArrowLeft } from "@/components/icons";
import { Alert, Card, ErrorState, LoadingRegion } from "@/components/ui";
import { OwnerOnlyNote } from "@/components/workspace/OwnerOnly";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { upsertChannel, type ChannelView } from "../_lib/channels";
import { ChannelsSkeleton } from "./ChannelsSkeleton";

export function ChannelSubpageFrame({
  children,
}: {
  /** The part, given the channels as the API has them now and how to show one saved. */
  children: (channels: readonly ChannelView[], onSaved: (channel: ChannelView) => void) => ReactNode;
}) {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const query = sectionQueries.channels(business.id);
  const channels = useQuery(query.key, query.fetch);

  return (
    <div className="space-y-4">
      <Link
        href={businessPath(business.id, "assistant/channels")}
        className="inline-flex min-h-10 items-center gap-1.5 text-sm font-medium text-accent hover:underline"
      >
        <IconArrowLeft className="size-4 rtl:rotate-180" aria-hidden />
        {t("channelPages.back")}
      </Link>
      {!isOwner ? <OwnerOnlyNote /> : null}
      {channels.error && !channels.data ? (
        <Card>
          <ErrorState error={channels.error} onRetry={channels.reload} />
        </Card>
      ) : !channels.data ? (
        <LoadingRegion label={t("common.loading")}>
          <ChannelsSkeleton />
        </LoadingRegion>
      ) : (
        children(channels.data, (updated) => channels.setData((current) => upsertChannel(current, updated)))
      )}
    </div>
  );
}

/** What a part says while its channel is off, with the way to turn it on. */
export function ChannelOffNote({ text }: { text: string }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  return (
    <Alert tone="info" title={text}>
      <Link href={businessPath(business.id, "assistant/channels")} className="font-medium text-accent hover:underline">
        {t("channelPages.back")}
      </Link>
    </Alert>
  );
}
