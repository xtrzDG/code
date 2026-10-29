import { pageMetadata } from "@/components/business/pageMetadata";

import { ShareChannelScreen } from "./ShareChannelScreen";

export const generateMetadata = pageMetadata("assistant/channels", "channelPages.share.title");

/** Channels → the chat page, links, QR code and table card (a page of its own on a phone). */
export default function ShareChannelPage() {
  return <ShareChannelScreen />;
}
