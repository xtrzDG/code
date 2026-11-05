// 1000 website-widget visitors (WIDGET_VISITORS) with an open chat: each
// polls for new answers every 4 seconds, as widget.js does, from its own
// client address, and now and then writes a message the scripted model
// answers after SCRIPTED_LLM_LATENCY_MS.
//
//   k6 run -e MANIFEST=$PWD/perf/manifest.json perf/k6/widget_polling.js
import http from "k6/http";
import { check, sleep } from "k6";
import { API_URL, clientAddress, pick, visitors } from "./lib/manifest.js";

const POLL_SECONDS = 4;
// One message about every two minutes per visitor.
const MESSAGE_CHANCE = Number(__ENV.MESSAGE_CHANCE || 1 / 30);

export const options = {
  scenarios: {
    visitors: {
      executor: "constant-vus",
      vus: Number(__ENV.WIDGET_VISITORS || 1000),
      duration: __ENV.DURATION || "5m",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{call:poll}": ["p(95)<150"],
    // The answer waits for the model: SCRIPTED_LLM_LATENCY_MS plus the rest.
    "http_req_duration{call:message}": [`p(95)<${Number(__ENV.SCRIPTED_LLM_LATENCY_MS || 800) + 1500}`],
  },
};

export default function () {
  // Visitors open their pages at different moments, not in one burst.
  if (__ITER === 0) {
    sleep(Math.random() * POLL_SECONDS);
  }
  const visitor = pick(visitors, __VU - 1);
  const url = `${API_URL}/v1/widget/${visitor.business_id}/messages`;
  const headers = {
    "X-Widget-Session-Key": visitor.session_key,
    "X-Forwarded-For": clientAddress(__VU),
  };
  const poll = http.get(`${url}?after=${visitor.latest_message_id}`, { headers, tags: { call: "poll" } });
  check(poll, { "poll answers 200": (r) => r.status === 200 });
  if (Math.random() < MESSAGE_CHANCE) {
    const sent = http.post(
      url,
      JSON.stringify({ session_key: visitor.session_key, text: "Do you have a table tonight?" }),
      { headers: { ...headers, "Content-Type": "application/json" }, tags: { call: "message" } },
    );
    // The message is stored and queued at once (202); a later poll brings the answer.
    check(sent, { "message accepted": (r) => r.status === 202 });
  }
  sleep(POLL_SECONDS - 0.25 + Math.random() * 0.5);
}
