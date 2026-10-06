/**
 * The Channels pages on a phone. Large screens keep one page with every
 * part; on a phone the channel cards stay on /assistant/channels and each
 * longer part is a page of its own, linked from there:
 *
 *   /assistant/channels/website  the website chat's look, code and sites
 *   /assistant/channels/calls    call forwarding codes
 *   /assistant/channels/share    links, QR code and table card
 *
 * An address with the part's anchor (…/channels#share, from the setup
 * guide or a notification) opens its page on a phone.
 */

import { businessPath } from "@/lib/navigation";

export const CHANNEL_SUBPAGES = ["website", "calls", "share"] as const;

export type ChannelSubpage = (typeof CHANNEL_SUBPAGES)[number];

/** The anchors of the large-screen page that a phone opens as pages (the setup guide and notifications link to #share). */
const ANCHOR_PAGES: Readonly<Record<string, ChannelSubpage>> = {
  "#share": "share",
};

export function channelSubpagePath(businessId: string, subpage: ChannelSubpage): string {
  return `${businessPath(businessId, "assistant/channels")}/${subpage}`;
}

/** The phone page an anchor of the large-screen page stands for, if any. */
export function subpageOfAnchor(hash: string): ChannelSubpage | null {
  return ANCHOR_PAGES[hash] ?? null;
}

/** The pages to offer: the website chat's once it is on, call forwarding once the phone is, sharing always. */
export function offeredSubpages({ isWebChatOn, isPhoneOn }: { isWebChatOn: boolean; isPhoneOn: boolean }): ChannelSubpage[] {
  return CHANNEL_SUBPAGES.filter((page) => (page === "website" ? isWebChatOn : page === "calls" ? isPhoneOn : true));
}
