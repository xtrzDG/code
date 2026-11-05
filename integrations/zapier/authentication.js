'use strict';

const { apiUrl } = require('./lib/api');

// An API key from Settings → Integrations → API keys. The connection is
// tested against `GET /v1/public-api/me`, which also names it.
module.exports = {
  type: 'custom',
  fields: [
    {
      key: 'api_key',
      label: 'API key',
      required: true,
      type: 'password',
      helpText:
        'Create a key in Assistant Workshop under Settings → Integrations → API keys. ' +
        'Give it the scopes of the triggers and actions you use (for triggers: `webhooks:manage`).',
    },
  ],
  test: async (z) => {
    const response = await z.request({ url: apiUrl('/me') });
    return response.data;
  },
  connectionLabel: '{{business_name}} ({{api_key_name}})',
};
