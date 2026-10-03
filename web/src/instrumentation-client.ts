/**
 * Browser errors of the cabinet go to Sentry through the cabinet's own
 * tunnel (src/app/api/monitoring); the SDK loads only after the first one.
 */

import { reportClientError } from "@/lib/monitoring/clientReporter";

window.addEventListener("error", (event) => {
  void reportClientError(event.error ?? event.message);
});
window.addEventListener("unhandledrejection", (event) => {
  void reportClientError(event.reason);
});
