import path from "node:path";

import { describe, expect, it } from "vitest";

import { describeSpec, matchSpecs, parseShard, planShards, readSpecFiles, specsOfShard, type SpecFile } from "./shards";

const E2E_DIRECTORY = path.resolve(__dirname, "..");

function spec(name: string, weight: number, sharesAdminState = false): SpecFile {
  return { name, weight, sharesAdminState };
}

describe("parseShard", () => {
  it("reads index/total and runs everything without a value", () => {
    expect(parseShard("2/4")).toEqual({ index: 2, total: 4 });
    expect(parseShard(" 1/1 ")).toEqual({ index: 1, total: 1 });
    expect(parseShard(undefined)).toBeNull();
    expect(parseShard("")).toBeNull();
  });

  it.each(["0/4", "5/4", "1/0", "two/4", "1-4", "1/4/2"])("refuses %s", (value) => {
    expect(() => parseShard(value)).toThrow(/E2E_SHARD/);
  });
});

describe("describeSpec", () => {
  it("weighs a spec by its tests and sees the admin sign-in", () => {
    const source = [
      'import { signInAsPlatformAdmin } from "./support/admin";',
      'test("one", async () => {});',
      '  test.skip("two", async () => {});',
      'test.describe("group", () => {});',
      "// test(...) in a comment is not at a line start",
    ].join("\n");

    expect(describeSpec("a.spec.ts", source)).toEqual({ name: "a.spec.ts", weight: 2, sharesAdminState: true });
    expect(describeSpec("b.spec.ts", "for (const x of xs) {}")).toEqual({ name: "b.spec.ts", weight: 1, sharesAdminState: false });
  });
});

describe("planShards", () => {
  it("keeps the specs that share the admin team in one shard", () => {
    const specs = [spec("a.spec.ts", 9), spec("b.spec.ts", 8), spec("admin-1.spec.ts", 1, true), spec("admin-2.spec.ts", 2, true), spec("c.spec.ts", 1)];

    const plan = planShards(specs, 3);

    expect(plan.filter((names) => names.includes("admin-1.spec.ts"))).toEqual([["admin-1.spec.ts", "admin-2.spec.ts", "c.spec.ts"]]);
    expect(plan).toEqual([["a.spec.ts"], ["b.spec.ts"], ["admin-1.spec.ts", "admin-2.spec.ts", "c.spec.ts"]]);
  });

  it("gives every spec to exactly one shard, balanced by weight", () => {
    const specs = Array.from({ length: 40 }, (_, index) => spec(`s${String(index).padStart(2, "0")}.spec.ts`, (index % 7) + 1));
    const plan = planShards(specs, 4);

    expect(plan.flat().sort()).toEqual(specs.map((item) => item.name));
    const weights = plan.map((names) => names.reduce((sum, name) => sum + specs.find((item) => item.name === name)!.weight, 0));
    expect(Math.max(...weights) - Math.min(...weights)).toBeLessThanOrEqual(7);
  });

  it("does not depend on the order the files were read in", () => {
    const specs = [spec("a.spec.ts", 3), spec("b.spec.ts", 3), spec("c.spec.ts", 2), spec("d.spec.ts", 1, true)];

    expect(planShards([...specs].reverse(), 2)).toEqual(planShards(specs, 2));
  });
});

describe("the suite's own specs", () => {
  const specs = readSpecFiles(E2E_DIRECTORY);

  it("split into four shards that together run every spec once", () => {
    const shards = [1, 2, 3, 4].map((index) => specsOfShard(specs, { index, total: 4 }));

    expect(shards.flat().sort()).toEqual(specs.map((item) => item.name));
    expect(shards.every((names) => names.length > 0)).toBe(true);
  });

  it("run every admin spec, the Tbilisi route tour among them, in the same shard", () => {
    const admin = specs.filter((item) => item.sharesAdminState).map((item) => item.name);
    const shards = planShards(specs, 4);

    expect(admin).toContain("tour-routes.spec.ts");
    expect(shards.filter((names) => admin.some((name) => names.includes(name)))).toHaveLength(1);
  });
});

describe("matchSpecs", () => {
  it("matches exactly the named files, never a longer name", () => {
    const pattern = matchSpecs(["inbox.spec.ts", "a11y.spec.ts"]);

    expect(pattern.test("/repo/web/e2e/inbox.spec.ts")).toBe(true);
    expect(pattern.test("C:\\repo\\web\\e2e\\a11y.spec.ts")).toBe(true);
    expect(pattern.test("/repo/web/e2e/public-a11y.spec.ts")).toBe(false);
    expect(pattern.test("/repo/web/e2e/inboxXspec.ts")).toBe(false);
    expect(matchSpecs([]).test("/repo/web/e2e/inbox.spec.ts")).toBe(false);
  });
});
