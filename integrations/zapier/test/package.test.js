'use strict';

const assert = require('node:assert/strict');
const { test } = require('node:test');
const packageJson = require('../package.json');

// zapier-platform-core 19.1.0 pins form-data 4.0.5, which has a CRLF
// injection in multipart field names (GHSA-hmw2-7cc7-3qxx, fixed in 4.0.6).
// The override holds the fixed version until the core raises its own pin.
function versionParts(version) {
  return String(version).split('.').map(Number);
}

test('form-data is held at a version without the CRLF injection', () => {
  const [major, minor, patch] = versionParts(packageJson.overrides['form-data']);
  assert.equal(major, 4);
  assert.ok(minor > 0 || patch >= 6, packageJson.overrides['form-data']);
});

test('the platform version follows the pinned core', () => {
  assert.match(packageJson.dependencies['zapier-platform-core'], /^\d+\.\d+\.\d+$/);
});
