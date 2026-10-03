"use client";

/**
 * What the finale shows: the channels the assistant answers in, the
 * business's own chat page (or, without one, a link that tries the
 * assistant from a phone), and the "went live" moment marked as
 * celebrated once, so the cabinet does not throw the party again.
 */

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { sectionQueries } from "@/api/sectionQueries";
import { useQuery } from "@/api/useQuery";
import { isChannelOn } from "@/app/b/[businessId]/assistant/channels/_lib/channels";
import { useBusiness } from "@/components/business/BusinessContext";
import { businessPath } from "@/lib/navigation";

import type { StepContext } from "../flow/stepContext";

export function useFinale(ctx: StepContext) {
  const { businessId, setup } = ctx;
  const router = useRouter();
  const { markSetUp } = useBusiness();
  const channelsQuery = sectionQueries.channels(businessId);
  const channels = useQuery(channelsQuery.key, channelsQuery.fetch);
  const share = useQuery(queryKeys.channels.share(businessId, ""), () =>
    api.GET("/v1/businesses/{business_id}/share-links", { params: { path: { business_id: businessId } } }),
  );
  const live = (channels.data ?? []).filter((channel) => channel.channel !== "owner_test" && isChannelOn(channel)).map((channel) => channel.channel);
  const phoneLink = setup.phone_test_links?.find((link) => link.is_answering)?.url ?? null;
  const shareUrl = share.data?.hosted_chat_url ?? null;

  // Mark "went live" as celebrated (once, even if the finale is opened again).
  const wentLive = setup.milestones?.find((milestone) => milestone.kind === "went_live");
  const shouldCelebrate = wentLive !== undefined && !wentLive.celebrated_at;
  const isMarked = useRef(false);
  useEffect(() => {
    if (!shouldCelebrate || isMarked.current) {
      return;
    }
    isMarked.current = true;
    void api.POST("/v1/businesses/{business_id}/setup/milestones/{kind}/celebrate", {
      params: { path: { business_id: businessId, kind: "went_live" } },
    });
  }, [businessId, shouldCelebrate]);

  /** Into the cabinet, with all its sections open. */
  const openCabinet = () => {
    markSetUp();
    router.push(businessPath(businessId, "overview"));
    router.refresh();
  };

  return { channels: live, shareUrl, phoneUrl: shareUrl ?? phoneLink, isShareLoading: share.isLoading && !share.data, openCabinet };
}
