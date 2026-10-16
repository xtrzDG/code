import { describe, expect, it } from "vitest";

import { ApiError } from "@/api/errors";

import {
  currentPage,
  importPercent,
  importStage,
  isImportRunning,
  normalizeWebsiteAddress,
  pageLabel,
  problemText,
  profileWebsite,
  siteHost,
  startProblemText,
  type WebsiteImport,
} from "./websiteImport";

function view(changes: Partial<WebsiteImport> = {}): WebsiteImport {
  return {
    id: "website_import_1",
    business_id: "business_1",
    status: "reading",
    url: "https://cafe.ge",
    pages_planned: 0,
    pages_read: 0,
    pages_skipped: 0,
    items_found: 0,
    started_at: 1,
    ...changes,
  };
}

function refused(status: number, code?: string, details: string[] = []): ApiError {
  return new ApiError({
    status,
    code: status === 422 ? "validation_failed" : status === 409 ? "conflict" : "rate_limited",
    reasons: code ? [{ code, message: "", details }] : [],
  });
}

describe("website addresses", () => {
  it("adds https:// and keeps only web addresses", () => {
    expect(normalizeWebsiteAddress(" cafe.ge ")).toBe("https://cafe.ge/");
    expect(normalizeWebsiteAddress("http://Cafe.ge/ka/menu")).toBe("http://cafe.ge/ka/menu");
    expect(normalizeWebsiteAddress("кафе.рф")).toBe("https://xn--80akn5b.xn--p1ai/");
    expect(normalizeWebsiteAddress("")).toBeNull();
    expect(normalizeWebsiteAddress("my cafe")).toBeNull();
    expect(normalizeWebsiteAddress("ftp://cafe.ge")).toBeNull();
    expect(normalizeWebsiteAddress("localhost")).toBeNull();
  });

  it("names sites and pages briefly", () => {
    expect(siteHost("https://www.cafe.ge/ka/")).toBe("cafe.ge");
    expect(siteHost("not a url")).toBe("not a url");
    expect(pageLabel("https://cafe.ge/menu?lang=ka")).toBe("/menu?lang=ka");
    expect(pageLabel("https://cafe.ge")).toBe("/");
    expect(pageLabel("::")).toBe("::");
  });

  it("offers the website link of the profile", () => {
    const links = [
      { kind: "menu" as const, url: "https://cafe.ge/menu" },
      { kind: "website" as const, url: "https://cafe.ge" },
    ];
    expect(profileWebsite({ links } as Parameters<typeof profileWebsite>[0])).toBe("https://cafe.ge");
    expect(profileWebsite({ links: links.slice(0, 1) } as Parameters<typeof profileWebsite>[0])).toBeNull();
    expect(profileWebsite(undefined)).toBeNull();
  });
});

describe("import progress", () => {
  it("moves from queued through opening and reading to done", () => {
    expect(isImportRunning(view({ status: "queued" }))).toBe(true);
    expect(isImportRunning(view({ status: "done" }))).toBe(false);
    expect(isImportRunning(null)).toBe(false);
    expect(importStage(view({ status: "queued" }))).toBe("queued");
    expect(importStage(view())).toBe("opening");
    expect(importStage(view({ pages_planned: 7 }))).toBe("reading");
    expect(importStage(view({ status: "failed" }))).toBe("failed");
    expect(importPercent(view({ status: "queued" }))).toBe(4);
    expect(importPercent(view())).toBe(10);
    expect(importPercent(view({ pages_planned: 4, pages_read: 1, pages_skipped: 1 }))).toBe(54);
    expect(importPercent(view({ pages_planned: 4, pages_read: 4 }))).toBe(96);
    expect(importPercent(view({ status: "done" }))).toBe(100);
    expect(currentPage(view({ pages_planned: 4, pages_read: 1, pages_skipped: 1 }))).toBe(3);
    expect(currentPage(view({ pages_planned: 4, pages_read: 4 }))).toBe(4);
  });
});

describe("problems in words", () => {
  it("explains a failed import by its problem and detail", () => {
    expect(problemText("website_link_invalid", "not_public").key).toBe("knowledge.website.errors.notPublic");
    expect(problemText("website_link_invalid", "port_not_allowed").key).toBe("knowledge.website.errors.port");
    expect(problemText("website_link_unreachable", "unknown_host").key).toBe("knowledge.website.errors.unknownHost");
    expect(problemText("website_link_unreachable", "timeout").key).toBe("knowledge.website.errors.timeout");
    expect(problemText("website_link_unreachable", "http_status:503")).toEqual({
      key: "knowledge.website.errors.httpStatus",
      values: { status: 503 },
    });
    expect(problemText("website_link_unreachable", "connection_failed").key).toBe("knowledge.website.errors.unreachable");
    expect(problemText("website_link_unreadable", "media_type:application/pdf").key).toBe(
      "knowledge.website.errors.unreadable",
    );
    expect(problemText("website_reader_unavailable", "reader_failed").key).toBe("knowledge.website.errors.reader");
    expect(problemText("website_import_interrupted", null).key).toBe("knowledge.website.errors.interrupted");
    expect(problemText("something_new", null).key).toBe("knowledge.website.errors.unreachable");
  });

  it("explains a refused start, or leaves it to the generic message", () => {
    expect(startProblemText(refused(422, "website_link_invalid", ["credentials_in_url"]))?.key).toBe(
      "knowledge.website.errors.credentials",
    );
    expect(startProblemText(refused(422))?.key).toBe("knowledge.website.errors.address");
    expect(startProblemText(refused(409, "website_import_running"))?.key).toBe("knowledge.website.errors.running");
    expect(startProblemText(refused(429))?.key).toBe("knowledge.website.errors.tooMany");
    expect(startProblemText(new ApiError({ status: 502, code: "external_service_error" }))).toBeNull();
    expect(startProblemText(new Error("network"))).toBeNull();
  });
});
