'use strict';

const packageJson = require('./package.json');
const authentication = require('./authentication');
const { explainErrors, includeApiKey } = require('./lib/api');
const createBooking = require('./creates/create_booking');
const createLead = require('./creates/create_lead');
const triggers = require('./triggers');

// The Zapier app of Assistant Workshop (integrations/zapier/README.md).
module.exports = {
  version: packageJson.version,
  platformVersion: packageJson.dependencies['zapier-platform-core'],
  authentication,
  beforeRequest: [includeApiKey],
  afterResponse: [explainErrors],
  triggers,
  creates: {
    [createBooking.key]: createBooking,
    [createLead.key]: createLead,
  },
  searches: {},
  resources: {},
};
