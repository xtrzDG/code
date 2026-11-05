import { describe, expect, it } from "vitest";

import { channelSubpagePath, offeredSubpages, subpageOfAnchor } from "./channelPages";

describe("the Channels pages on a phone", () => {
  it("live under the channels page", () => {
    expect(channelSubpagePath("business_1", "share")).toBe("/b/business_1/assistant/channels/share");
    expect(channelSubpagePath("biz/2", "website")).toBe("/b/biz%2F2/assistant/channels/website");
  });

  it("open from the large page's anchors", () => {
    expect(subpageOfAnchor("#share")).toBe("share");
    expect(subpageOfAnchor("")).toBeNull();
    expect(subpageOfAnchor("#tools")).toBeNull();
  });

  it("offer the website chat and call forwarding only once they are on, sharing always", () => {
    expect(offeredSubpages({ isWebChatOn: true, isPhoneOn: true })).toEqual(["website", "calls", "share"]);
    expect(offeredSubpages({ isWebChatOn: false, isPhoneOn: true })).toEqual(["calls", "share"]);
    expect(offeredSubpages({ isWebChatOn: true, isPhoneOn: false })).toEqual(["website", "share"]);
    expect(offeredSubpages({ isWebChatOn: false, isPhoneOn: false })).toEqual(["share"]);
  });
});
