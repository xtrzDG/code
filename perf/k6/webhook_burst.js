// A burst of customer messages through Telegram webhooks: 200 a second
// (WEBHOOK_RATE) for a minute over the seeded restaurants' bots, each with
// the secret token Telegram sends. The webhook only stores the update and
// queues it; the worker answers (scripted model) and the outbox sends, so
// watch the queue drain in the worker log or the admin jobs page too.
//
//   k6 run -e MANIFEST=$PWD/perf/manifest.json perf/k6/webhook_burst.js
import http from "k6/http";
import { check } from "k6";
import { API_URL, pick, telegramBusinesses } from "./lib/manifest.js";

const RATE = Number(__ENV.WEBHOOK_RATE || 200);

export const options = {
  scenarios: {
    burst: {
      executor: "constant-arrival-rate",
      rate: RATE,
      timeUnit: "1s",
      duration: __ENV.DURATION || "1m",
      preAllocatedVUs: Math.max(50, RATE),
      maxVUs: RATE * 4,
    },
  },
  // Telegram waits for the answer and retries what it did not get; the
  // burst must be taken whole (no errors, nothing dropped) and acknowledged
  // well within that wait.
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000", "p(99)<3000"],
    dropped_iterations: ["count<100"],
  },
};

export default function () {
  const sequence = (__VU * 1000003 + __ITER) % 2147483647;
  const business = pick(telegramBusinesses, sequence);
  const chatId = 700000000 + (sequence % 50000);
  const update = {
    update_id: sequence,
    message: {
      message_id: sequence,
      date: Math.floor(Date.now() / 1000),
      chat: { id: chatId, type: "private" },
      from: { id: chatId, first_name: "Load" },
      text: "Hello! Are you open tonight?",
    },
  };
  const response = http.post(
    `${API_URL}/v1/channels/telegram/${business.telegram_channel_id}/webhook`,
    JSON.stringify(update),
    {
      headers: {
        "Content-Type": "application/json",
        "X-Telegram-Bot-Api-Secret-Token": business.telegram_webhook_secret,
      },
    },
  );
  check(response, { "webhook accepted": (r) => r.status === 200 });
}
