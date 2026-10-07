import { pageMetadata } from "@/components/business/pageMetadata";

import { WebsiteChannelScreen } from "./WebsiteChannelScreen";

export const generateMetadata = pageMetadata("assistant/channels", "channelPages.website.title");

/** Channels → the website chat's look, its code and the sites allowed to show it (a page of its own on a phone). */
export default function WebsiteChannelPage() {
  return <WebsiteChannelScreen />;
}
