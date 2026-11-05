"use client";

import { ChannelSubpageFrame } from "../_components/ChannelSubpageFrame";
import { ShareSection } from "../_components/ShareSection";
import { findChannel, isChannelOn } from "../_lib/channels";

/** The links to the assistant, their QR code and the table card. */
export function ShareChannelScreen() {
  return (
    <ChannelSubpageFrame>
      {(channels) => {
        const webChat = findChannel(channels, "web_chat");
        return <ShareSection isWebChatOn={isChannelOn(webChat)} accent={webChat?.widget_color ?? null} />;
      }}
    </ChannelSubpageFrame>
  );
}
