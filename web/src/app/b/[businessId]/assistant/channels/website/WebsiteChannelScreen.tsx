"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";

import { ChannelOffNote, ChannelSubpageFrame } from "../_components/ChannelSubpageFrame";
import { WebChatSection } from "../_components/WebChatSection";
import { findChannel, isChannelOn } from "../_lib/channels";

/** The website chat once it is on; until then, where to turn it on. */
export function WebsiteChannelScreen() {
  const { t } = useI18n();
  const { isOwner } = useBusiness();
  return (
    <ChannelSubpageFrame>
      {(channels, onSaved) => {
        const webChat = findChannel(channels, "web_chat");
        return webChat && isChannelOn(webChat) ? (
          <WebChatSection channel={webChat} canManage={isOwner} onSaved={onSaved} />
        ) : (
          <ChannelOffNote text={t("channelPages.off.website")} />
        );
      }}
    </ChannelSubpageFrame>
  );
}
