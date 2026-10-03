"use client";

/**
 * "Where do your customers write?" as state: the website chat (on unless
 * the owner turned it off before), a Telegram bot connected with the token
 * from @BotFather, and the business's own chat page once the website chat
 * is on. Continue switches the website chat as chosen; with no channel on,
 * the step is skipped for now.
 */

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { sectionQueries } from "@/api/sectionQueries";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { findChannel, isChannelOn, markChannelDisabled, upsertChannel } from "@/app/b/[businessId]/assistant/channels/_lib/channels";
import { buildConnectBody, EMPTY_CONNECT_FORM, type ConnectChannelBody, type ConnectFieldError } from "@/app/b/[businessId]/assistant/channels/_lib/connectForm";

import { useSaveTracker } from "../SaveTracker";
import type { StepContext } from "../flow/stepContext";

const CONNECT_ERRORS = { conflict: "channels.errors.accountTaken", external_service_error: "channels.errors.provider" } as const;

export function useChannelsStep(ctx: StepContext) {
  const { businessId } = ctx;
  const track = useSaveTracker();
  const channelsQuery = sectionQueries.channels(businessId);
  const channels = useQuery(channelsQuery.key, channelsQuery.fetch, { requireFresh: true });
  const web = findChannel(channels.data, "web_chat");
  const telegram = findChannel(channels.data, "telegram");
  const [webChoice, setWebChoice] = useState<boolean | null>(null);
  const isWebOn = webChoice ?? (web ? isChannelOn(web) : true);
  const share = useQuery(
    queryKeys.channels.share(businessId, ""),
    () => api.GET("/v1/businesses/{business_id}/share-links", { params: { path: { business_id: businessId } } }),
    { enabled: isChannelOn(web) },
  );
  const [token, setToken] = useState("");
  const [tokenError, setTokenError] = useState<ConnectFieldError | null>(null);
  const [isFinishing, setFinishing] = useState(false);

  const connect = useMutation(
    (channel: "web" | "telegram", body: ConnectChannelBody) =>
      api.PUT("/v1/businesses/{business_id}/channels/{channel}", { params: { path: { business_id: businessId, channel } }, body }),
    { errorMessages: CONNECT_ERRORS, stale: [queryKeys.assistant.all(businessId), queryKeys.channels.all(businessId)] },
  );
  const disconnect = useMutation(
    () => api.DELETE("/v1/businesses/{business_id}/channels/{channel}", { params: { path: { business_id: businessId, channel: "web" } } }),
    { stale: [queryKeys.assistant.all(businessId), queryKeys.channels.all(businessId)] },
  );

  const connectTelegram = async () => {
    const built = buildConnectBody("telegram", { ...EMPTY_CONNECT_FORM, botToken: token });
    if (!built.ok) {
      setTokenError(built.errors.botToken ?? "required");
      return;
    }
    setTokenError(null);
    const result = await connect.run("telegram", built.body);
    if (result.ok) {
      channels.setData((current) => upsertChannel(current, result.data));
      setToken("");
      ctx.refresh();
    }
  };

  /** Switch the website chat as chosen, then on (or "skip for now" with no channel). */
  const finish = async () => {
    setFinishing(true);
    try {
      let isAnyOn = isChannelOn(telegram);
      if (isWebOn && !isChannelOn(web)) {
        const run = connect.run("web", {});
        void track(run.then((result) => result.ok));
        const result = await run;
        if (!result.ok) {
          return;
        }
        channels.setData((current) => upsertChannel(current, result.data));
        isAnyOn = true;
      } else if (!isWebOn && isChannelOn(web)) {
        const run = disconnect.run();
        void track(run.then((result) => result.ok));
        const result = await run;
        if (!result.ok) {
          return;
        }
        channels.setData((current) => markChannelDisabled(current, "web_chat"));
      } else if (isWebOn) {
        isAnyOn = true;
      }
      if (isAnyOn) {
        ctx.refresh();
        ctx.next();
      } else {
        await ctx.skip("channels");
      }
    } finally {
      setFinishing(false);
    }
  };

  return {
    isLoading: channels.isLoading && !channels.data,
    error: channels.data ? null : channels.error,
    reload: channels.reload,
    isWebOn,
    setWebOn: setWebChoice,
    hostedUrl: isChannelOn(web) ? (share.data?.hosted_chat_url ?? null) : null,
    telegram: {
      channel: isChannelOn(telegram) ? telegram : undefined,
      token,
      setToken: (value: string) => {
        setToken(value);
        setTokenError(null);
      },
      error: tokenError,
      isConnecting: connect.isPending && token !== "",
      connect: connectTelegram,
    },
    isFinishing,
    finish,
  };
}
