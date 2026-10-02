/**
 * The website chat widget's error beacon: an error of the widget's own code
 * reaches POST /v1/widget/errors as its kind, phase and position in
 * widget.js, never as a message text, and the host page keeps working.
 */

import type { Request, Route } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import { BUSINESS, FakeWidgetApi, SITE, loadWidgetSource, serveSite } from "./support/widget-site";

test.beforeAll(async () => {
  await loadWidgetSource();
});

/** The fake widget API with a scripted config answer, recording error reports. */
class BrokenConfigApi extends FakeWidgetApi {
  reports: Record<string, unknown>[] = [];

  constructor(private readonly config: { status: number; body: unknown }) {
    super();
  }

  override async handle(route: Route): Promise<void> {
    const request: Request = route.request();
    const url = new URL(request.url());
    if (url.pathname === "/v1/widget/errors" && request.method() === "POST") {
      this.reports.push(JSON.parse(request.postData() ?? "{}") as Record<string, unknown>);
      await route.fulfill({ status: 204, headers: { "access-control-allow-origin": "*" } });
      return;
    }
    if (url.pathname.endsWith("/config")) {
      await route.fulfill({
        status: this.config.status,
        headers: { "access-control-allow-origin": "*" },
        json: this.config.body,
      });
      return;
    }
    await super.handle(route);
  }
}

test("a failing chat configuration is reported with its status only", async ({ page }) => {
  const api = new BrokenConfigApi({ status: 503, body: { error: "unavailable" } });
  await serveSite(page.context(), api);
  await page.goto(`${SITE}/`);

  await expect.poll(() => api.reports.length).toBe(1);
  expect(api.reports[0]).toEqual({
    kind: "config_failed",
    phase: "boot",
    business_id: BUSINESS,
    status_code: 503,
  });
  await expect(page.getByRole("heading", { name: "Shop page /" })).toBeVisible();
});

test("an error of the widget's code is reported with its place, not its text", async ({ page }) => {
  // A malformed language list makes the panel fail while it is built.
  const api = new BrokenConfigApi({
    status: 200,
    body: { is_enabled: true, business_name: "Cafe Batumi", languages: [null], default_language: "en" },
  });
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await serveSite(page.context(), api);
  await page.goto(`${SITE}/`);

  await expect.poll(() => api.reports.length).toBe(1);
  const report = api.reports[0] ?? {};
  expect(report).toMatchObject({ kind: "script_error", phase: "mount", business_id: BUSINESS, error_name: "TypeError" });
  expect(report.line).toEqual(expect.any(Number));
  expect(report.column).toEqual(expect.any(Number));
  expect(JSON.stringify(report)).not.toContain("tag");
  expect(Object.keys(report).sort()).toEqual(["business_id", "column", "error_name", "kind", "line", "phase"]);
  // The error stays inside the widget: the host page sees none.
  expect(pageErrors).toEqual([]);
});
