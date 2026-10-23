import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { BusinessDeletionView } from "@/api/types";
import { formatDate } from "@/lib/format";
import { answerGet, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { DeletedBusinessesCard } from "./DeletedBusinessesCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));
const saved = vi.hoisted(() => vi.fn());
vi.mock("@/components/exports/csvExport", async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  saveFile: saved,
}));

const LIST = "/v1/me/business-deletions";
const CERTIFICATE = "/v1/me/business-deletions/{deletion_id}/certificate";
const STARTED = Date.UTC(2026, 9, 20, 10, 0) * 1000;
const completed: BusinessDeletionView = {
  id: "business_deletion_1",
  business_name: "Café Tbilisi",
  reason: "owner_request",
  state: "completed",
  started_at: STARTED,
  completed_at: STARTED + 60_000_000,
};
const running: BusinessDeletionView = {
  id: "business_deletion_2",
  business_name: "Salobie",
  reason: "unpaid_subscription",
  state: "in_progress",
  started_at: STARTED,
  completed_at: null,
};

describe("DeletedBusinessesCard: the certificates of deleted businesses", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.GET).mockReset();
    saved.mockReset();
  });

  it.each(["en", "ru", "ka", "he", "de"] as const)("lists each deletion with why and when, in %s", async (locale) => {
    const { t } = textsIn(locale);
    answerGet(() => ok({ items: [completed, running] }));
    renderInLocale(<DeletedBusinessesCard />, { locale });

    const card = await screen.findByTestId("deleted-businesses");
    const date = formatDate(STARTED, { locale, timeZone: "UTC" });
    expect(card.textContent).toContain(t("closure.deletions.reasonOwner"));
    expect(card.textContent).toContain(t("closure.deletions.completedOn", { date }));
    expect(card.textContent).toContain(t("closure.deletions.reasonUnpaid"));
    expect(card.textContent).toContain(t("closure.deletions.inProgress"));
    // Only a complete deletion has its certificate.
    expect(within(card).getAllByRole("button", { name: t("closure.deletions.certificate") })).toHaveLength(1);
  });

  it("downloads the certificate in the reader's language under the API's name", async () => {
    const { t } = textsIn("ru");
    const pdf = new Blob(["%PDF-1.7"], { type: "application/pdf" });
    answerGet((path) =>
      path === LIST
        ? ok({ items: [completed] })
        : Promise.resolve({
            data: pdf,
            response: new Response(null, {
              status: 200,
              headers: { "content-disposition": 'attachment; filename="deletion-certificate-1a2b3c4d.pdf"' },
            }),
          }),
    );
    renderInLocale(<DeletedBusinessesCard />, { locale: "ru" });

    await userEvent.click(await screen.findByRole("button", { name: t("closure.deletions.certificate") }));

    await waitFor(() => expect(saved).toHaveBeenCalledWith(pdf, "deletion-certificate-1a2b3c4d.pdf"));
    expect(vi.mocked(api.GET)).toHaveBeenCalledWith(CERTIFICATE, {
      params: { path: { deletion_id: "business_deletion_1" }, query: { language: "ru" } },
      headers: { Accept: "application/pdf" },
      parseAs: "blob",
    });
  });

  it("is not there while nothing was deleted", async () => {
    answerGet(() => ok({ items: [] }));
    renderInLocale(<DeletedBusinessesCard />);

    await waitFor(() => expect(vi.mocked(api.GET)).toHaveBeenCalledWith(LIST));
    expect(screen.queryByTestId("deleted-businesses")).toBeNull();
  });
});
