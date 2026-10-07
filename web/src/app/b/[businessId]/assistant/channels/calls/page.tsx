import { pageMetadata } from "@/components/business/pageMetadata";

import { CallsChannelScreen } from "./CallsChannelScreen";

export const generateMetadata = pageMetadata("assistant/channels", "channelPages.calls.title");

/** Channels → call forwarding codes (a page of its own on a phone). */
export default function CallsChannelPage() {
  return <CallsChannelScreen />;
}
