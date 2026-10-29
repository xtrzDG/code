import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderInLocale, textsIn } from "@/test/render";

import { OfferedChoices, StoryContextLine } from "./MessageContext";

describe("MessageContext", () => {
  it("says that a customer answered the business's story", () => {
    const { container } = renderInLocale(<StoryContextLine note="story_reply" alignEnd={false} />, { locale: "it" });

    expect(container.textContent).toBe("Risposta alla tua storia");
  });

  it("names a mention in the customer's own story", () => {
    renderInLocale(<StoryContextLine note="story_mention" alignEnd />, { locale: "it" });

    expect(screen.getByText(textsIn("it").t("inboxCard.messageContext.story_mention"))).toBeTruthy();
  });

  it("lists the options an answer offered without buttons", () => {
    renderInLocale(<OfferedChoices choices={["18:00", "19:30"]} alignEnd={false} />);

    const list = screen.getByRole("list", { name: textsIn("en").t("inboxCard.offeredChoices") });
    expect([...list.querySelectorAll("li")].map((item) => item.textContent)).toEqual(["18:00", "19:30"]);
    expect(screen.queryAllByRole("button")).toEqual([]);
  });
});
