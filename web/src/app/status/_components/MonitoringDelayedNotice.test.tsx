import { screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderInLocale, textsIn } from "@/test/render";

import { MonitoringDelayedNotice } from "./MonitoringDelayedNotice";

const NOW = Date.UTC(2026, 9, 6, 12, 17, 30);
const CHECKED_AT = Date.UTC(2026, 9, 6, 12, 0) * 1000;

describe("MonitoringDelayedNotice: the platform's checks are late", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("says how long ago the last check was, in the reader's language", () => {
    renderInLocale(<MonitoringDelayedNotice checkedAt={CHECKED_AT} />, { locale: "it" });

    const texts = textsIn("it");
    const notice = screen.getByRole("status").textContent;
    expect(notice).toContain(texts.t("platformStatus.monitoringDelayed.title"));
    expect(notice).toContain(texts.tp("platformStatus.monitoringDelayed.minutesAgo", 17));
    expect(notice).toContain("L'ultima verifica risale a 17 minuti fa.");
  });

  it("counts whole minutes in English too", () => {
    renderInLocale(<MonitoringDelayedNotice checkedAt={CHECKED_AT} />);

    expect(screen.getByRole("status").textContent).toContain("The last check was 17 minutes ago.");
  });
});
