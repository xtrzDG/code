/**
 * "Next, when you are ready" at the end of the tunnel, read from the
 * guided setup (GET …/setup) and the channels: adding prices when the
 * offer step was skipped, connecting the messengers that are not connected
 * yet (none when they all are), then teaching new answers and following
 * the conversations. Pure; the finale screen renders it.
 */

import type { Schema } from "@/api/types";
import type { BusinessPage } from "@/lib/navigation";

type ChannelKind = Schema<"ChannelKind">;

/** The messengers the finale suggests connecting, most asked for first. */
export const SUGGESTED_CHANNELS: readonly ChannelKind[] = ["whatsapp", "instagram", "telegram", "messenger"];

/** How many missing messengers the line names ("Connect WhatsApp and Instagram"). */
const NAMED_CHANNELS = 2;

export type FinaleNextKey = "offer" | "channels" | "knowledge" | "messages";

export interface FinaleNextStep {
  key: FinaleNextKey;
  /** The cabinet page it opens ("inbox": its All view). */
  page: BusinessPage;
  /** For "channels": the messengers to name, in order. */
  channels?: readonly ChannelKind[];
}

function isSkipped(setup: Schema<"SetupView">, code: Schema<"SetupStepCode">): boolean {
  return setup.steps.some((step) => step.code === code && step.status === "skipped");
}

export function finaleNextSteps(setup: Schema<"SetupView">, connected: readonly ChannelKind[]): FinaleNextStep[] {
  const steps: FinaleNextStep[] = [];
  if (isSkipped(setup, "offer")) {
    steps.push({ key: "offer", page: "assistant/knowledge" });
  }
  const missing = SUGGESTED_CHANNELS.filter((channel) => !connected.includes(channel));
  if (missing.length > 0) {
    steps.push({ key: "channels", page: "assistant/channels", channels: missing.slice(0, NAMED_CHANNELS) });
  }
  steps.push({ key: "knowledge", page: "assistant/knowledge" }, { key: "messages", page: "inbox" });
  return steps;
}
