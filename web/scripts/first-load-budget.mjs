/**
 * The first-load budget (first-load-budget.json): how much gzipped
 * JavaScript a first visit to each listed page may download, and how big
 * the lazy 3D chunk (three.js and the scenes, fetched later on capable wide
 * screens only) may grow. `npm run measure:first-load -- --check` measures
 * the last build against it and fails over budget (CI, job "web-build").
 *
 * Kilobytes are 1024 bytes, as the measurement prints them. Pure: the
 * measuring script reads the file and passes the numbers in.
 */

const KILOBYTE = 1024;

/** The budget file's content, checked: `{ pages: { "/en": 192, … }, lazy3dChunk: 244 }`. */
export function parseBudget(raw) {
  if (typeof raw !== "object" || raw === null) {
    throw new Error("first-load budget: not an object");
  }
  const { pages, lazy3dChunk } = raw;
  if (typeof pages !== "object" || pages === null || Object.keys(pages).length === 0) {
    throw new Error("first-load budget: `pages` must list at least one page");
  }
  const entries = Object.entries(pages);
  for (const [page, kilobytes] of entries) {
    if (!page.startsWith("/")) {
      throw new Error(`first-load budget: page "${page}" must start with /`);
    }
    if (!isPositive(kilobytes)) {
      throw new Error(`first-load budget: ${page} needs a positive number of kilobytes`);
    }
  }
  if (!isPositive(lazy3dChunk)) {
    throw new Error("first-load budget: `lazy3dChunk` needs a positive number of kilobytes");
  }
  return { pages: Object.fromEntries(entries), lazy3dChunk };
}

function isPositive(value) {
  return typeof value === "number" && Number.isFinite(value) && value > 0;
}

const kilobytes = (bytes) => `${(bytes / KILOBYTE).toFixed(1)} KB`;

/**
 * What is over budget: every listed page must have been measured and stay
 * at or under its kilobytes; the build must have a lazy 3D chunk (no chunk
 * means three.js moved into a page's first load or the scene is gone), and
 * one only (a second copy of three.js would be downloaded twice), within
 * its kilobytes. An empty list: within budget.
 */
export function overBudget(budget, measured) {
  const problems = [];
  for (const [page, limit] of Object.entries(budget.pages)) {
    const result = measured.pages.find((entry) => entry.page === page);
    if (result === undefined) {
      problems.push(`${page}: not measured`);
    } else if (result.gzip > limit * KILOBYTE) {
      problems.push(`${page}: ${kilobytes(result.gzip)} gzip, over its budget of ${limit} KB`);
    }
  }
  if (measured.lazyChunks.length === 0) {
    problems.push("no lazy 3D chunk in the build: three.js must stay behind the scenes' import()");
  } else if (measured.lazyChunks.length > 1) {
    problems.push(`${measured.lazyChunks.length} chunks carry three.js (${measured.lazyChunks.map((chunk) => chunk.name).join(", ")}): one is shared by every scene`);
  }
  for (const chunk of measured.lazyChunks) {
    if (chunk.gzip > budget.lazy3dChunk * KILOBYTE) {
      problems.push(`lazy 3D chunk ${chunk.name}: ${kilobytes(chunk.gzip)} gzip, over its budget of ${budget.lazy3dChunk} KB`);
    }
  }
  return problems;
}
