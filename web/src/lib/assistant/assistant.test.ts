import { describe, expect, it } from "vitest";

import { defaultTestVersionId, liveVersion, sortVersions, versionActions } from "./versions";
import {
  applicableAutotestKinds,
  criterionScore,
  filterResults,
  formatScore,
  isRunInProgress,
  narrowedSelection,
  resultLanguages,
  scenarioAverage,
  scenarioNumber,
  scoreTone,
  sortResults,
  summarizeRun,
  type AutotestRunView,
  type AutotestScenarioResult,
} from "./autotests";
import { blockingChecks, checkState, isTestingRefusal, refusalReasons, type GoLiveCheck } from "./goLive";
import { isSessionKey, newSessionKey, parseStoredTestChat, prettyJson } from "./testChat";

const version = (id: string, versionNumber: number, status: "draft" | "testing" | "ready" | "tests_failed" | "published" | "archived") => ({
  id,
  version_number: versionNumber,
  status,
});

const result = (key: string, outcome: AutotestScenarioResult["outcome"], language = "en", scores: number[] = []): AutotestScenarioResult => ({
  scenario_key: key,
  kind: "booking",
  language,
  outcome,
  scores: scores.map((score, index) => ({
    criterion: (["facts_and_prices", "booking_data", "ai_disclosure", "handoff", "language"] as const)[index] ?? "language",
    score,
  })),
  judge_notes: [],
  check_notes: [],
  transcript: [],
  cost_micro_usd: 0,
});

describe("versions", () => {
  it("offers the actions a status allows", () => {
    const owner = { isOwner: true, isPlatformAdmin: false };
    const staff = { isOwner: false, isPlatformAdmin: false };
    const admin = { isOwner: false, isPlatformAdmin: true };
    expect(versionActions("ready", owner)).toEqual({ publish: true, forcePublish: false, runAutotests: true, rollback: false });
    expect(versionActions("tests_failed", owner)).toEqual({ publish: false, forcePublish: false, runAutotests: true, rollback: false });
    expect(versionActions("tests_failed", admin).forcePublish).toBe(true);
    expect(versionActions("draft", admin).forcePublish).toBe(true);
    expect(versionActions("ready", admin).forcePublish).toBe(false);
    expect(versionActions("archived", owner)).toEqual({ publish: false, forcePublish: false, runAutotests: false, rollback: true });
    expect(versionActions("testing", owner)).toEqual({ publish: false, forcePublish: false, runAutotests: false, rollback: false });
    expect(versionActions("published", owner).runAutotests).toBe(false);
    expect(versionActions("ready", staff)).toEqual({ publish: false, forcePublish: false, runAutotests: false, rollback: false });
  });

  it("sorts newest first and finds the live version", () => {
    const versions = [version("a", 1, "archived"), version("c", 3, "ready"), version("b", 2, "published")];
    expect(sortVersions(versions).map((item) => item.id)).toEqual(["c", "b", "a"]);
    expect(liveVersion(versions)?.id).toBe("b");
    expect(liveVersion([version("a", 1, "draft")])).toBeUndefined();
  });

  it("chooses the version the test chat talks to", () => {
    // The newest version that is not archived, as the API picks it.
    expect(defaultTestVersionId([version("a", 1, "published"), version("b", 2, "ready")])).toBe("b");
    expect(defaultTestVersionId([version("a", 1, "ready"), version("b", 2, "published")])).toBe("b");
    expect(defaultTestVersionId([version("a", 1, "draft"), version("b", 2, "tests_failed")])).toBe("b");
    expect(defaultTestVersionId([version("a", 1, "testing"), version("b", 2, "archived")])).toBe("a");
    expect(defaultTestVersionId([version("a", 1, "archived"), version("b", 2, "archived")])).toBe("b");
    expect(defaultTestVersionId([])).toBeNull();
  });

  it("formats scores with one decimal in the UI language", () => {
    expect(formatScore(4.25, "en")).toBe("4.3");
    expect(formatScore(4, "ru")).toBe("4,0");
  });
});

describe("autotests", () => {
  const run = (results: AutotestScenarioResult[], scenarioCount = results.length): AutotestRunView => ({
    id: "run",
    business_id: "business",
    assistant_version_id: "version",
    version_status: "testing",
    scenario_count: scenarioCount,
    passed_count: results.filter((item) => item.outcome === "passed").length,
    pass_rate: 0,
    is_passed: false,
    is_full_coverage: false,
    status: "finished",
    cost_micro_usd: 0,
    created_at: 0,
    updated_at: 0,
    results,
  });

  it("polls while the version is under test or the run is running", () => {
    expect(isRunInProgress("testing", null)).toBe(true);
    expect(isRunInProgress("ready", run([]))).toBe(false);
    expect(isRunInProgress("draft", { ...run([]), status: "running" })).toBe(true);
    expect(isRunInProgress(undefined, undefined)).toBe(false);
  });

  it("summarizes outcomes and progress", () => {
    const summary = summarizeRun(run([result("a", "passed"), result("b", "failed"), result("c", "errored")], 6));
    expect(summary).toEqual({ total: 6, done: 3, passed: 1, failed: 1, errored: 1, progress: 0.5 });
    expect(summarizeRun(run([])).progress).toBe(1);
  });

  it("filters, sorts and lists languages of results", () => {
    const results = [result("a", "passed", "ka"), result("b", "failed", "en"), result("c", "errored", "ka"), result("d", "failed", "ka")];
    expect(filterResults(results, { outcome: "problems", language: "all" }).map((item) => item.scenario_key)).toEqual(["b", "c", "d"]);
    expect(filterResults(results, { outcome: "all", language: "ka" }).map((item) => item.scenario_key)).toEqual(["a", "c", "d"]);
    expect(sortResults(results).map((item) => item.scenario_key)).toEqual(["c", "b", "d", "a"]);
    expect(resultLanguages(results)).toEqual(["ka", "en"]);
  });

  it("numbers repeated scenarios", () => {
    expect(scenarioNumber("price_question__en__2")).toBe(2);
    expect(scenarioNumber("price_question__pt-br__13")).toBe(13);
    expect(scenarioNumber("booking__ka")).toBeNull();
  });

  it("reads judge scores", () => {
    const judged = result("a", "passed", "en", [5, 4, 3]);
    expect(criterionScore(judged, "booking_data")).toBe(4);
    expect(criterionScore(judged, "language")).toBeNull();
    expect(scenarioAverage(judged)).toBe(4);
    expect(scenarioAverage(result("b", "errored"))).toBeNull();
    expect(scoreTone(4.5)).toBe("success");
    expect(scoreTone(3)).toBe("warning");
    expect(scoreTone(2)).toBe("danger");
  });

  it("plans booking scenarios only for versions that book", () => {
    const niche = ["booking", "price_question", "cancellation", "price_question", "emergency"] as const;
    expect(applicableAutotestKinds(niche, ["search_knowledge", "create_booking"])).toEqual([
      "booking",
      "price_question",
      "cancellation",
      "emergency",
    ]);
    expect(applicableAutotestKinds(niche, ["search_knowledge", "create_lead"])).toEqual(["price_question", "emergency"]);
  });

  it("sends a narrowed selection only when something was left out", () => {
    expect(narrowedSelection(["ka", "en"], ["en", "ka"])).toBeNull();
    expect(narrowedSelection(["ka"], ["en", "ka"])).toEqual(["ka"]);
    expect(narrowedSelection(["xx"], ["en"])).toEqual([]);
  });
});

describe("going live", () => {
  const refusal = (status: number, reasons: { code: string; message?: string; details?: string[] }[]) => ({
    status,
    reasons: reasons.map((reason) => ({ message: "", details: [], ...reason })),
  });

  it("reads the reason codes of a refused publish or rollback", () => {
    const reasons = refusalReasons(
      refusal(409, [
        { code: "subscription_or_trial", details: ["none"] },
        { code: "profile_gaps", details: ["no_address", "no_opening_hours"] },
        { code: "something_new", message: "A reason the cabinet does not know." },
      ]),
    );
    expect(reasons).toEqual([
      { code: "subscription_or_trial", message: "", details: ["none"] },
      { code: "profile_gaps", message: "", details: ["no_address", "no_opening_hours"] },
      { code: null, message: "A reason the cabinet does not know.", details: [] },
    ]);
    expect(refusalReasons(refusal(403, [{ code: "force_publish_admin_only" }]))[0]?.code).toBe("force_publish_admin_only");
  });

  it("ignores other errors and answers without reasons", () => {
    expect(refusalReasons(refusal(502, [{ code: "dpa" }]))).toEqual([]);
    expect(refusalReasons(refusal(409, []))).toEqual([]);
    expect(refusalReasons(null)).toEqual([]);
  });

  it("tells a version under test from an untested one", () => {
    expect(isTestingRefusal({ code: "autotests", details: ["testing", "running"] })).toBe(true);
    expect(isTestingRefusal({ code: "autotests", details: ["tests_failed", "finished"] })).toBe(false);
    expect(isTestingRefusal({ code: "dpa", details: ["testing"] })).toBe(false);
  });

  it("shows each check as done, missing, a warning or in progress", () => {
    const check = (code: GoLiveCheck["code"], isOk: boolean, isBlocking: boolean, details: string[] = []) => ({
      code,
      is_ok: isOk,
      is_blocking: isBlocking,
      details,
    });
    expect(checkState(check("dpa", true, true))).toBe("ok");
    expect(checkState(check("dpa", false, true))).toBe("missing");
    expect(checkState(check("voice_configuration", false, false))).toBe("warning");
    expect(checkState(check("autotests", false, true, ["testing", "running"]))).toBe("pending");
    expect(checkState(check("autotests", false, true, ["draft"]))).toBe("missing");
    expect(
      blockingChecks([check("dpa", false, true), check("voice_configuration", false, false), check("staff_contact", true, true)]).map(
        (item) => item.code,
      ),
    ).toEqual(["dpa"]);
  });
});

describe("test chat", () => {
  it("makes session keys the API accepts", () => {
    const key = newSessionKey(1_790_000_000_000, () => 0.5);
    expect(isSessionKey(key)).toBe(true);
    expect(key.length).toBeLessThanOrEqual(64);
    expect(newSessionKey(1, () => 0)).not.toBe(newSessionKey(1, () => 0.99));
    expect(isSessionKey("-bad")).toBe(false);
    expect(isSessionKey("a".repeat(65))).toBe(false);
  });

  it("restores only a valid stored chat", () => {
    expect(parseStoredTestChat(JSON.stringify({ sessionKey: "web-1", versionId: "v", conversationId: null }))).toEqual({
      sessionKey: "web-1",
      versionId: "v",
      conversationId: null,
    });
    expect(parseStoredTestChat(JSON.stringify({ sessionKey: "bad key" }))).toBeNull();
    expect(parseStoredTestChat("{not json")).toBeNull();
    expect(parseStoredTestChat(null)).toBeNull();
  });

  it("pretty-prints tool call JSON and keeps other text", () => {
    expect(prettyJson('{"a":1}')).toBe('{\n  "a": 1\n}');
    expect(prettyJson("not json")).toBe("not json");
  });
});
