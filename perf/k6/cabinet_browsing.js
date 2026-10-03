// Owners and staff browsing the cabinet: dashboard, the conversation feed,
// a conversation card, bookings and availability, with think time between
// pages. Every virtual user is the owner of one seeded business.
//
//   k6 run -e MANIFEST=$PWD/perf/manifest.json -e API_URL=http://localhost:8000 \
//     perf/k6/cabinet_browsing.js
import http from "k6/http";
import { check, group, sleep } from "k6";
import { API_URL, businesses, dayFromToday, ownerHeaders, pick } from "./lib/manifest.js";

export const options = {
  scenarios: {
    browsing: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "1m", target: Number(__ENV.CABINET_USERS || 100) },
        { duration: __ENV.DURATION || "5m", target: Number(__ENV.CABINET_USERS || 100) },
        { duration: "30s", target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{page:dashboard}": ["p(95)<800"],
    "http_req_duration{page:conversations}": ["p(95)<500"],
    "http_req_duration{page:conversation}": ["p(95)<500"],
    "http_req_duration{page:bookings}": ["p(95)<500"],
    "http_req_duration{page:availability}": ["p(95)<500"],
  },
};

function get(path, business, page) {
  const response = http.get(`${API_URL}${path}`, {
    headers: ownerHeaders(business),
    tags: { page },
  });
  check(response, { [`${page} answers 200`]: (r) => r.status === 200 });
  return response;
}

export default function () {
  const business = pick(businesses, __VU - 1);
  const base = `/v1/businesses/${business.business_id}`;
  group("dashboard", () => get(`${base}/dashboard`, business, "dashboard"));
  sleep(1 + Math.random() * 2);
  const feed = get(`${base}/conversations`, business, "conversations");
  sleep(1 + Math.random() * 2);
  const listed = feed.status === 200 ? feed.json("items") : [];
  const conversationId = listed.length
    ? listed[__ITER % listed.length].id
    : pick(business.conversation_ids, __ITER);
  get(`${base}/conversations/${conversationId}`, business, "conversation");
  sleep(2 + Math.random() * 3);
  get(`${base}/bookings`, business, "bookings");
  sleep(1);
  get(`${base}/availability?date=${dayFromToday(__ITER % 14)}&party_size=2`, business, "availability");
  sleep(2 + Math.random() * 3);
}
