#!/usr/bin/env node
/**
 * The visual tests (e2e/visual, README "Visual tests and the review gate")
 * in the browser of Playwright's own image, so a screenshot renders the
 * same pixels on every machine (fonts, Chromium build, its rasterizer):
 *
 *   npm run e2e:visual                   # compare with the committed baselines
 *   npm run e2e:visual:update            # write the baselines that changed
 *   npm run e2e:visual -- new-business   # more arguments go to Playwright
 *   node scripts/visual-browser.mjs --image   # print the image (CI pulls it early)
 *
 * It starts `playwright run-server` in the pinned image (this checkout's
 * node_modules mounted read-only, so the server is exactly the runner's
 * version), runs `playwright test --project visual` against it with
 * VISUAL_BROWSER_WS, and removes the container. The browser reaches the
 * cabinet on this machine through the runner (`exposeNetwork`,
 * e2e/visual/project.ts). With VISUAL_BROWSER_WS already set, that browser
 * is used and no container is started.
 */

import { spawn, spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

/** Playwright's image for the version in package.json, pinned by digest (e2e/visual/visualBrowser.test.ts). */
export const VISUAL_BROWSER_IMAGE =
  "mcr.microsoft.com/playwright:v1.64.1-noble@sha256:47b510dd9230bf0b9bfc9b20102241e577ea7a99334ab4c3ca19f19770e9b8ea";
const SERVER_PORT = 3000;
const STARTUP_TIMEOUT_MS = 120_000;
const WEB_DIRECTORY = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

/** `docker run` arguments of the browser server: this user's node_modules, a random loopback port. */
export function dockerRunArguments({ name, nodeModules, image = VISUAL_BROWSER_IMAGE }) {
  return [
    "run",
    "--detach",
    "--rm",
    "--init",
    // Chromium's shared memory: the image's guidance for Chrome.
    "--ipc=host",
    "--name",
    name,
    "--user",
    "pwuser",
    "--publish",
    `127.0.0.1::${SERVER_PORT}`,
    "--volume",
    `${nodeModules}:/visual/node_modules:ro`,
    image,
    "node",
    "/visual/node_modules/playwright/cli.js",
    "run-server",
    "--port",
    String(SERVER_PORT),
    "--host",
    "0.0.0.0",
  ];
}

/** `playwright test` arguments: compare (`--update-snapshots=none`) or write the changed baselines. */
export function playwrightArguments(update, extra) {
  return [
    "playwright",
    "test",
    "--config",
    "e2e/playwright.config.ts",
    "--project",
    "visual",
    `--update-snapshots=${update ? "changed" : "none"}`,
    ...extra,
  ];
}

/** The host port Docker published for the server (`docker port` prints "127.0.0.1:49153"). */
export function publishedPort(output) {
  const match = /:(\d+)\s*$/m.exec(output.trim());
  if (!match) {
    throw new Error(`docker port printed no port: ${JSON.stringify(output)}`);
  }
  return Number(match[1]);
}

function docker(args) {
  const result = spawnSync("docker", args, { encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(`docker ${args[0]} failed: ${result.stderr || result.stdout}`);
  }
  return result.stdout;
}

async function waitForServer(url) {
  const deadline = Date.now() + STARTUP_TIMEOUT_MS;
  while (Date.now() < deadline) {
    try {
      if ((await fetch(url)).ok) {
        return;
      }
    } catch {
      // Not listening yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`The browser server at ${url} did not start within ${STARTUP_TIMEOUT_MS / 1000} s.`);
}

function runPlaywright(args, wsEndpoint) {
  return new Promise((resolve) => {
    const child = spawn("npx", args, {
      cwd: WEB_DIRECTORY,
      stdio: "inherit",
      env: { ...process.env, E2E_VISUAL: "1", VISUAL_BROWSER_WS: wsEndpoint },
    });
    child.on("exit", (code, signal) => resolve(code ?? (signal ? 1 : 0)));
  });
}

async function main(argv) {
  if (argv.includes("--image")) {
    process.stdout.write(`${VISUAL_BROWSER_IMAGE}\n`);
    return;
  }
  const update = argv.includes("--update");
  const extra = argv.filter((argument) => argument !== "--update");
  const args = playwrightArguments(update, extra);
  if (process.env.VISUAL_BROWSER_WS) {
    process.exit(await runPlaywright(args, process.env.VISUAL_BROWSER_WS));
  }
  const name = `visual-browser-${process.pid}`;
  docker(dockerRunArguments({ name, nodeModules: path.join(WEB_DIRECTORY, "node_modules") }));
  const remove = () => spawnSync("docker", ["rm", "--force", name], { stdio: "ignore" });
  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.on(signal, () => {
      remove();
      process.exit(130);
    });
  }
  let status = 1;
  try {
    const port = publishedPort(docker(["port", name, String(SERVER_PORT)]));
    await waitForServer(`http://127.0.0.1:${port}/`);
    status = await runPlaywright(args, `ws://127.0.0.1:${port}/`);
  } finally {
    remove();
  }
  process.exit(status);
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  await main(process.argv.slice(2));
}
