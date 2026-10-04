import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { BUSINESS_PAGES } from "@/lib/navigation";

import { articleLinks, linkTarget } from "./helpMarkdown";
import {
  HELP_ARTICLES,
  PAGE_HELP,
  cabinetHref,
  cabinetPage,
  coachMarkFor,
  helpArticlePath,
  helpSlugForPage,
  isHelpArticleSlug,
} from "./helpTopics";

const HELP_DIRECTORY = fileURLToPath(new URL("../../../../docs/help/", import.meta.url));
const LANGUAGES = ["en", "ru", "ka"] as const;

function articleFiles(language: string): string[] {
  return readdirSync(`${HELP_DIRECTORY}${language}`)
    .filter((name) => name.endsWith(".md"))
    .sort();
}

describe("the help articles the cabinet knows", () => {
  it.each(LANGUAGES)("are exactly the files of docs/help/%s", (language) => {
    expect(articleFiles(language).map((name) => name.replace(/\.md$/, ""))).toEqual([...HELP_ARTICLES].sort());
  });

  it.each(LANGUAGES)("link only to articles and cabinet pages that exist (%s)", (language) => {
    for (const name of articleFiles(language)) {
      const source = readFileSync(`${HELP_DIRECTORY}${language}/${name}`, "utf8");
      for (const target of articleLinks(source)) {
        const resolved = linkTarget(target);
        expect(resolved, `${language}/${name}: ${target}`).not.toBeNull();
        if (resolved?.kind === "article") {
          expect(isHelpArticleSlug(resolved.slug), `${language}/${name}: ${target}`).toBe(true);
        }
      }
    }
  });
});

describe("helpSlugForPage", () => {
  it("names an article for every page of a business", () => {
    for (const page of BUSINESS_PAGES) {
      expect(isHelpArticleSlug(PAGE_HELP[page])).toBe(true);
    }
  });

  it("opens the matching article of a section's page", () => {
    expect(helpSlugForPage("inbox")).toBe("inbox");
    expect(helpSlugForPage("assistant/channels")).toBe("channels");
    expect(helpSlugForPage("settings/billing")).toBe("billing");
    expect(helpSlugForPage("settings/calls")).toBe("call-forwarding");
  });

  it("has nothing outside the business pages", () => {
    expect(helpSlugForPage(null)).toBeNull();
  });
});

describe("cabinet links", () => {
  it("know the cabinet's pages", () => {
    expect(cabinetPage("assistant/channels")).toBe("assistant/channels");
    expect(cabinetPage("assistant/unknown")).toBeNull();
  });

  it("lead into the business the person is in", () => {
    expect(cabinetHref("bookings", "biz_1")).toBe("/b/biz_1/bookings");
    expect(cabinetHref("bookings", null)).toBeNull();
  });

  it("open an article of the help center", () => {
    expect(helpArticlePath("inbox")).toBe("/help/inbox");
    expect(isHelpArticleSlug("nothing-here")).toBe(false);
  });
});

describe("coach marks", () => {
  it("show on the Inbox, the Assistant's test page and Channels, each once", () => {
    expect(coachMarkFor("inbox")?.key).toBe("inbox");
    expect(coachMarkFor("assistant")?.article).toBe("teach-your-assistant");
    expect(coachMarkFor("assistant/channels")?.key).toBe("channels");
    expect(coachMarkFor("bookings")).toBeNull();
    expect(coachMarkFor(null)).toBeNull();
  });
});
