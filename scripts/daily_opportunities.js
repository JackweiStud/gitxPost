#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { getTweetMetricsWithRetry } = require('./x_metrics_cdp.js');

const DEFAULT_TOP_N = 5;
const DEFAULT_CDP_LIMIT = 10;
const DEFAULT_METRICS_DELAY_MS = 1800;
const DEFAULT_METRICS_JITTER_MS = 1800;
const DEFAULT_METRICS_RETRIES = 1;
const DEFAULT_RESULT_DIR = path.resolve('xinfo/log/day');
const ENRICH_LLM_PY = path.resolve(__dirname, 'enrich_opportunity_llm.py');
const REPO_ROOT = path.resolve(__dirname, '..');
const VENV_PYTHON = path.join(REPO_ROOT, '.venv', 'bin', 'python');

const TOPIC_RULES = [
  ['agent', ['agent', 'agents', 'workflow', 'openclaw', 'claude code', 'computer use', 'browser use', 'automation']],
  ['coding', ['cursor', 'composer', 'coding', 'code', 'github', 'repo', 'developer', 'build', 'ship', 'lines of code']],
  ['design-ai', ['design', 'figma', 'ux', 'ui', 'prototype', 'new tab', 'canvas']],
  ['monetization', ['startup', 'revenue', 'growth', 'creator', 'followers', 'business', 'pricing', 'gtm']],
  ['model', ['gpt', 'claude', 'gemini', 'grok', 'model', 'llm', 'benchmark', 'karpathy', 'anthropic', 'openai']],
  ['security', ['security', 'privacy', 'scam', 'risk', 'attack', 'jailbreak']],
];

const FOCUS_WORDS = [
  'ai', 'agent', 'workflow', 'coding', 'code', 'cursor', 'claude', 'grok', 'gemini',
  'openclaw', 'startup', 'creator', 'growth', 'x', 'twitter', 'automation', 'build',
  'ship', 'llm', 'model', 'tool', 'developer', 'product', 'karpathy', 'anthropic', 'openai',
];

const IGNORE_WORDS = [
  'meme', 'nft', 'web3', 'crypto', 'giveaway', 'airdrop', 'politics', 'war', 'celebrity', 'sports',
];

function parseTime(value) {
  const date = new Date(String(value || '').trim().replace(' ', 'T'));
  if (!Number.isNaN(date.getTime())) return date;

  const fallback = new Date(String(value || '').trim());
  return Number.isNaN(fallback.getTime()) ? null : fallback;
}

function hoursAgo(scanTime, itemTime) {
  const scan = parseTime(scanTime);
  const item = parseTime(itemTime);
  if (!scan || !item) return 9999;
  return Math.max(0, (scan - item) / 36e5);
}

function itemText(item) {
  return `${item.title || ''}\n${item.summary || ''}`.toLowerCase();
}

function countHits(text, words) {
  return words.reduce((count, word) => count + (text.includes(word) ? 1 : 0), 0);
}

function detectTopic(text) {
  for (const [topic, words] of TOPIC_RULES) {
    if (words.some((word) => text.includes(word))) return topic;
  }
  return 'other';
}

function scoreCandidate(item, scanTime) {
  const text = itemText(item);
  const ageHours = hoursAgo(scanTime, item.time);
  const topic = detectTopic(text);
  const creatorFit = Math.min(
    25,
    countHits(text, FOCUS_WORDS) * 4 + (['agent', 'coding', 'design-ai', 'monetization', 'model'].includes(topic) ? 5 : 0),
  );
  const remixPotential = Math.min(
    20,
    (/(how|why|what|build|built|launch|launched|ship|shipped|from|to|case|framework|playbook|mistake|lesson|learned|trend|landscape|ceiling|works|altered)/i.test(item.title || '') ? 8 : 0) +
      (/[0-9]/.test(item.title || '') ? 4 : 0) +
      ((item.summary || '').length > 80 ? 4 : 0) +
      (['agent', 'coding', 'monetization', 'model'].includes(topic) ? 4 : 0),
  );
  const replyPotential = Math.min(
    20,
    (/(i |we |my |our |我|我们|我最|我做|我用)/i.test(`${item.title || ''} ${item.summary || ''}`) ? 5 : 0) +
      (/(think|believe|love|hate|surprised|learned|found|noticed|tested|built|released|launched|宣布|加入|取代|改变)/i.test(text) ? 5 : 0) +
      (/(question|debate|hot take|takeaway|agree|disagree|vs|ceiling|problem|wrong|right|天塌|狂魔)/i.test(text) ? 5 : 0) +
      (['agent', 'coding', 'model'].includes(topic) ? 3 : 0) +
      ((item.summary || '').length > 120 ? 2 : 0),
  );
  const freshness = ageHours <= 6 ? 15 : ageHours <= 12 ? 12 : ageHours <= 24 ? 8 : ageHours <= 48 ? 4 : 0;
  const topicCluster = ['agent', 'coding', 'model', 'monetization', 'design-ai'].includes(topic) ? 5 : 1;
  const contentQuality = Math.min(5, Math.floor(((item.title || '').length + (item.summary || '').length) / 80));
  let penalty = 0;
  if (countHits(text, IGNORE_WORDS)) penalty += 12;
  if ((item.title || '').length < 25) penalty += 4;
  if (/^(rt|re:|\s*quote)/i.test(item.title || '')) penalty += 8;
  if (topic === 'other') penalty += 4;

  return {
    creatorFit,
    remixPotential,
    replyPotential,
    freshness,
    topicCluster,
    contentQuality,
    penalty,
    preScore: Math.max(0, creatorFit + remixPotential + replyPotential + freshness + topicCluster + contentQuality - penalty),
    topic,
    ageHours: Number(ageHours.toFixed(1)),
  };
}

function pickTopCandidates(items, scanTime, options = {}) {
  const limit = options.limit || DEFAULT_CDP_LIMIT;
  const maxPerAuthor = options.maxPerAuthor || 2;
  const maxPerTopic = options.maxPerTopic || 3;
  const authorCount = new Map();
  const topicCount = new Map();
  const scored = items
    .map((item, index) => ({ index, item, score: scoreCandidate(item, scanTime) }))
    .sort((a, b) => b.score.preScore - a.score.preScore);
  const picked = [];

  for (const row of scored) {
    const author = row.item.account || row.item.author || 'unknown';
    const topic = row.score.topic;
    if ((authorCount.get(author) || 0) >= maxPerAuthor) continue;
    if ((topicCount.get(topic) || 0) >= maxPerTopic) continue;

    picked.push(row);
    authorCount.set(author, (authorCount.get(author) || 0) + 1);
    topicCount.set(topic, (topicCount.get(topic) || 0) + 1);
    if (picked.length >= limit) break;
  }

  return picked;
}

function engagementScore(metrics) {
  const values = metrics || {};
  return (
    Math.log((values.views || 0) + 1) * 0.35 +
    Math.log((values.replies || 0) + 1) * 0.30 +
    Math.log((values.reposts || 0) + 1) * 0.20 +
    Math.log((values.likes || 0) + 1) * 0.10 +
    Math.log((values.bookmarks || 0) + 1) * 0.05
  ) * 10;
}

function computeFinalScore(row) {
  const engagement = engagementScore(row.metrics);
  const finalScore = row.preScore * 0.55 + engagement * 0.35 + row.freshness * 0.10;
  return {
    engagementScore: Number(engagement.toFixed(2)),
    finalScore: Number(finalScore.toFixed(2)),
  };
}

function classifyAction(row) {
  const metrics = row.metrics || {};
  if ((metrics.views || 0) > 100000 || (metrics.reposts || 0) > 50 || (metrics.bookmarks || 0) > 100) {
    return 'remix_post';
  }
  if ((metrics.replies || 0) >= 5 && (metrics.views || 0) >= 3000 && row.replyPotential >= 10) {
    return 'reply';
  }
  if ((metrics.likes || 0) >= 30 && row.replyPotential >= 10) {
    return 'quote_or_reply';
  }
  return 'skip_or_watch';
}

function parseLastJsonObject(text) {
  const source = String(text || '').trim();
  const end = source.lastIndexOf('}');
  if (end < 0) return null;
  let depth = 0;
  for (let index = end; index >= 0; index -= 1) {
    if (source[index] === '}') depth += 1;
    if (source[index] === '{') {
      depth -= 1;
      if (depth === 0) {
        try {
          return JSON.parse(source.slice(index, end + 1));
        } catch {
          return null;
        }
      }
    }
  }
  return null;
}

function enrichOpportunityWithLLM(opportunity, options = {}) {
  const python = options.python || process.env.PYTHON || (fs.existsSync(VENV_PYTHON) ? VENV_PYTHON : 'python3');
  const script = options.script || ENRICH_LLM_PY;
  const runner = options.runner || spawnSync;
  const result = runner(python, [script], {
    input: JSON.stringify(opportunity),
    encoding: 'utf8',
    cwd: options.cwd || REPO_ROOT,
    timeout: options.timeoutMs || 180000,
  });
  const parsed = parseLastJsonObject(result.stdout);

  if (result.error || !parsed || !parsed.ok) {
    return {
      ...opportunity,
      llmExplanationOk: false,
      llmExplanationError: result.error
        ? result.error.message
        : (parsed && parsed.error) || result.stderr || result.stdout || `LLM explanation exited ${result.status}`,
    };
  }

  return {
    ...opportunity,
    llmExplanationOk: true,
    llmExplanationError: null,
    trafficMotif: parsed.trafficMotif,
    myAngle: parsed.myAngle,
    recommendedAction: parsed.recommendedAction,
    draftPrompts: parsed.draftPrompts,
  };
}

function findLatestResultFile(resultDir = DEFAULT_RESULT_DIR) {
  if (!fs.existsSync(resultDir)) {
    throw new Error(`Result directory not found: ${resultDir}`);
  }

  const candidates = fs.readdirSync(resultDir)
    .filter((name) => /^\d{4}-\d{2}-\d{2}_result\.json$/.test(name))
    .sort();

  if (candidates.length === 0) {
    throw new Error(`No *_result.json files found in ${resultDir}`);
  }

  return path.join(resultDir, candidates[candidates.length - 1]);
}

function defaultOutputFileForResult(resultFile) {
  const resolved = path.resolve(resultFile);
  const dayDir = path.dirname(resolved);
  const logDir = path.dirname(dayDir);
  const baseName = path.basename(resolved).replace(/_result\.json$/, '_opportunities.json');
  return path.join(logDir, 'opportunities', baseName);
}

function writeOutputFile(outputFile, payload) {
  fs.mkdirSync(path.dirname(outputFile), { recursive: true });
  fs.writeFileSync(outputFile, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

function formatMetric(value) {
  if (!Number.isFinite(value)) return '-';
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(value >= 10_000_000 ? 1 : 2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(value >= 10_000 ? 1 : 2)}K`;
  return String(value);
}

function truncateText(text, maxLength = 72) {
  const value = String(text || '').replace(/\s+/g, ' ').trim();
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value;
}

function formatSummary(output) {
  const lines = [
    `ok: ${output.ok}`,
    `input: ${output.resultFile}`,
    `output: ${output.outputFile}`,
    `candidates: ${output.totalCandidates}, cdp: ${output.cdpCandidates}, top: ${(output.opportunities || []).length}`,
    '',
    'Top opportunities:',
  ];

  for (const [index, item] of (output.opportunities || []).entries()) {
    const metrics = item.metrics || {};
    lines.push(
      `${index + 1}. @${item.account} ${item.finalScore} ${item.actionType} ` +
      `views=${formatMetric(metrics.views)} replies=${formatMetric(metrics.replies)} ` +
      `reposts=${formatMetric(metrics.reposts)} likes=${formatMetric(metrics.likes)} ` +
      `bookmarks=${formatMetric(metrics.bookmarks)} | ${truncateText(item.title)}`,
    );
  }

  return lines.join('\n');
}

async function buildOpportunities(resultFile, options = {}) {
  const payload = JSON.parse(fs.readFileSync(resultFile, 'utf8'));
  const scanTime = payload.summary && payload.summary.scan_time;
  if (!scanTime) throw new Error('Missing summary.scan_time in result file');

  const items = (payload.summary && payload.summary.new_ideas_preview) || [];
  const preselected = pickTopCandidates(items, scanTime, { limit: options.cdpLimit || DEFAULT_CDP_LIMIT });
  const enriched = [];

  for (const row of preselected) {
    const metricsResult = await getTweetMetricsWithRetry(row.item.link, {
      port: options.port,
      navigateWaitMs: options.waitMs,
      delayMs: options.metricsDelayMs || DEFAULT_METRICS_DELAY_MS,
      jitterMs: options.metricsJitterMs || DEFAULT_METRICS_JITTER_MS,
      retries: options.metricsRetries ?? DEFAULT_METRICS_RETRIES,
    });
    const metrics = metricsResult.metrics || {};
    const score = computeFinalScore({
      preScore: row.score.preScore,
      freshness: row.score.freshness,
      metrics,
    });
    const actionInput = { ...row.score, metrics };
    const opportunity = {
      account: row.item.account || row.item.author || 'unknown',
      title: row.item.title || '',
      url: row.item.link || '',
      time: row.item.time || '',
      preScore: row.score.preScore,
      scoreBreakdown: row.score,
      metricsOk: metricsResult.ok,
      metricsError: metricsResult.error || null,
      metrics,
      engagementScore: score.engagementScore,
      finalScore: score.finalScore,
      actionType: classifyAction(actionInput),
      tweetText: metricsResult.tweetText || '',
    };
    enriched.push(enrichOpportunityWithLLM(opportunity, options));
  }

  enriched.sort((a, b) => b.finalScore - a.finalScore);
  return {
    ok: true,
    resultFile: path.resolve(resultFile),
    scanTime,
    totalCandidates: items.length,
    cdpCandidates: preselected.length,
    opportunities: enriched.slice(0, options.topN || DEFAULT_TOP_N),
  };
}

function parseArgs(argv) {
  const options = {
    topN: DEFAULT_TOP_N,
    cdpLimit: DEFAULT_CDP_LIMIT,
    port: 19222,
    waitMs: 12000,
    metricsDelayMs: DEFAULT_METRICS_DELAY_MS,
    metricsJitterMs: DEFAULT_METRICS_JITTER_MS,
    metricsRetries: DEFAULT_METRICS_RETRIES,
    json: false,
    outputFile: null,
  };
  let resultFile = null;

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--result-file') resultFile = argv[++index];
    else if (arg === '--output') options.outputFile = argv[++index];
    else if (arg === '--json') options.json = true;
    else if (arg === '--top-n') options.topN = Number.parseInt(argv[++index], 10);
    else if (arg === '--cdp-limit') options.cdpLimit = Number.parseInt(argv[++index], 10);
    else if (arg === '--port') options.port = Number.parseInt(argv[++index], 10);
    else if (arg === '--wait-ms') options.waitMs = Number.parseInt(argv[++index], 10);
    else if (arg === '--metrics-delay-ms') options.metricsDelayMs = Number.parseInt(argv[++index], 10);
    else if (arg === '--metrics-jitter-ms') options.metricsJitterMs = Number.parseInt(argv[++index], 10);
    else if (arg === '--metrics-retries') options.metricsRetries = Number.parseInt(argv[++index], 10);
    else if (arg === '--help' || arg === '-h') options.help = true;
  }

  return { resultFile, options };
}

function printHelp() {
  console.log(`Usage:
  node scripts/daily_opportunities.js
  node scripts/daily_opportunities.js --result-file xinfo/log/day/YYYY-MM-DD_result.json

Options:
  --result-file PATH  Input scan result JSON. Default: latest xinfo/log/day/*_result.json
  --output PATH       Output JSON path. Default: xinfo/log/opportunities/YYYY-MM-DD_opportunities.json
  --json              Print full JSON to stdout instead of compact summary
  --top-n 5        Final opportunity count
  --cdp-limit 10   Number of preselected URLs to enrich with Chrome/CDP
  --port 19222     Chrome CDP port
  --wait-ms 12000  Per URL max wait time
  --metrics-delay-ms 1800    Base delay before metric retry
  --metrics-jitter-ms 1800   Random extra delay before metric retry
  --metrics-retries 1        Retry count for non-guard metric failures`);
}

async function main() {
  const { resultFile, options } = parseArgs(process.argv.slice(2));
  if (options.help) {
    printHelp();
    return;
  }

  const inputFile = resultFile || findLatestResultFile();
  const outputFile = path.resolve(options.outputFile || defaultOutputFileForResult(inputFile));
  const output = await buildOpportunities(inputFile, options);
  output.outputFile = outputFile;
  writeOutputFile(outputFile, output);

  if (options.json) {
    console.log(JSON.stringify(output, null, 2));
  } else {
    console.log(formatSummary(output));
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error(JSON.stringify({ ok: false, error: error.message }, null, 2));
    process.exit(1);
  });
}

module.exports = {
  scoreCandidate,
  pickTopCandidates,
  computeFinalScore,
  findLatestResultFile,
  defaultOutputFileForResult,
  formatSummary,
  parseLastJsonObject,
  enrichOpportunityWithLLM,
  buildOpportunities,
};
