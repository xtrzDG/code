import { describe, expect, it } from "vitest";

import { businessIdOfPath, tunnelStepReports } from "./stepReports";

describe("tunnel step reports", () => {
  it("enter the first screen, and complete a screen when going deeper", () => {
    expect(tunnelStepReports(null, "business", undefined)).toEqual([{ kind: "tunnel_step", step: "business", action: "entered" }]);
    expect(tunnelStepReports("hours", "people", "biz_1")).toEqual([
      { kind: "tunnel_step", step: "hours", action: "completed", business_id: "biz_1" },
      { kind: "tunnel_step", step: "people", action: "entered", business_id: "biz_1" },
    ]);
  });

  it("complete nothing going back, and the finale is no screen", () => {
    expect(tunnelStepReports("people", "hours", "biz_1")).toEqual([
      { kind: "tunnel_step", step: "hours", action: "entered", business_id: "biz_1" },
    ]);
    expect(tunnelStepReports("launch", "done", "biz_1")).toEqual([
      { kind: "tunnel_step", step: "launch", action: "completed", business_id: "biz_1" },
    ]);
    expect(tunnelStepReports("hours", "hours", "biz_1")).toEqual([]);
  });

  it("name the business of /b/{id}/setup only", () => {
    expect(businessIdOfPath("/b/business_1/setup")).toBe("business_1");
    expect(businessIdOfPath("/create")).toBeUndefined();
    expect(businessIdOfPath("/b/%E0%A4%A/setup")).toBeUndefined();
  });
});
