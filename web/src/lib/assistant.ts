/**
 * Pure helpers of the Assistant section (app/b/[businessId]/assistant):
 * version statuses and actions, autotest results, publish refusals and the
 * test chat.
 */

import type { Schema } from "@/api/types";

export type AssistantVersionStatus = Schema<"AssistantVersionStatus">;
export type AssistantVersionSummary = Schema<"AssistantVersionSummary">;
export type AssistantVersionDetails = Schema<"AssistantVersionDetails">;
export type AssistantToolName = Schema<"AssistantToolName">;
export type AutotestRunView = Schema<"AutotestRunView">;
export type AutotestScenarioResult = Schema<"AutotestScenarioResultView">;
export type AutotestScenarioKind = Schema<"AutotestScenarioKind">;
export type AutotestOutcome = Schema<"AutotestOutcome">;
export type JudgeCriterion = Schema<"JudgeCriterion">;
export type MessageView = Schema<"MessageView">;

export const JUDGE_CRITERIA: readonly JudgeCriterion[] = [
  "facts_and_prices",
  "booking_data",
  "ai_disclosure",
  "handoff",
  "language",
];

export const AUTOTEST_KINDS: readonly AutotestScenarioKind[] = [
  "booking",
  "booking_out_of_hours",
  "cancellation",
  "price_question",
  "unknown_question",
  "discount_request",
  "rude_customer",
  "human_request",
  "prompt_injection",
  "emergency",
];

/** The judge's pass mark: a run passes with an average of at least 4 of 5. */
export const PASSING_SCORE = 4;

// --- Versions ---------------------------------------------------------------------

export type StatusTone = "neutral" | "accent" | "success" | "warning" | "danger" | "info";

export const VERSION_STATUS_TONES: Record<AssistantVersionStatus, StatusTone> = {
  draft: "neutral",
  testing: "info",
  ready: "accent",
  tests_failed: "danger",
  published: "success",
  archived: "neutral",
};

/** What an owner (or a platform admin) can do with a version in its status. */
export interface VersionActions {
  publish: boolean;
  /** Publish a version that did not pass its autotests (platform admins only). */
  forcePublish: boolean;
  runAutotests: boolean;
  rollback: boolean;
}

export function versionActions(
  status: AssistantVersionStatus,
  viewer: { isOwner: boolean; isPlatformAdmin: boolean },
): VersionActions {
  const canChange = viewer.isOwner || viewer.isPlatformAdmin;
  const untested = status === "draft" || status === "tests_failed";
  return {
    publish: canChange && status === "ready",
    forcePublish: viewer.isPlatformAdmin && untested,
    runAutotests: canChange && (untested || status === "ready"),
    rollback: canChange && status === "archived",
  };
}

/** Newest first (the API's order, kept stable for local updates). */
export function sortVersions<T extends Pick<AssistantVersionSummary, "version_number">>(versions: readonly T[]): T[] {
  return [...versions].sort((left, right) => right.version_number - left.version_number);
}

export function liveVersion<T extends Pick<AssistantVersionSummary, "status">>(versions: readonly T[]): T | undefined {
  return versions.find((version) => version.status === "published");
}

/**
 * The version the test chat should talk to by default: the live one, else
 * the newest ready, draft, under-test or failed one (the API itself only
 * falls back to ready and draft versions), else the newest of all.
 */
export function defaultTestVersionId(
  versions: readonly Pick<AssistantVersionSummary, "id" | "status" | "version_number">[],
): string | null {
  const sorted = sortVersions(versions);
  for (const status of ["published", "ready", "draft", "testing", "tests_failed"] as const) {
    const match = sorted.find((version) => version.status === status);
    if (match) {
      return match.id;
    }
  }
  return sorted[0]?.id ?? null;
}

/** "4.25" -> "4.3" in the UI language (scores are 1..5). */
export function formatScore(score: number, locale: string): string {
  return new Intl.NumberFormat(locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(score);
}

// --- Autotests --------------------------------------------------------------------

/**
 * Keep polling while the version is under test (the worker plays the run in
 * the background) or the run says it is still running.
 */
export function isRunInProgress(
  versionStatus: AssistantVersionStatus | undefined,
  run: (AutotestRunView & { status?: string }) | null | undefined,
): boolean {
  return versionStatus === "testing" || run?.status === "running";
}

export interface RunSummary {
  total: number;
  done: number;
  passed: number;
  failed: number;
  errored: number;
  /** 0..1 share of finished scenarios; 1 when nothing is planned. */
  progress: number;
}

export function summarizeRun(run: Pick<AutotestRunView, "scenario_count" | "results">): RunSummary {
  const results = run.results ?? [];
  const count = (outcome: AutotestOutcome) => results.filter((result) => result.outcome === outcome).length;
  const total = Math.max(run.scenario_count, results.length);
  return {
    total,
    done: results.length,
    passed: count("passed"),
    failed: count("failed"),
    errored: count("errored"),
    progress: total === 0 ? 1 : results.length / total,
  };
}

export type ResultFilter = "all" | "problems";

export function filterResults(
  results: readonly AutotestScenarioResult[],
  filter: { outcome: ResultFilter; language: string | "all" },
): AutotestScenarioResult[] {
  return results.filter(
    (result) =>
      (filter.outcome === "all" || result.outcome !== "passed") &&
      (filter.language === "all" || result.language === filter.language),
  );
}

/** Problems first (errored, failed), then passed; stable inside each outcome. */
export function sortResults(results: readonly AutotestScenarioResult[]): AutotestScenarioResult[] {
  const rank: Record<AutotestOutcome, number> = { errored: 0, failed: 1, passed: 2 };
  return results
    .map((result, index) => ({ result, index }))
    .sort((left, right) => rank[left.result.outcome] - rank[right.result.outcome] || left.index - right.index)
    .map((entry) => entry.result);
}

/** "price_question__en__2" -> 2: scenarios repeated for several items are numbered. */
export function scenarioNumber(scenarioKey: string): number | null {
  const match = /__(\d+)$/.exec(scenarioKey);
  return match ? Number(match[1]) : null;
}

export function resultLanguages(results: readonly Pick<AutotestScenarioResult, "language">[]): string[] {
  return [...new Set(results.map((result) => result.language))];
}

export function criterionScore(result: Pick<AutotestScenarioResult, "scores">, criterion: JudgeCriterion): number | null {
  return result.scores.find((score) => score.criterion === criterion)?.score ?? null;
}

/** Average judge score of one scenario, or null when it was not judged. */
export function scenarioAverage(result: Pick<AutotestScenarioResult, "scores">): number | null {
  if (result.scores.length === 0) {
    return null;
  }
  return result.scores.reduce((sum, score) => sum + score.score, 0) / result.scores.length;
}

export function scoreTone(score: number): StatusTone {
  if (score >= PASSING_SCORE) {
    return "success";
  }
  return score >= 3 ? "warning" : "danger";
}

const BOOKING_SCENARIO_KINDS: ReadonlySet<AutotestScenarioKind> = new Set(["booking", "booking_out_of_hours", "cancellation"]);

/**
 * Scenario kinds that apply to a version, as the API plans them: the
 * niche's kinds without repeats, booking ones only when the version books.
 */
export function applicableAutotestKinds(
  nicheKinds: readonly AutotestScenarioKind[],
  tools: readonly AssistantToolName[],
): AutotestScenarioKind[] {
  const canBook = tools.includes("create_booking");
  return nicheKinds.filter(
    (kind, index) => nicheKinds.indexOf(kind) === index && (canBook || !BOOKING_SCENARIO_KINDS.has(kind)),
  );
}

/**
 * The scenarios to send when the owner narrows a run: null means "all"
 * (only a run over every language and kind can make a version ready).
 */
export function narrowedSelection<T extends string>(chosen: readonly T[], available: readonly T[]): T[] | null {
  const unique = available.filter((value) => chosen.includes(value));
  return unique.length === available.length ? null : unique;
}

// --- Publishing -------------------------------------------------------------------

export type PublishRefusalReason =
  | "subscription"
  | "dpa"
  | "profile"
  | "autotests"
  | "testing"
  | "alreadyLive"
  | "archived"
  | "notArchived"
  | "adminOnly";

export interface PublishRefusal {
  reasons: PublishRefusalReason[];
  /** Profile gap kinds named by the API ("no_address", …). */
  gapKinds: string[];
}

const REFUSAL_PATTERNS: readonly [RegExp, PublishRefusalReason][] = [
  [/trial or pay|subscription/i, "subscription"],
  [/data processing agreement|\bDPA\b/i, "dpa"],
  [/complete the profile|what to add/i, "profile"],
  [/not passed the autotests|accept_failed_tests/i, "autotests"],
  [/is being tested|being tested/i, "testing"],
  [/already live/i, "alreadyLive"],
  [/is archived|use rollback/i, "archived"],
  [/only an earlier live version/i, "notArchived"],
  [/platform admin/i, "adminOnly"],
];

/**
 * Why the API refused to publish or roll back, from its (English) message.
 * The API answers 409/403 with one sentence listing what is missing, e.g.
 * "The assistant cannot go live yet: start the trial or pay for the
 * subscription; accept the data processing agreement (version …); complete
 * the profile (see what to add: no_address, no_faq)."
 */
export function classifyPublishRefusal(message: string | null | undefined): PublishRefusal {
  const text = message ?? "";
  const reasons: PublishRefusalReason[] = [];
  for (const [pattern, reason] of REFUSAL_PATTERNS) {
    if (pattern.test(text) && !reasons.includes(reason)) {
      reasons.push(reason);
    }
  }
  const gapList = /what to add:\s*([a-z_,\s]+)/i.exec(text)?.[1] ?? "";
  const gapKinds = gapList
    .split(",")
    .map((kind) => kind.trim())
    .filter((kind) => /^[a-z_]+$/.test(kind));
  // "Only a platform admin may publish a version that has not passed the
  // autotests (accept_failed_tests)" is one reason, not two.
  return {
    reasons: reasons.includes("adminOnly") ? reasons.filter((reason) => reason !== "autotests") : reasons,
    gapKinds,
  };
}

// --- Test chat ----------------------------------------------------------------------

/** A test chat session key the API accepts: ^[A-Za-z0-9][A-Za-z0-9_-]*$, at most 64. */
export function newSessionKey(now: number = Date.now(), random: () => number = Math.random): string {
  const suffix = Math.floor(random() * 36 ** 6)
    .toString(36)
    .padStart(6, "0");
  return `web-${now.toString(36)}-${suffix}`;
}

const SESSION_KEY = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;

export function isSessionKey(value: unknown): value is string {
  return typeof value === "string" && SESSION_KEY.test(value);
}

/** Tool call input or result as readable JSON; text that is not JSON stays as it is. */
export function prettyJson(text: string): string {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}

/** The test chat remembered in the browser tab, so a reload keeps the conversation. */
export interface StoredTestChat {
  sessionKey: string;
  versionId: string | null;
  conversationId: string | null;
}

export function parseStoredTestChat(raw: string | null): StoredTestChat | null {
  if (!raw) {
    return null;
  }
  try {
    const value = JSON.parse(raw) as Partial<StoredTestChat>;
    if (!isSessionKey(value.sessionKey)) {
      return null;
    }
    return {
      sessionKey: value.sessionKey,
      versionId: typeof value.versionId === "string" ? value.versionId : null,
      conversationId: typeof value.conversationId === "string" ? value.conversationId : null,
    };
  } catch {
    return null;
  }
}

/** Messages shown in the chat: customer and assistant lines (system notes too). */
export function chatMessages(messages: readonly MessageView[]): MessageView[] {
  return [...messages].sort((left, right) => left.created_at - right.created_at);
}
