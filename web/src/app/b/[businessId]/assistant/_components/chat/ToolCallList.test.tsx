import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderInLocale, textsIn } from "@/test/render";

import { ToolCallList } from "./ToolCallList";

describe("ToolCallList", () => {
  const { t } = textsIn("en");

  it("shows a tool call's input and result when the API sent them", () => {
    renderInLocale(
      <ToolCallList toolCalls={[{ tool_name: "get_price", input_json: '{"item":"tea"}', result_json: '{"price":"2"}', is_error: false }]} />,
    );

    expect(screen.getByText(t("assistant.chat.toolInput"))).toBeTruthy();
    expect(screen.getByText(t("assistant.chat.toolResult"))).toBeTruthy();
  });

  it("shows only the tool when the API kept its input and result back", () => {
    const { container } = renderInLocale(
      <ToolCallList toolCalls={[{ tool_name: "get_price", input_json: null, result_json: null, is_error: true }]} />,
    );

    expect(screen.getByText("get_price")).toBeTruthy();
    expect(screen.getByText(t("assistant.chat.toolError"))).toBeTruthy();
    expect(screen.queryByText(t("assistant.chat.toolInput"))).toBeNull();
    expect(container.querySelector("pre")).toBeNull();
  });
});
