'use strict';

// The public API of Assistant Workshop as this app calls it: the base
// address (set per app version with `zapier env:set 1.0.0
// WORKSHOP_API_URL=https://…`), the key on every request and errors in
// words a Zap's owner understands.

const PUBLIC_API_PATH = '/v1/public-api';

function apiUrl(path) {
  const base = (process.env.WORKSHOP_API_URL || '').replace(/\/+$/, '');
  if (!base.startsWith('https://')) {
    throw new Error(
      'WORKSHOP_API_URL is not set to the https address of the API.'
    );
  }
  return `${base}${PUBLIC_API_PATH}${path}`;
}

function includeApiKey(request, z, bundle) {
  const apiKey = bundle.authData && bundle.authData.api_key;
  if (apiKey) {
    request.headers = request.headers || {};
    request.headers.Authorization = `Bearer ${apiKey}`;
  }
  return request;
}

// The API answers errors as {error, message, details}; a refused key is
// an authentication problem Zapier asks the user to reconnect for.
function explainErrors(response, z) {
  if (response.status < 400) {
    return response;
  }
  const body = readJson(response);
  const message = (body && body.message) || `HTTP ${response.status}`;
  if (response.status === 401) {
    throw new z.errors.RefreshAuthError(message);
  }
  if (response.status === 429) {
    const seconds = Number(response.getHeader('retry-after')) || 60;
    throw new z.errors.ThrottledError(message, seconds);
  }
  throw new z.errors.Error(message, (body && body.error) || 'api_error', response.status);
}

function readJson(response) {
  if (response.data !== undefined) {
    return response.data;
  }
  try {
    return JSON.parse(response.content);
  } catch {
    return null;
  }
}

module.exports = { PUBLIC_API_PATH, apiUrl, includeApiKey, explainErrors, readJson };
