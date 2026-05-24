#!/usr/bin/env node

const path = require('node:path');
const DEFAULT_PORT = 19222;
const DEFAULT_NAVIGATE_WAIT_MS = 7500;
const DEFAULT_DELAY_MS = 1500;
const DEFAULT_JITTER_MS = 1500;
const DEFAULT_RETRIES = 1;

function parseCompactNumber(raw) {
  if (!raw) return null;
  const value = String(raw).replace(/,/g, '').trim();
  const match = value.match(/([0-9]+(?:\.[0-9]+)?)(?:\s*([KMB万千])\b)?/i);
  if (!match) return null;

  const number = Number.parseFloat(match[1]);
  const unit = (match[2] || '').toLowerCase();
  const multiplier =
    unit === 'k' || unit === '千' ? 1_000 :
    unit === 'm' ? 1_000_000 :
    unit === 'b' ? 1_000_000_000 :
    unit === '万' ? 10_000 :
    1;

  return Math.round(number * multiplier);
}

function findMetric(text, names) {
  for (const name of names) {
    const regex = new RegExp(
      `([0-9][0-9,]*(?:\\.[0-9]+)?\\s*(?:K|M|B|万|千)?)(?:\\s+)?${name}`,
      'i',
    );
    const match = text.match(regex);
    if (match) return parseCompactNumber(match[1]);
  }
  return null;
}

function extractMetricsFromText(text) {
  const source = String(text || '');
  return {
    replies: findMetric(source, ['repl(?:y|ies)', '回复']),
    reposts: findMetric(source, ['repost(?:s)?', 'retweet(?:s)?', '转帖', '转发']),
    likes: findMetric(source, ['like(?:s)?', '喜欢']),
    views: findMetric(source, ['view(?:s)?', '次查看', '查看']),
    bookmarks: findMetric(source, ['bookmark(?:s)?', '书签']),
  };
}

function hasAnyMetric(metrics) {
  return Object.values(metrics || {}).some((value) => Number.isFinite(value));
}

function detectPageGuard(page) {
  const title = String((page && page.title) || '').toLowerCase();
  const text = String((page && page.text) || '').toLowerCase();
  const source = `${title}\n${text}`;

  if (/rate limit|too many requests|try again later|temporarily restricted|temporarily blocked/.test(source)) {
    return { blocked: true, reason: 'rate_limited' };
  }
  if (/captcha|verify you are human|unusual activity|automated requests|confirm you.?re not a robot/.test(source)) {
    return { blocked: true, reason: 'challenge_required' };
  }
  if (/sign in to x|log in to x|login to x|create your account|join x today|javascript is not available/.test(source)) {
    return { blocked: true, reason: 'login_required' };
  }
  if (/this account doesn.?t exist|this post is unavailable|page doesn.?t exist/.test(source)) {
    return { blocked: true, reason: 'unavailable' };
  }

  return { blocked: false, reason: null };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, Math.max(0, ms)));
}

function jitterDelay(baseMs, jitterMs) {
  const base = Number.isFinite(baseMs) ? baseMs : 0;
  const jitter = Number.isFinite(jitterMs) ? jitterMs : 0;
  return base + Math.floor(Math.random() * (jitter + 1));
}

class CDPClient {
  constructor(webSocketDebuggerUrl) {
    this.webSocketDebuggerUrl = webSocketDebuggerUrl;
    this.nextId = 0;
    this.pending = new Map();
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.webSocketDebuggerUrl);
      this.ws.onopen = () => resolve();
      this.ws.onerror = reject;
      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (!message.id || !this.pending.has(message.id)) return;

        const { resolve: done, reject: fail } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) {
          fail(new Error(JSON.stringify(message.error)));
        } else {
          done(message.result);
        }
      };
    });
  }

  send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = ++this.nextId;
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    try {
      this.ws.close();
    } catch {
      // Best effort cleanup only.
    }
  }
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`${url} failed: HTTP ${response.status}`);
  }
  return response.json();
}

async function findTargetById(port, targetId) {
  const targets = await fetchJson(`http://127.0.0.1:${port}/json/list`);
  return targets.find((target) => target.id === targetId) || null;
}

async function createBackgroundTarget(port) {
  const version = await fetchJson(`http://127.0.0.1:${port}/json/version`);
  if (!version.webSocketDebuggerUrl) {
    throw new Error('Browser CDP websocket is not available');
  }

  const browserClient = new CDPClient(version.webSocketDebuggerUrl);
  await browserClient.connect();
  try {
    const created = await browserClient.send('Target.createTarget', {
      url: 'about:blank',
      background: true,
    });
    const targetId = created.targetId;
    for (let attempt = 0; attempt < 20; attempt += 1) {
      const target = await findTargetById(port, targetId);
      if (target && target.webSocketDebuggerUrl) return target;
      await sleep(100);
    }
    throw new Error(`Background target ${targetId} did not expose websocket`);
  } finally {
    browserClient.close();
  }
}

const { spawn } = require('node:child_process');

function checkPortFree(port) {
  return new Promise((resolve) => {
    const net = require('node:net');
    const socket = new net.Socket();
    socket.setTimeout(800);
    socket.on('connect', () => {
      socket.destroy();
      resolve(false);
    })
    .on('error', () => {
      socket.destroy();
      resolve(true);
    })
    .on('timeout', () => {
      socket.destroy();
      resolve(true);
    })
    .connect(port, '127.0.0.1');
  });
}

async function spawnChrome(port) {
  const chromePath = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  const userDir = path.resolve(__dirname, '../chrome_data_mirror');

  const proc = spawn(chromePath, [
    `--remote-debugging-port=${port}`,
    '--headless=new',
    `--user-data-dir=${userDir}`,
    '--no-first-run',
    '--no-default-browser-check'
  ], {
    detached: true,
    stdio: 'ignore'
  });
  proc.unref();

  for (let attempt = 0; attempt < 20; attempt += 1) {
    const isFree = await checkPortFree(port);
    if (!isFree) return proc;
    await sleep(250);
  }
  return proc;
}

async function openBlankTarget(port, options = {}) {
  let spawnedProcess = null;
  const isFree = await checkPortFree(port);
  if (isFree) {
    spawnedProcess = await spawnChrome(port);
  }

  let target = null;
  if (options.backgroundTarget !== false) {
    target = await createBackgroundTarget(port);
  } else {
    target = await fetchJson(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' });
  }

  if (target) {
    target.spawnedProcess = spawnedProcess;
  }
  return target;
}

async function closeTarget(port, targetId) {
  if (!targetId) return;
  try {
    await fetch(`http://127.0.0.1:${port}/json/close/${targetId}`);
  } catch {
    // Closing the target is non-critical.
  }
}

function buildExtractionExpression() {
  return `(() => {
    const article = document.querySelector('article[data-testid="tweet"]') || document.querySelector('article');
    const root = article || document.body;
    const ariaLabels = Array.from(root.querySelectorAll('[aria-label]'))
      .map((element) => element.getAttribute('aria-label'))
      .filter(Boolean);

    return {
      title: document.title,
      tweetText: (root.querySelector('[data-testid="tweetText"]')?.innerText || '').trim(),
      labels: ariaLabels.slice(0, 120),
      text: (root.innerText || '').slice(0, 8000)
    };
  })()`;
}

async function getTweetMetrics(url, options = {}) {
  const port = options.port || DEFAULT_PORT;
  const navigateWaitMs = options.navigateWaitMs || DEFAULT_NAVIGATE_WAIT_MS;
  let target = null;
  let client = null;

  try {
    target = await openBlankTarget(port, { backgroundTarget: options.backgroundTarget });
    client = new CDPClient(target.webSocketDebuggerUrl);
    await client.connect();
    await client.send('Page.enable');
    await client.send('Runtime.enable');
    await client.send('Page.navigate', { url });
    const deadline = Date.now() + navigateWaitMs;
    let value = {};
    let metrics = {};

    while (Date.now() <= deadline) {
      const evaluated = await client.send('Runtime.evaluate', {
        expression: buildExtractionExpression(),
        returnByValue: true,
        awaitPromise: true,
      });
      value = evaluated.result && evaluated.result.value ? evaluated.result.value : {};
      const metricText = [...(value.labels || []), value.text || ''].join('\n');
      metrics = extractMetricsFromText(metricText);
      const guard = detectPageGuard(value);
      if (guard.blocked) {
        return {
          ok: false,
          url,
          error: `Page guard detected: ${guard.reason}`,
          guard,
          metrics,
          tweetText: value.tweetText || '',
          title: value.title || '',
        };
      }
      if ((value.tweetText && value.tweetText.trim()) || hasAnyMetric(metrics)) break;
      await sleep(750);
    }

    if (!value.tweetText && !hasAnyMetric(metrics)) {
      return {
        ok: false,
        url,
        error: 'Tweet content or metrics not found before timeout',
        guard: detectPageGuard(value),
        metrics,
        tweetText: '',
        title: value.title || '',
      };
    }

    return {
      ok: true,
      url,
      metrics,
      guard: { blocked: false, reason: null },
      tweetText: value.tweetText || '',
      title: value.title || '',
    };
  } catch (error) {
    return {
      ok: false,
      url,
      error: error.message,
      guard: { blocked: false, reason: null },
      metrics: {
        replies: null,
        reposts: null,
        likes: null,
        views: null,
        bookmarks: null,
      },
    };
  } finally {
    if (client) {
      client.close();
    }
    if (target) {
      if (target.id) {
        await closeTarget(port, target.id);
      }
      if (target.spawnedProcess) {
        target.spawnedProcess.kill('SIGTERM');
      }
    }
  }
}

function parseArgs(argv) {
  const urls = [];
  const options = {
    port: DEFAULT_PORT,
    navigateWaitMs: DEFAULT_NAVIGATE_WAIT_MS,
    delayMs: DEFAULT_DELAY_MS,
    jitterMs: DEFAULT_JITTER_MS,
    retries: DEFAULT_RETRIES,
    stopOnGuard: true,
    backgroundTarget: true,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--port') {
      options.port = Number.parseInt(argv[++index], 10);
    } else if (arg === '--wait-ms') {
      options.navigateWaitMs = Number.parseInt(argv[++index], 10);
    } else if (arg === '--delay-ms') {
      options.delayMs = Number.parseInt(argv[++index], 10);
    } else if (arg === '--jitter-ms') {
      options.jitterMs = Number.parseInt(argv[++index], 10);
    } else if (arg === '--retries') {
      options.retries = Number.parseInt(argv[++index], 10);
    } else if (arg === '--continue-on-guard') {
      options.stopOnGuard = false;
    } else if (arg === '--foreground') {
      options.backgroundTarget = false;
    } else if (arg === '--help' || arg === '-h') {
      options.help = true;
    } else {
      urls.push(arg);
    }
  }

  return { urls, options };
}

function printHelp() {
  console.log(`Usage:
  node scripts/x_metrics_cdp.js [--port 19222] [--wait-ms 7500] <x_url> [x_url...]

Output:
  JSON with per-URL replies/reposts/likes/views/bookmarks.

Safety:
  Reads visible X pages through your own Chrome/CDP session. It does not click,
  like, repost, reply, solve CAPTCHA, or bypass access controls. It slows down
  between URLs and stops on login/challenge/rate-limit pages by default.

Options:
  --foreground          Debug mode: open a visible/foreground tab
  --delay-ms 1500       Base delay between URLs
  --jitter-ms 1500      Random extra delay between URLs
  --retries 1           Retry count for empty/non-guard failures
  --continue-on-guard   Continue batch even after login/challenge/rate-limit

Prerequisite:
  A Chrome instance exposing CDP on the selected port, already logged into X if needed.`);
}

async function getTweetMetricsWithRetry(url, options = {}) {
  const attempts = Math.max(0, options.retries || 0) + 1;
  let lastResult = null;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    const result = await getTweetMetrics(url, options);
    result.attempt = attempt;
    lastResult = result;
    if (result.ok) return result;
    if (result.guard && result.guard.blocked) return result;
    if (attempt < attempts) {
      await sleep(jitterDelay(options.delayMs || DEFAULT_DELAY_MS, options.jitterMs || DEFAULT_JITTER_MS));
    }
  }
  return lastResult;
}

async function main() {
  const { urls, options } = parseArgs(process.argv.slice(2));
  if (options.help || urls.length === 0) {
    printHelp();
    process.exit(options.help ? 0 : 2);
  }

  const version = await fetchJson(`http://127.0.0.1:${options.port}/json/version`);
  const results = [];
  let stoppedByGuard = null;
  for (let index = 0; index < urls.length; index += 1) {
    if (index > 0) {
      await sleep(jitterDelay(options.delayMs, options.jitterMs));
    }
    const result = await getTweetMetricsWithRetry(urls[index], options);
    results.push(result);
    if (options.stopOnGuard && result.guard && result.guard.blocked) {
      stoppedByGuard = result.guard.reason;
      break;
    }
  }

  console.log(JSON.stringify({
    ok: results.every((item) => item.ok),
    browser: version.Browser || null,
    total: urls.length,
    processed: results.length,
    success: results.filter((item) => item.ok).length,
    failed: results.filter((item) => !item.ok).length,
    stoppedByGuard,
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
  parseCompactNumber,
  extractMetricsFromText,
  hasAnyMetric,
  detectPageGuard,
  parseArgs,
  jitterDelay,
  sleep,
  CDPClient,
  openBlankTarget,
  closeTarget,
  getTweetMetrics,
  getTweetMetricsWithRetry,
};
