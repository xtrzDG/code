"use client";

import { useI18n } from "@/i18n/client";

import { CallForwardingCard } from "../_components/CallForwardingCard";
import { ChannelOffNote, ChannelSubpageFrame } from "../_components/ChannelSubpageFrame";
import { findChannel, isChannelOn } from "../_lib/channels";

/** Call forwarding once the phone channel is connected; until then, where to connect it. */
export function CallsChannelScreen() {
  const { t } = useI18n();
  return (
    <ChannelSubpageFrame>
      {(channels) =>
        isChannelOn(findChannel(channels, "phone")) ? <CallForwardingCard /> : <ChannelOffNote text={t("channelPages.off.calls")} />
      }
    </ChannelSubpageFrame>
  );
}
