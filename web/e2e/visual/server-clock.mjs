/**
 * The cabinet server's clock in a visual run (`node --import`, set by
 * playwright.config.ts with VISUAL_SERVER_TIME_MS): `Date` stands still at
 * the browser's moment (e2e/visual/clock.ts VISUAL_VIEW_TIME), as the
 * browser's own clock does (page.clock.setFixedTime), so a page rendered on
 * the server shows the same day and time as after hydration. Timers are
 * untouched: they run on the event loop, not on `Date`.
 */

const fixedMs = Number(process.env.VISUAL_SERVER_TIME_MS);
if (!Number.isFinite(fixedMs)) {
  throw new Error(`VISUAL_SERVER_TIME_MS must be milliseconds since the epoch, not ${process.env.VISUAL_SERVER_TIME_MS}.`);
}

const RealDate = Date;

/**
 * `new Date()` and `Date.now()` at the fixed moment; every other use as the
 * real `Date`, whose static members it carries as its own (Next.js copies
 * them when it wraps `Date` itself).
 */
const properties = Object.getOwnPropertyDescriptors(RealDate);
properties.now = { ...properties.now, value: () => fixedMs };
const FixedDate = Object.defineProperties(function Date(...args) {
  if (!new.target) {
    return new RealDate(fixedMs).toString();
  }
  return args.length === 0 ? new RealDate(fixedMs) : new RealDate(...args);
}, properties);

globalThis.Date = FixedDate;
