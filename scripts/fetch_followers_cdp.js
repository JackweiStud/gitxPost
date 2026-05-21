#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');
const {
  CDPClient,
  openBlankTarget,
  closeTarget,
  sleep,
  detectPageGuard,
} = require('./x_metrics_cdp.js');

const BASE_DIR = path.resolve(__dirname, '..');
const FOLLOWERS_JSON = path.join(BASE_DIR, 'xinfo', 'log', 'followers.json');
const DEFAULT_PORT = 19222;

function parseCountText(raw) {
  if (!raw) return -1;
  const normalized = String(raw).replace(/,/g, '').trim();
  const match = normalized.match(/([0-9]+(?:\.[0-9]+)?)(?:\s*([KMB万千])\b)?/i);
  if (!match) return -1;
  const value = Number.parseFloat(match[1]);
  const unit = (match[2] || '').toLowerCase();
  const multiplier =
    unit === 'k' || unit === '千' ? 1000 :
    unit === 'm' ? 1000000 :
    unit === 'b' ? 1000000000 :
    unit === '万' ? 10000 :
    1;
  return Math.round(value * multiplier);
}

function parseTweetDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

async function evaluate(client, expression, ...args) {
  const argList = args.map((value) => ({ value }));
  const result = await client.send('Runtime.callFunctionOn', {
    functionDeclaration: expression,
    arguments: argList,
    returnByValue: true,
    awaitPromise: true,
    executionContextId: 1,
  }).catch(async () => {
    const fallback = await client.send('Runtime.evaluate', {
      expression: `(${expression})(...${JSON.stringify(args)})`,
      returnByValue: true,
      awaitPromise: true,
    });
    return fallback;
  });
  return result.result && result.result.value;
}

async function withPage(port, callback) {
  const target = await openBlankTarget(port, { backgroundTarget: true });
  const client = new CDPClient(target.webSocketDebuggerUrl);
  await client.connect();
  try {
    await client.send('Page.enable');
    await client.send('Runtime.enable');
    return await callback(client);
  } finally {
    client.close();
    await closeTarget(port, target.id);
  }
}

async function fetchProfileStats(username, options = {}) {
  const port = options.port || DEFAULT_PORT;
  const timeoutMs = (options.timeout || 30) * 1000;
  const url = `https://x.com/${username}`;

  return withPage(port, async (client) => {
    await client.send('Page.navigate', { url });
    await sleep(Math.min(6000, timeoutMs));
    const deadline = Date.now() + timeoutMs;
    let snapshot = {};
    while (Date.now() < deadline) {
      snapshot = await evaluate(client, `(username) => {
        const links = Array.from(document.querySelectorAll('a[href]')).map((a) => ({
          href: a.getAttribute('href') || '',
          text: a.innerText || ''
        }));
        return {
          title: document.title,
          text: document.body ? document.body.innerText : '',
          links: links.filter((item) =>
            item.href === '/' + username + '/following' ||
            item.href === '/' + username + '/followers' ||
            item.href === '/' + username + '/verified_followers'
          )
        };
      }`, username);
      const guard = detectPageGuard(snapshot);
      if (guard.blocked) {
        return { followers: -1, following: -1, guard, title: snapshot.title || '' };
      }
      if ((snapshot.links || []).length >= 2 || /Followers/i.test(snapshot.text || '')) break;
      await sleep(750);
    }

    let followers = -1;
    let following = -1;
    for (const link of snapshot.links || []) {
      if (/\/(verified_)?followers$/.test(link.href)) followers = parseCountText(link.text);
      if (/\/following$/.test(link.href)) following = parseCountText(link.text);
    }
    if (followers < 0) {
      const match = String(snapshot.text || '').match(/([0-9,.]+[KMB万千]?)\s*Followers/i);
      if (match) followers = parseCountText(match[1]);
    }
    if (following < 0) {
      const match = String(snapshot.text || '').match(/([0-9,.]+[KMB万千]?)\s*Following/i);
      if (match) following = parseCountText(match[1]);
    }

    return {
      followers,
      following,
      guard: { blocked: false, reason: null },
      title: snapshot.title || '',
    };
  });
}

async function fetchActivityStats(username, options = {}) {
  const port = options.port || DEFAULT_PORT;
  const timeoutMs = (options.timeout || 30) * 1000;
  const url = `https://x.com/${username}/with_replies`;
  const now = Date.now();
  const start = now - 24 * 60 * 60 * 1000;
  const seen = new Set();
  const all = new Set();

  try {
    await withPage(port, async (client) => {
      await client.send('Page.navigate', { url });
      await sleep(Math.min(5000, timeoutMs));
      const rounds = 18;
      for (let round = 0; round < rounds; round += 1) {
        const metas = await evaluate(client, `(username) => {
          function pathOf(href) {
            try { return new URL(href, location.origin).pathname || ''; } catch { return href || ''; }
          }
          function statusId(pathname) {
            const match = pathname.match(/\\/status\\/(\\d+)/);
            return match ? match[1] : null;
          }
          const rows = [];
          for (const article of document.querySelectorAll('article[data-testid="tweet"]')) {
            const userNameNode = article.querySelector('[data-testid="User-Name"]');
            if (!userNameNode) continue;
            const ownAuthor = Array.from(userNameNode.querySelectorAll('a[href]'))
              .some((a) => pathOf(a.getAttribute('href') || '') === '/' + username);
            if (!ownAuthor) continue;
            for (const time of article.querySelectorAll('time[datetime]')) {
              const anchor = time.closest('a[href]');
              if (!anchor) continue;
              const pathname = pathOf(anchor.getAttribute('href') || '');
              const id = statusId(pathname);
              const dt = time.getAttribute('datetime');
              if (id && dt) {
                rows.push({ id, dt });
                break;
              }
            }
          }
          return rows;
        }`, username);

        for (const item of metas || []) {
          all.add(item.id);
          const date = parseTweetDate(item.dt);
          if (!date) continue;
          const ts = date.getTime();
          if (ts >= start && ts <= now) seen.add(item.id);
        }
        await evaluate(client, `() => { window.scrollBy(0, 900); return true; }`);
        await sleep(1000);
        if (round > 6 && (metas || []).length === 0) break;
      }
    });
    return { activity_24h: seen.size, activity_ok: true, discovered_count: all.size };
  } catch (error) {
    return { activity_24h: 0, activity_ok: false, activity_error: error.message };
  }
}

function todayParts() {
  const now = new Date();
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
  const parts = Object.fromEntries(formatter.formatToParts(now).map((part) => [part.type, part.value]));
  return {
    date: `${parts.year}-${parts.month}-${parts.day}`,
    time: `${parts.hour}:${parts.minute}:${parts.second}`,
  };
}

function saveStats(username, stats) {
  fs.mkdirSync(path.dirname(FOLLOWERS_JSON), { recursive: true });
  let data = { username, records: [] };
  if (fs.existsSync(FOLLOWERS_JSON)) {
    try {
      data = JSON.parse(fs.readFileSync(FOLLOWERS_JSON, 'utf8'));
    } catch {
      data = { username, records: [] };
    }
  }
  data.username = username;
  if (!Array.isArray(data.records)) data.records = [];

  const { date, time } = todayParts();
  const record = {
    date,
    time,
    followers: stats.followers,
    following: stats.following,
    activity_24h: stats.activity_24h || 0,
  };
  const existingIndex = data.records.findIndex((item) => item.date === date);
  let previous = data.records.at(-1);
  if (existingIndex >= 0) {
    previous = existingIndex > 0 ? data.records[existingIndex - 1] : null;
    data.records[existingIndex] = record;
  } else {
    data.records.push(record);
  }
  data.records.sort((a, b) => `${a.date} ${a.time}`.localeCompare(`${b.date} ${b.time}`));

  fs.writeFileSync(FOLLOWERS_JSON, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
  let change = null;
  if (previous && previous.followers >= 0 && record.followers >= 0) {
    const diff = record.followers - previous.followers;
    change = {
      previous_date: previous.date,
      previous_followers: previous.followers,
      diff,
      direction: diff > 0 ? 'up' : diff < 0 ? 'down' : 'same',
    };
  }
  return { ...record, change, total_records: data.records.length };
}

function parseArgs(argv) {
  const options = { username: null, timeout: 30, jsonOnly: false, port: DEFAULT_PORT };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--timeout') options.timeout = Number.parseInt(argv[++i], 10);
    else if (arg === '--port') options.port = Number.parseInt(argv[++i], 10);
    else if (arg === '--json-only') options.jsonOnly = true;
    else if (!arg.startsWith('--')) options.username = arg;
  }
  options.username = options.username || process.env.XPOST_USERNAME || 'jackaiwison';
  return options;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const profile = await fetchProfileStats(options.username, options);
  if (profile.followers < 0) {
    console.log(JSON.stringify({
      ok: false,
      error: `无法获取 @${options.username} 的粉丝数据`,
      username: options.username,
      guard: profile.guard,
      title: profile.title,
    }, null, 2));
    process.exit(1);
  }

  const activity = await fetchActivityStats(options.username, options);
  const saved = saveStats(options.username, { ...profile, ...activity });
  console.log(JSON.stringify({
    ok: true,
    username: options.username,
    followers: profile.followers,
    following: profile.following,
    activity_24h: activity.activity_24h,
    activity_ok: activity.activity_ok,
    data_file: FOLLOWERS_JSON,
    ...saved,
    source: 'cdp',
  }, null, 2));
}

if (require.main === module) {
  main().catch((error) => {
    console.log(JSON.stringify({ ok: false, error: error.message }, null, 2));
    process.exit(1);
  });
}

module.exports = {
  parseCountText,
  fetchProfileStats,
  fetchActivityStats,
  saveStats,
};
