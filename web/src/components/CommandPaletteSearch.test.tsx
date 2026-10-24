import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { queryCache } from "@/api/queryCache";
import { answerGet, ok, pending } from "@/test/fakeApi";
import { Providers } from "@/test/render";

import { useCommandPaletteSearch, type PaletteSearchScope } from "./CommandPaletteSearch";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const SEARCH = "/v1/businesses/{business_id}/search";
const SCOPE: PaletteSearchScope = { businessId: "business_1", timeZone: "Asia/Tbilisi" };

const NINO = {
  customers: [{ id: "contact_1", name: "Nino Beridze", phone_number: "+995599123456", masked_phone_number: null }],
  conversations: [],
  bookings: [],
};

function renderSearch(text: string) {
  const wrapper = ({ children }: { children: ReactNode }) => <Providers locale="en">{children}</Providers>;
  return renderHook(({ typed }: { typed: string }) => useCommandPaletteSearch(SCOPE, typed), {
    wrapper,
    initialProps: { typed: text },
  });
}

describe("useCommandPaletteSearch", () => {
  beforeEach(() => {
    queryCache.clear();
    answerGet((path) => (path === SEARCH ? ok(NINO) : pending()));
  });

  it("finds customers once the typing pauses", async () => {
    const { result } = renderSearch("Nino");

    await waitFor(() => expect(result.current.groups.customers?.map((entry) => entry.label)).toEqual(["Nino Beridze"]));
    expect(result.current.searched).toBe("Nino");
  });

  it("shows no hits of the earlier text once the box is empty again", async () => {
    const { result, rerender } = renderSearch("Nino");
    await waitFor(() => expect(result.current.groups.customers).toHaveLength(1));

    // A fresh opening clears the box: the earlier hits are gone at once,
    // not after the typing pause (the palette counted them as options).
    act(() => rerender({ typed: "" }));

    expect(result.current.searched).toBeNull();
    expect(result.current.groups.customers).toEqual([]);
    expect(result.current.isSearching).toBe(false);
  });
});
