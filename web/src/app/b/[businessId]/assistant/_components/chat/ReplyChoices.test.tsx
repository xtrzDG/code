import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderInLocale, textsIn } from "@/test/render";

import { AssistantLine } from "./AssistantLine";
import { ReplyChoices } from "./ReplyChoices";

describe("ReplyChoices", () => {
  it("sends the tapped option as the customer's message", async () => {
    const onChoose = vi.fn();
    renderInLocale(<ReplyChoices choices={["18:00", "19:30"]} onChoose={onChoose} isSending={false} />, { locale: "ru" });

    const group = screen.getByRole("group", { name: textsIn("ru").t("assistant.chat.choicesLabel") });
    expect(group.textContent).toBe("18:0019:30");
    await userEvent.click(screen.getByRole("button", { name: "19:30" }));

    expect(onChoose).toHaveBeenCalledWith("19:30");
  });

  it("cannot be tapped while a message is on its way", () => {
    renderInLocale(<ReplyChoices choices={["Yes", "No"]} onChoose={vi.fn()} isSending />);

    expect(screen.getAllByRole("button").every((button) => (button as HTMLButtonElement).disabled)).toBe(true);
  });

  it("an earlier answer keeps its options as a record, not as buttons", () => {
    renderInLocale(
      <AssistantLine
        entry={{ kind: "assistant", key: "a", text: "Shall I book it?", choices: ["Yes", "No"], versionId: null }}
        answerLabel={() => ""}
      />,
    );

    expect(screen.queryAllByRole("button")).toEqual([]);
    const list = screen.getByRole("list", { name: textsIn("en").t("assistant.chat.choicesLabel") });
    expect(list.textContent).toBe("YesNo");
  });
});
