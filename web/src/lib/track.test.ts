import { describe, expect, it, vi } from "vitest";

import { FLUSH_DELAY_MS, MAX_BATCH, MAX_QUEUE, createTelemetryQueue, type TelemetryReport } from "./track";

const VITAL: TelemetryReport = {
  kind: "web_vital",
  metric: "lcp",
  value: 1800,
  route: "/b/[businessId]/inbox",
  device_class: "mobile",
};

function harness(status = 202, retryAfterSeconds?: number) {
  let clock = 1_000;
  const timers: { run: () => void; delay: number }[] = [];
  const sent: { reports: TelemetryReport[]; keepalive: boolean }[] = [];
  const send = vi.fn((reports: TelemetryReport[], keepalive: boolean) => {
    sent.push({ reports, keepalive });
    return Promise.resolve({ status, retryAfterSeconds });
  });
  const queue = createTelemetryQueue({
    send,
    now: () => clock,
    schedule: (run, delay) => timers.push({ run, delay }),
    cancel: () => undefined,
  });
  return {
    queue,
    sent,
    timers,
    advance: (ms: number) => {
      clock += ms;
    },
  };
}

describe("telemetry queue", () => {
  it("sends the reports of a few seconds together", async () => {
    const { queue, sent, timers } = harness();

    queue.track(VITAL);
    queue.track({ ...VITAL, metric: "cls", value: 900 });

    expect(sent).toHaveLength(0);
    expect(timers).toEqual([expect.objectContaining({ delay: FLUSH_DELAY_MS })]);
    timers[0]?.run();
    await vi.waitFor(() => expect(sent).toHaveLength(1));
    expect(sent[0]?.reports).toHaveLength(2);
    expect(queue.size()).toBe(0);
  });

  it("sends a full batch at once and splits what is over 50", async () => {
    const { queue, sent } = harness();

    for (let index = 0; index < MAX_BATCH; index += 1) {
      queue.track(VITAL);
    }
    await vi.waitFor(() => expect(sent).toHaveLength(1));
    expect(sent[0]?.reports).toHaveLength(MAX_BATCH);

    for (let index = 0; index < MAX_BATCH - 1; index += 1) {
      queue.track(VITAL);
    }
    await queue.flush(true);
    expect(sent[1]).toMatchObject({ keepalive: true });
    expect(sent[1]?.reports).toHaveLength(MAX_BATCH - 1);
  });

  it("goes quiet for the Retry-After of a 429 and drops what waits", async () => {
    const { queue, sent, advance } = harness(429, 30);

    queue.track(VITAL);
    await queue.flush();
    queue.track(VITAL);

    expect(sent).toHaveLength(1);
    expect(queue.size()).toBe(0);
    advance(30_000);
    queue.track(VITAL);
    expect(queue.size()).toBe(1);
  });

  it("keeps at most 200 reports and survives a failed send", async () => {
    const send = vi.fn(() => Promise.reject(new Error("offline")));
    const queue = createTelemetryQueue({ send, schedule: () => 0, cancel: () => undefined });

    for (let index = 0; index < MAX_QUEUE + 20; index += 1) {
      queue.track({ kind: "tunnel_step", step: "hours", action: "entered" });
    }
    await expect(queue.flush()).resolves.toBeUndefined();
    expect(send).toHaveBeenCalled();
  });
});
