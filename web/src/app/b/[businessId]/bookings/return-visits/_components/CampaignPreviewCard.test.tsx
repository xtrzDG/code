import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderInLocale, textsIn } from "@/test/render";

import { CampaignPreviewCard } from "./CampaignPreviewCard";

const previews = [{ language: "it", text: "Trattoria da Marco: ti aspettiamo venerdì 7 novembre." }];

describe("CampaignPreviewCard", () => {
  it.each(["en", "it"] as const)("is the message customers get, not an example (%s)", (locale) => {
    renderInLocale(<CampaignPreviewCard previews={previews} />, { locale });
    const { t } = textsIn(locale);

    expect(screen.getByRole("heading", { name: t("returnVisits.preview.title") })).toBeTruthy();
    expect(screen.getByText(previews[0]!.text)).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/as it would be today|come sarebbe oggi|What customers read/);
  });

  it("names the card in plain words", () => {
    expect(textsIn("en").t("returnVisits.preview.title")).toBe("Message customers get");
    expect(textsIn("it").t("returnVisits.preview.title")).toBe("Messaggio che ricevono i clienti");
  });
});
