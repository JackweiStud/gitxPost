const test = require('node:test');
const assert = require('node:assert/strict');

const {
  normalizeHandle,
  buildProfileUrl,
  normalizeTweetUrl,
  convertExtractedItem,
  classifyErrorMessage,
  parseArgs,
} = require('./scripts/x_profile_timeline_cdp.js');

test('normalizes profile handles and URLs', () => {
  assert.equal(normalizeHandle('@naval'), 'naval');
  assert.equal(buildProfileUrl('naval'), 'https://x.com/naval');
  assert.equal(buildProfileUrl('naval', { withReplies: true }), 'https://x.com/naval/with_replies');
  assert.equal(normalizeTweetUrl('/naval/status/123', 'naval'), 'https://x.com/naval/status/123');
  assert.equal(normalizeTweetUrl('https://x.com/i/status/456', 'naval'), 'https://x.com/naval/status/456');
});

test('converts extracted DOM rows into radar items', () => {
  assert.deepEqual(convertExtractedItem({
    href: '/naval/status/123',
    datetime: '2026-08-22T01:02:03.000Z',
    text: 'hello\nworld',
  }, 'naval'), {
    title: 'hello',
    link: 'https://x.com/naval/status/123',
    pub_date: '2026-08-22T01:02:03.000Z',
    description: 'hello\nworld',
  });

  assert.equal(convertExtractedItem({ href: '/naval/status/123', text: 'old', pinned: true }, 'naval').title, 'Pinned: old');
  assert.equal(convertExtractedItem({ href: '/naval/status/123', text: 'reshare', reposted: true }, 'naval').title, 'RT reshare');
});

test('classifies retryable CDP failures', () => {
  assert.deepEqual(classifyErrorMessage('fetch failed'), {
    error_type: 'cdp_connect_failed',
    retryable: true,
  });
  assert.deepEqual(classifyErrorMessage('No visible timeline items found'), {
    error_type: 'no_visible_timeline',
    retryable: true,
  });
  assert.deepEqual(classifyErrorMessage('This account is unavailable'), {
    error_type: 'account_unavailable',
    retryable: false,
  });
});

test('parseArgs supports conservative retry options', () => {
  const parsed = parseArgs([
    '--retries', '2',
    '--retry-delay-ms', '3000',
    '--retry-jitter-ms', '1000',
    'naval',
  ]);

  assert.equal(parsed.options.retries, 2);
  assert.equal(parsed.options.retryDelayMs, 3000);
  assert.equal(parsed.options.retryJitterMs, 1000);
  assert.deepEqual(parsed.usernames, ['naval']);
});
