#!/usr/bin/env node

const {
  CDPClient,
  openBlankTarget,
  closeTarget,
  detectPageGuard,
  sleep,
  jitterDelay,
} = require('./x_metrics_cdp.js');

const DEFAULT_PORT = 19222;
const DEFAULT_WAIT_MS = 10000;
const DEFAULT_MAX_SCROLLS = 3;
const DEFAULT_LIMIT_ITEMS = 8;
const DEFAULT_RETRIES = 1;
const DEFAULT_RETRY_DELAY_MS = 2500;
const DEFAULT_RETRY_JITTER_MS = 2500;

function normalizeHandle(raw) {
  return String(raw || '').replace(/^@+/, '').trim();
}

function buildProfileUrl(username, options = {}) {
  const handle = normalizeHandle(username);
  return `https://x.com/${handle}${options.withReplies ? '/with_replies' : ''}`;
}

function normalizeTweetUrl(rawHref, username) {
  if (!rawHref) return '';
  const href = String(rawHref);
  try {
    const url = new URL(href, 'https://x.com');
    const internalMatch = url.pathname.match(/^\/i\/status\/(\d+)/);
    const rawUserMatch = url.pathname.match(/^\/([^/]+)\/status\/(\d+)/);
    const userMatch = rawUserMatch && rawUserMatch[1] !== 'i' ? rawUserMatch : null;
    if (!internalMatch && !userMatch) return '';
    const author = userMatch ? userMatch[1] : normalizeHandle(username);
    const statusId = userMatch ? userMatch[2] : internalMatch[1];
    return `https://x.com/${author}/status/${statusId}`;
  } catch {
    return '';
  }
}

function buildExtractionExpression(username, limitItems) {
  const expected = JSON.stringify(normalizeHandle(username).toLowerCase());
  const limit = Number.isFinite(limitItems) ? Math.max(1, limitItems) : DEFAULT_LIMIT_ITEMS;
  return `(() => {
    const expected = ${expected};
    const limit = ${limit};

    function pathOf(href) {
      try {
        return new URL(href, location.origin).pathname || '';
      } catch {
        return href || '';
      }
    }

    function statusId(pathname) {
      const m = pathname.match(/\\/status\\/(\\d+)/);
      return m ? m[1] : null;
    }

    function authorFromPath(pathname) {
      const m = pathname.match(/^\\/([^/]+)\\/status\\/\\d+/);
      return m ? m[1] : '';
    }

    function cleanText(text) {
      return String(text || '').replace(/\\n{3,}/g, '\\n\\n').trim();
    }

    function firstUsefulLine(text) {
      const lines = cleanText(text).split('\\n').map((line) => line.trim()).filter(Boolean);
      return lines.find((line) => !/^(reply|repost|like|view|bookmark|share)$/i.test(line)) || '';
    }

    const pageText = document.body ? document.body.innerText || '' : '';
    const articles = Array.from(document.querySelectorAll('article[data-testid="tweet"], article'));
    const seen = new Set();
    const items = [];

    for (const article of articles) {
      const anchors = Array.from(article.querySelectorAll('a[href]'));
      let statusAnchor = null;
      let sid = '';
      let author = '';
      for (const anchor of anchors) {
        const pathname = pathOf(anchor.getAttribute('href') || '');
        const id = statusId(pathname);
        if (!id) continue;
        const candidateAuthor = authorFromPath(pathname);
        if (candidateAuthor && candidateAuthor.toLowerCase() !== expected) continue;
        statusAnchor = anchor;
        sid = id;
        author = candidateAuthor || expected;
        break;
      }
      if (!statusAnchor || !sid || seen.has(sid)) continue;
      seen.add(sid);

      const tweetText = cleanText(article.querySelector('[data-testid="tweetText"]')?.innerText || '');
      const fullText = cleanText(article.innerText || '');
      const text = tweetText || firstUsefulLine(fullText);
      const socialHead = fullText.split('\\n').slice(0, 4).join(' ');
      const pinned = /\\bPinned\\b|已置顶|置顶/.test(socialHead);
      const reposted = /\\bReposted\\b|转帖|转发/.test(socialHead);
      const timeEl = article.querySelector('time[datetime]');
      const datetime = timeEl ? timeEl.getAttribute('datetime') || '' : '';
      const href = statusAnchor.getAttribute('href') || '';

      items.push({
        username: author || expected,
        href,
        statusId: sid,
        datetime,
        text,
        fullText,
        pinned,
        reposted,
      });

      if (items.length >= limit) break;
    }

    return {
      title: document.title || '',
      text: pageText.slice(0, 8000),
      items,
    };
  })()`;
}

function convertExtractedItem(item, username) {
  const text = String(item.text || item.fullText || '').trim();
  const titlePrefix = item.pinned ? 'Pinned: ' : (item.reposted ? 'RT ' : '');
  return {
    title: `${titlePrefix}${text.split('\n').find(Boolean) || '推文'}`,
    link: normalizeTweetUrl(item.href, username),
    pub_date: item.datetime || '',
    description: text,
  };
}

function classifyErrorMessage(message) {
  const source = String(message || '').toLowerCase();
  if (/fetch failed|econnrefused|socket hang up|browser cdp websocket|did not expose websocket/.test(source)) {
    return { error_type: 'cdp_connect_failed', retryable: true };
  }
  if (/timeout|timed out|deadline/.test(source)) {
    return { error_type: 'cdp_timeout', retryable: true };
  }
  if (/no visible timeline/.test(source)) {
    return { error_type: 'no_visible_timeline', retryable: true };
  }
  if (/account doesn.?t exist|page doesn.?t exist|unavailable/.test(source)) {
    return { error_type: 'account_unavailable', retryable: false };
  }
  return { error_type: 'cdp_unknown_failed', retryable: false };
}

async function fetchProfileTimeline(username, options = {}) {
  const handle = normalizeHandle(username);
  const port = options.port || DEFAULT_PORT;
  const waitMs = options.waitMs || DEFAULT_WAIT_MS;
  const maxScrolls = Number.isFinite(options.maxScrolls) ? options.maxScrolls : DEFAULT_MAX_SCROLLS;
  const limitItems = Number.isFinite(options.limitItems) ? options.limitItems : DEFAULT_LIMIT_ITEMS;
  let target = null;
  let client = null;

  try {
    target = await openBlankTarget(port, { backgroundTarget: options.backgroundTarget !== false });
    client = new CDPClient(target.webSocketDebuggerUrl);
    await client.connect();
    await client.send('Page.enable');
    await client.send('Runtime.enable');
    await client.send('Page.navigate', { url: buildProfileUrl(handle, options) });

    const deadline = Date.now() + waitMs;
    let value = { title: '', text: '', items: [] };

    for (let round = 0; round <= maxScrolls; round += 1) {
      while (Date.now() <= deadline) {
        const evaluated = await client.send('Runtime.evaluate', {
          expression: buildExtractionExpression(handle, limitItems),
          returnByValue: true,
          awaitPromise: true,
        });
        value = evaluated.result && evaluated.result.value ? evaluated.result.value : value;
        const guard = detectPageGuard(value);
        if (guard.blocked) {
          return {
            ok: false,
            username: handle,
            error: `Page guard detected: ${guard.reason}`,
            error_type: guard.reason || 'page_guard',
            retryable: false,
            guard,
            items: [],
          };
        }
        if (value.items && value.items.length > 0) break;
        await sleep(750);
      }
      if (value.items && value.items.length >= limitItems) break;
      if (round >= maxScrolls) break;
      await client.send('Runtime.evaluate', {
        expression: 'window.scrollBy(0, Math.max(700, Math.floor(window.innerHeight * 0.9)))',
        returnByValue: false,
      });
      await sleep(jitterDelay(options.delayMs || 1200, options.jitterMs || 800));
    }

    const guard = detectPageGuard(value);
    if (guard.blocked) {
      return {
        ok: false,
        username: handle,
        error: `Page guard detected: ${guard.reason}`,
        error_type: guard.reason || 'page_guard',
        retryable: false,
        guard,
        items: [],
      };
    }

    const items = (value.items || [])
      .map((item) => convertExtractedItem(item, handle))
      .filter((item) => item.link && item.title);

    const emptyClass = classifyErrorMessage('No visible timeline items found');
    return {
      ok: items.length > 0,
      username: handle,
      error: items.length > 0 ? null : 'No visible timeline items found',
      error_type: items.length > 0 ? null : emptyClass.error_type,
      retryable: items.length > 0 ? false : emptyClass.retryable,
      guard: { blocked: false, reason: null },
      items,
    };
  } catch (error) {
    const classified = classifyErrorMessage(error.message);
    return {
      ok: false,
      username: handle,
      error: error.message,
      error_type: classified.error_type,
      retryable: classified.retryable,
      guard: { blocked: false, reason: null },
      items: [],
    };
  } finally {
    if (client) client.close();
    if (target) {
      if (target.id) await closeTarget(port, target.id);
      if (target.spawnedProcess) target.spawnedProcess.kill('SIGTERM');
    }
  }
}

async function fetchProfileTimelineWithRetry(username, options = {}) {
  const attempts = Math.max(0, options.retries || 0) + 1;
  let lastResult = null;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    const result = await fetchProfileTimeline(username, options);
    result.attempt = attempt;
    lastResult = result;
    if (result.ok) return result;
    if (result.guard && result.guard.blocked) return result;
    if (!result.retryable) return result;
    if (attempt < attempts) {
      await sleep(jitterDelay(options.retryDelayMs || DEFAULT_RETRY_DELAY_MS, options.retryJitterMs || DEFAULT_RETRY_JITTER_MS));
    }
  }

  return lastResult;
}

function parseArgs(argv) {
  const usernames = [];
  const options = {
    port: DEFAULT_PORT,
    waitMs: DEFAULT_WAIT_MS,
    maxScrolls: DEFAULT_MAX_SCROLLS,
    limitItems: DEFAULT_LIMIT_ITEMS,
    delayMs: 1200,
    jitterMs: 800,
    retries: DEFAULT_RETRIES,
    retryDelayMs: DEFAULT_RETRY_DELAY_MS,
    retryJitterMs: DEFAULT_RETRY_JITTER_MS,
    backgroundTarget: true,
    withReplies: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--port') {
      options.port = Number.parseInt(argv[++index], 10);
    } else if (arg === '--wait-ms') {
      options.waitMs = Number.parseInt(argv[++index], 10);
    } else if (arg === '--max-scrolls') {
      options.maxScrolls = Number.parseInt(argv[++index], 10);
    } else if (arg === '--limit-items') {
      options.limitItems = Number.parseInt(argv[++index], 10);
    } else if (arg === '--delay-ms') {
      options.delayMs = Number.parseInt(argv[++index], 10);
    } else if (arg === '--jitter-ms') {
      options.jitterMs = Number.parseInt(argv[++index], 10);
    } else if (arg === '--retries') {
      options.retries = Number.parseInt(argv[++index], 10);
    } else if (arg === '--retry-delay-ms') {
      options.retryDelayMs = Number.parseInt(argv[++index], 10);
    } else if (arg === '--retry-jitter-ms') {
      options.retryJitterMs = Number.parseInt(argv[++index], 10);
    } else if (arg === '--foreground') {
      options.backgroundTarget = false;
    } else if (arg === '--with-replies') {
      options.withReplies = true;
    } else if (arg === '--help' || arg === '-h') {
      options.help = true;
    } else {
      usernames.push(normalizeHandle(arg));
    }
  }

  return { usernames: usernames.filter(Boolean), options };
}

function printHelp() {
  console.log(`Usage:
  node scripts/x_profile_timeline_cdp.js [options] <username> [username...]

Output:
  JSON with visible X profile timeline items read through Chrome/CDP.

Safety:
  Uses your existing Chrome/CDP session. It reads visible DOM only; it does not
  call X API, click, like, repost, reply, solve challenges, or bypass guards.
  It stops on login, challenge, or rate-limit guard pages.`);
}

async function main() {
  const { usernames, options } = parseArgs(process.argv.slice(2));
  if (options.help || usernames.length === 0) {
    printHelp();
    process.exit(options.help ? 0 : 2);
  }

  const results = [];
  for (let index = 0; index < usernames.length; index += 1) {
    if (index > 0) await sleep(jitterDelay(options.delayMs, options.jitterMs));
    const result = await fetchProfileTimelineWithRetry(usernames[index], options);
    results.push(result);
    if (result.guard && result.guard.blocked) break;
  }

  console.log(JSON.stringify({
    ok: results.every((result) => result.ok),
    total: usernames.length,
    success: results.filter((result) => result.ok).length,
    failed: results.filter((result) => !result.ok).length,
    stoppedByGuard: (results.find((result) => result.guard && result.guard.blocked) || {}).error_type || null,
    results,
  }, null, 2));
}

if (require.main === module) {
  main().catch((error) => {
    console.error(JSON.stringify({ ok: false, error: error.message }, null, 2));
    process.exit(1);
  });
}

module.exports = {
  normalizeHandle,
  buildProfileUrl,
  normalizeTweetUrl,
  buildExtractionExpression,
  convertExtractedItem,
  classifyErrorMessage,
  parseArgs,
  fetchProfileTimeline,
  fetchProfileTimelineWithRetry,
};
