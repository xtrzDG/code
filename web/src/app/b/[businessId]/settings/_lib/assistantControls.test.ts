import { describe, expect, it } from "vitest";

import {
  SWITCHABLE_ACTIONS,
  actionLabel,
  assistantControls,
  controlsBody,
  controlsChangeText,
  withAction,
} from "./assistantControls";

const VIEW = {
  remembers_customers: true,
  shares_team_notes: false,
  is_paused: false,
  disabled_tools: ["send_payment_link", "handoff_to_human"],
  updated_at: null,
} as const;

describe("assistant controls", () => {
  it("reads the stored controls, keeping only the actions the card lists", () => {
    expect(assistantControls({ ...VIEW, disabled_tools: [...VIEW.disabled_tools] })).toEqual({
      isHandedOver: false,
      disabledActions: ["send_payment_link"],
    });
  });

  it("switches one action off or on, in the card's order", () => {
    expect(withAction(["send_payment_link"], "create_booking", false)).toEqual(["create_booking", "send_payment_link"]);
    expect(withAction(["create_booking", "send_payment_link"], "create_booking", true)).toEqual(["send_payment_link"]);
    expect(withAction([], "cancel_booking", true)).toEqual([]);
  });

  it("saves the controls with the memory switches as stored", () => {
    const view = { ...VIEW, disabled_tools: [...VIEW.disabled_tools] };
    expect(controlsBody(view, { isHandedOver: true, disabledActions: ["create_booking"] })).toEqual({
      remembers_customers: true,
      shares_team_notes: false,
      is_paused: true,
      disabled_tools: ["create_booking"],
    });
  });

  it("tells the owner what changed", () => {
    const running = { isHandedOver: false, disabledActions: [] };
    expect(controlsChangeText(running, { ...running, isHandedOver: true })).toBe("assistantControls.handedOver");
    expect(controlsChangeText({ ...running, isHandedOver: true }, running)).toBe("assistantControls.resumed");
    expect(controlsChangeText(running, { ...running, disabledActions: ["send_link"] })).toBe("assistantControls.actionOff");
    expect(controlsChangeText({ ...running, disabledActions: ["send_link"] }, running)).toBe("assistantControls.actionOn");
    expect(controlsChangeText(running, running)).toBeNull();
  });

  it("names every action", () => {
    expect(SWITCHABLE_ACTIONS.map(actionLabel)).toContain("assistantControls.actions.create_booking");
  });
});
