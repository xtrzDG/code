import { describe, expect, it } from "vitest";

import { heroPlan, type DeviceSignals } from "./heroDevice";

const DESKTOP: DeviceSignals = {
  prefersReducedMotion: false,
  isWideLayout: true,
  isCoarsePointer: false,
  cores: 8,
  memoryGb: 8,
  saveData: false,
  effectiveType: "4g",
};

const TABLET: DeviceSignals = { ...DESKTOP, isCoarsePointer: true };

describe("which hero a device gets", () => {
  it("is the 3D scene on a capable desktop, also when the browser hides its cores, memory and network", () => {
    expect(heroPlan(DESKTOP)).toEqual({ kind: "scene" });
    expect(heroPlan({ prefersReducedMotion: false, isWideLayout: true, isCoarsePointer: false })).toEqual({ kind: "scene" });
  });

  it("is the poster with reduced motion or data saver, whatever the device", () => {
    expect(heroPlan({ ...DESKTOP, prefersReducedMotion: true })).toEqual({ kind: "poster", reason: "reduced-motion" });
    expect(heroPlan({ ...DESKTOP, saveData: true })).toEqual({ kind: "poster", reason: "save-data" });
    // Reduced motion is named first: the poster then stands still too.
    expect(heroPlan({ ...DESKTOP, prefersReducedMotion: true, saveData: true, isWideLayout: false })).toEqual({
      kind: "poster",
      reason: "reduced-motion",
    });
  });

  it("is the animated poster on a phone-sized screen, even a strong one", () => {
    expect(heroPlan({ ...TABLET, isWideLayout: false, cores: 12, memoryGb: 16 })).toEqual({ kind: "poster", reason: "narrow-screen" });
    expect(heroPlan({ ...DESKTOP, isWideLayout: false })).toEqual({ kind: "poster", reason: "narrow-screen" });
  });

  it("is the poster on a slow connection", () => {
    for (const effectiveType of ["slow-2g", "2g", "3g"]) {
      expect(heroPlan({ ...DESKTOP, effectiveType })).toEqual({ kind: "poster", reason: "slow-network" });
    }
    expect(heroPlan({ ...DESKTOP, effectiveType: "4g" })).toEqual({ kind: "scene" });
  });

  it("is the poster on a weak device: few cores or little memory", () => {
    expect(heroPlan({ ...DESKTOP, cores: 2 })).toEqual({ kind: "poster", reason: "low-power" });
    expect(heroPlan({ ...DESKTOP, memoryGb: 2 })).toEqual({ kind: "poster", reason: "low-power" });
    expect(heroPlan({ ...DESKTOP, cores: 4, memoryGb: 4 })).toEqual({ kind: "scene" });
  });

  it("asks more of a touch device: six cores and six gigabytes where the browser tells", () => {
    expect(heroPlan(TABLET)).toEqual({ kind: "scene" });
    expect(heroPlan({ ...TABLET, cores: 4 })).toEqual({ kind: "poster", reason: "low-power" });
    expect(heroPlan({ ...TABLET, memoryGb: 4 })).toEqual({ kind: "poster", reason: "low-power" });
    expect(heroPlan({ ...TABLET, cores: undefined, memoryGb: undefined })).toEqual({ kind: "scene" });
  });
});
