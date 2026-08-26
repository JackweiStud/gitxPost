const test = require('node:test');
const assert = require('node:assert/strict');

const {
  parseCompactNumber,
  extractMetricsFromText,
  hasAnyMetric,
  detectPageGuard,
  parseArgs,
} = require('./scripts/x_metrics_cdp.js');

test('parseCompactNumber does not treat bookmark B as billion unit', () => {
  assert.equal(parseCompactNumber('40 Bookmarks'), 40);
  assert.equal(parseCompactNumber('2.6M Views'), 2600000);
  assert.equal(parseCompactNumber('1,085 Likes'), 1085);
});

test('extractMetricsFromText reads X engagement labels', () => {
  const text = [
    '79 replies',
    '131 reposts',
    '1,085 likes',
    '267.9K views',
    '807 bookmarks',
  ].join('\n');

  assert.deepEqual(extractMetricsFromText(text), {
    replies: 79,
    reposts: 131,
    likes: 1085,
    views: 267900,
    bookmarks: 807,
  });
});

test('hasAnyMetric rejects empty metric payloads', () => {
  assert.equal(hasAnyMetric({
    replies: null,
    reposts: null,
    likes: null,
    views: null,
    bookmarks: null,
  }), false);
  assert.equal(hasAnyMetric({
    replies: 0,
    reposts: 0,
    likes: 4,
    views: 75,
    bookmarks: 0,
  }), true);
});

test('detectPageGuard identifies login, challenge, and rate-limit states', () => {
  const login = detectPageGuard({
    title: 'X',
    text: 'Sign in to X to continue. JavaScript is not available.',
  });
  assert.equal(login.blocked, true);
  assert.equal(login.reason, 'login_required');
  assert.match(String(login.matched), /sign in to x/i);

  const challenge = detectPageGuard({
    title: 'Verify your identity / X',
    text: 'Please complete this challenge to help us confirm you are not a robot.',
  });
  assert.equal(challenge.blocked, true);
  assert.equal(challenge.reason, 'challenge_required');
  assert.match(String(challenge.matched), /verify your identity|complete this challenge/i);

  const limited = detectPageGuard({
    title: 'Rate limit exceeded / X',
    text: 'Something went wrong. Rate limit exceeded. Try again later.',
  });
  assert.equal(limited.blocked, true);
  assert.equal(limited.reason, 'rate_limited');
  assert.match(String(limited.matched), /rate limit/i);

  assert.deepEqual(detectPageGuard({
    title: 'Post / X',
    text: 'Composer 2.5 is now the most-chosen model in Cursor. 10 replies 20 likes',
  }), { blocked: false, reason: null, matched: null });

  const broken = detectPageGuard({
    title: 'OpenAI Developers (OpenAIDevs) / X',
    text: '出错了。请尝试重新加载。',
  });
  assert.equal(broken.blocked, true);
  assert.equal(broken.reason, 'timeline_error');

  const reload = detectPageGuard({
    title: 'X',
    text: 'Something went wrong. Please try reloading.',
  });
  assert.equal(reload.blocked, true);
  assert.equal(reload.reason, 'timeline_error');
});

test('detectPageGuard uses URL and notice, not tweet body, for hard guards', () => {
  const loginUrl = detectPageGuard({
    title: 'X',
    url: 'https://x.com/i/flow/login?redirect_after_login=%2Fnaval',
    text: 'whatever',
  });
  assert.equal(loginUrl.reason, 'login_required');
  assert.match(String(loginUrl.matched), /\/i\/flow\/login/);

  const accessUrl = detectPageGuard({
    title: 'X',
    url: 'https://x.com/account/access',
    text: 'Please try again later in this tweet.',
  });
  assert.equal(accessUrl.reason, 'challenge_required');
  assert.match(String(accessUrl.matched), /\/account\/access/);

  const tweetFalsePositive = detectPageGuard({
    title: 'aiDotEngineer / X',
    url: 'https://x.com/aiDotEngineer',
    text: 'We hit a rate limit at work. Please try again later.',
    tweetText: 'We hit a rate limit at work. Please try again later.',
    items: [{ statusId: '1' }],
  });
  assert.equal(tweetFalsePositive.blocked, false);

  const chineseNotice = detectPageGuard({
    title: 'X',
    url: 'https://x.com/opencode',
    notice: '操作过于频繁，请稍后再试。',
  });
  assert.equal(chineseNotice.reason, 'rate_limited');
  assert.match(String(chineseNotice.matched), /操作过于频繁/);
});

test('parseArgs supports conservative pacing options', () => {
  const parsed = parseArgs([
    '--delay-ms', '2000',
    '--jitter-ms', '500',
    '--retries', '2',
    '--continue-on-guard',
    'https://x.com/a/status/1',
  ]);

  assert.equal(parsed.options.delayMs, 2000);
  assert.equal(parsed.options.jitterMs, 500);
  assert.equal(parsed.options.retries, 2);
  assert.equal(parsed.options.stopOnGuard, false);
  assert.equal(parsed.options.backgroundTarget, true);
  assert.deepEqual(parsed.urls, ['https://x.com/a/status/1']);
});

test('parseArgs supports foreground debug mode', () => {
  const parsed = parseArgs(['--foreground', 'https://x.com/a/status/1']);
  assert.equal(parsed.options.backgroundTarget, false);
});
