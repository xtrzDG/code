import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import type { ResourceCalendarView } from "@/lib/resourceCalendar";
import { answerGet, ok, pending } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { business } from "../../../../settings/_lib/settingsFixtures";
import { ResourceCalendarSheet } from "./ResourceCalendarSheet";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const CALENDAR = "/v1/businesses/{business_id}/resources/{resource_id}/calendar";
const GOOGLE_LIST = "/v1/businesses/{business_id}/integrations/google-calendar/calendars";
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const { t, tp } = textsIn("en");
const at = (hour: number) => Date.UTC(2026, 9, 6, hour, 0) * 1000;

const view = (patch: Partial<ResourceCalendarView> = {}): ResourceCalendarView => ({
  business_id: business.id,
  resource_id: "resource_1",
  resource_name: "Sea view",
  google: { is_available: true, is_connected: true, calendar_id: "primary", status: { block_count: 2, last_synced_at: at(8) } },
  ical_imports: [
    { feed_id: "ical_import_1", host: "www.airbnb.com", added_at: at(7), status: { block_count: 0, problem: "timeout" } },
  ],
  ical_export: { is_on: false },
  booking_system: null,
  booking_system_kinds: ["cal_com"],
  upcoming_busy_times: [{ source: "ical", feed_host: "www.airbnb.com", starts_at: at(10), ends_at: at(12) }],
  next_sync_at: at(9),
  ...patch,
});

function serve(calendar: ResourceCalendarView) {
  answerGet((path) => {
    if (path === CALENDAR) return ok(calendar);
    if (path === GOOGLE_LIST) {
      return ok({
        is_readable: true,
        items: [
          { calendar_id: "owner@example.com", name: "Owner", access_role: "owner", is_primary: true },
          { calendar_id: "room@group.calendar.google.com", name: "Room 1", access_role: "reader", is_primary: false },
        ],
      });
    }
    return pending();
  });
}

function renderSheet() {
  return renderInLocale(
    <BusinessProvider business={business} me={me}>
      <ResourceCalendarSheet resource={{ id: "resource_1", name: "Sea view" }} onClose={() => undefined} />
    </BusinessProvider>,
  );
}

describe("ResourceCalendarSheet: a resource's calendars", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.POST).mockReset();
    vi.mocked(api.PUT).mockReset();
  });

  it("shows each source with how its last read went, and the busy times ahead", async () => {
    serve(view());
    renderSheet();

    expect(await screen.findByText(t("calendarSync.problems.timeout"))).toBeTruthy();
    expect(screen.getAllByText("www.airbnb.com").length).toBeGreaterThan(0);
    expect(await screen.findByText("Owner")).toBeTruthy();
    expect(screen.getByText(new RegExp(tp("calendarSync.status.busy", 2)))).toBeTruthy();
    expect(screen.getByText(t("calendarSync.busy.sources.ical"), { exact: false })).toBeTruthy();
    expect(screen.getByRole("button", { name: t("calendarSync.export.create") })).toBeTruthy();
  });

  it("checks an iCal address before sending it, then imports it", async () => {
    const user = userEvent.setup();
    serve(view({ ical_imports: [] }));
    const added = view({
      ical_imports: [{ feed_id: "ical_import_2", host: "admin.booking.com", added_at: at(9), status: { block_count: 0 } }],
    });
    vi.mocked(api.POST).mockImplementation((() => ok(added)) as never);
    renderSheet();

    const address = await screen.findByLabelText(t("calendarSync.ical.address"));
    await user.type(address, "ftp://example.com/feed.ics");
    await user.click(screen.getByRole("button", { name: t("calendarSync.ical.import") }));
    expect(screen.getByText(t("calendarSync.ical.invalid"))).toBeTruthy();
    expect(api.POST).not.toHaveBeenCalled();

    await user.clear(address);
    await user.type(address, " https://admin.booking.com/ical/feed.ics ");
    await user.click(screen.getByRole("button", { name: t("calendarSync.ical.import") }));
    const [, init] = vi.mocked(api.POST).mock.calls[0] as unknown as [string, { body: { url: string } }];
    expect(init.body).toEqual({ url: "https://admin.booking.com/ical/feed.ics" });
    expect(await screen.findByText("admin.booking.com")).toBeTruthy();
  });

  it("links the account's own calendar as primary", async () => {
    const user = userEvent.setup();
    serve(view({ google: { is_available: true, is_connected: true, calendar_id: null, status: null } }));
    vi.mocked(api.PUT).mockImplementation((() => ok(view())) as never);
    renderSheet();

    const select = await screen.findByLabelText(t("calendarSync.google.calendar"));
    await screen.findByRole("option", { name: t("calendarSync.google.primary", { name: "Owner" }) });
    await user.selectOptions(select, "primary");
    await user.click(screen.getByRole("button", { name: t("calendarSync.google.link") }));
    const [, init] = vi.mocked(api.PUT).mock.calls[0] as unknown as [string, { body: unknown }];
    expect(init.body).toEqual({ calendar_id: "primary" });
  });

  it("sends people to Channels while Google is not connected", async () => {
    serve(view({ google: { is_available: true, is_connected: false, calendar_id: null, status: null } }));
    renderSheet();

    const link = await screen.findByRole("link", { name: t("calendarSync.google.openChannels") });
    expect(link.getAttribute("href")).toBe(`/b/${business.id}/assistant/channels`);
  });

  it("asks for a booking system's event type and key, then connects it", async () => {
    const user = userEvent.setup();
    serve(view());
    vi.mocked(api.PUT).mockImplementation(
      (() =>
        ok(
          view({
            booking_system: {
              kind: "cal_com",
              external_resource_id: "1203845",
              external_resource_title: "Sea view stay",
              added_at: at(9),
              status: { block_count: 0 },
            },
          }),
        )) as never,
    );
    renderSheet();

    await user.click(await screen.findByRole("button", { name: t("calendarSync.bookingSystem.connect") }));
    expect(screen.getByText(t("calendarSync.bookingSystem.eventTypeRequired"))).toBeTruthy();
    expect(screen.getByText(t("calendarSync.bookingSystem.apiKeyRequired"))).toBeTruthy();
    expect(api.PUT).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText(t("calendarSync.bookingSystem.eventType"), { exact: false }), "1203845");
    await user.type(screen.getByLabelText(t("calendarSync.bookingSystem.apiKey"), { exact: false }), "cal_test_0000");
    await user.click(screen.getByRole("button", { name: t("calendarSync.bookingSystem.connect") }));
    const [, init] = vi.mocked(api.PUT).mock.calls[0] as unknown as [string, { body: unknown }];
    expect(init.body).toEqual({ kind: "cal_com", external_resource_id: "1203845", api_key: "cal_test_0000" });
    expect(await screen.findByText("Sea view stay")).toBeTruthy();
  });

  it("shows a new shared address once, and asks before replacing it", async () => {
    const user = userEvent.setup();
    serve(view());
    const shared = view({ ical_export: { is_on: true, created_at: at(9), last_read_at: null } });
    vi.mocked(api.POST).mockImplementation((() => ok({ url: "https://api.example.com/v1/public/ical/test-token-0000.ics", calendar: shared })) as never);
    renderSheet();

    await user.click(await screen.findByRole("button", { name: t("calendarSync.export.create") }));
    expect(await screen.findByText(t("calendarSync.export.shownOnce"))).toBeTruthy();
    const address = screen.getByLabelText(t("calendarSync.export.copy"), { selector: "input" });
    expect((address as HTMLInputElement).value).toContain("test-token-0000");
    expect(screen.getByText(t("calendarSync.export.neverRead"))).toBeTruthy();

    await user.click(screen.getByRole("button", { name: t("calendarSync.export.regenerate") }));
    const dialog = await screen.findByRole("dialog", { name: t("calendarSync.export.regenerateTitle") });
    expect(within(dialog).getByText(t("calendarSync.export.regenerateDescription"))).toBeTruthy();
    expect(api.POST).toHaveBeenCalledTimes(1);
  });
});
