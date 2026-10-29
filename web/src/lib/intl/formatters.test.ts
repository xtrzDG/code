import { afterEach, describe, expect, it, vi } from "vitest";

import { numberFormat } from "./formatters";

describe("numberFormat", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("makes a formatter once per locale and options, and reuses it", () => {
    const made = vi.spyOn(Intl, "NumberFormat");
    const options = { style: "currency", currency: "EUR" } as const;
    const first = numberFormat("de", options);
    const second = numberFormat("de", { ...options });
    expect(second).toBe(first);
    expect(made).toHaveBeenCalledTimes(1);
    expect(second.format(1234.5)).toBe(new Intl.NumberFormat("de", options).format(1234.5));
  });

  it("keeps formatters of other locales and options apart", () => {
    expect(numberFormat("en", { maximumFractionDigits: 0 }).format(2.5)).toBe("3");
    expect(numberFormat("en", { maximumFractionDigits: 1 }).format(2.5)).toBe("2.5");
    expect(numberFormat("ru").format(1234.5)).not.toBe(numberFormat("en").format(1234.5));
  });
});
