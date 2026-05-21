const test = require('node:test');
const assert = require('node:assert/strict');

const {
  scoreCandidate,
  pickTopCandidates,
  computeFinalScore,
  findLatestResultFile,
  defaultOutputFileForResult,
  formatSummary,
  parseLastJsonObject,
  enrichOpportunityWithLLM,
} = require('./scripts/daily_opportunities.js');

test('scoreCandidate uses summary scan time freshness without author priority', () => {
  const scanTime = '2026-05-20 03:12:32';
  const recent = scoreCandidate({
    account: 'unknown_small_builder',
    title: 'I built a Claude Code workflow that ships agent tasks faster',
    summary: 'A concrete build log with workflow, code, and agent lessons.',
    time: 'Tue, 19 May 2026 17:30:40 GMT',
  }, scanTime);
  const old = scoreCandidate({
    account: 'famous_author',
    title: 'I built a Claude Code workflow that ships agent tasks faster',
    summary: 'A concrete build log with workflow, code, and agent lessons.',
    time: 'Wed, 29 Apr 2026 17:30:40 GMT',
  }, scanTime);

  assert.equal(recent.authorPriority, undefined);
  assert.ok(recent.preScore > old.preScore);
  assert.equal(recent.freshness, 15);
  assert.equal(old.freshness, 0);
});

test('pickTopCandidates enforces author and topic diversity', () => {
  const scanTime = '2026-05-20 03:12:32';
  const items = Array.from({ length: 5 }, (_, index) => ({
    account: 'same_author',
    title: `I built agent workflow ${index} with Claude Code`,
    summary: 'agent workflow code build',
    time: 'Tue, 19 May 2026 17:30:40 GMT',
    link: `https://x.com/a/status/${index}`,
  }));

  const picked = pickTopCandidates(items, scanTime, { limit: 10, maxPerAuthor: 2 });
  assert.equal(picked.length, 2);
});

test('computeFinalScore lets strong real metrics lift a lower pre-score candidate', () => {
  const lowPreHighMetrics = computeFinalScore({
    preScore: 61,
    freshness: 15,
    metrics: { replies: 273, reposts: 275, likes: 2895, views: 26413728, bookmarks: 412 },
  });
  const highPreWeakMetrics = computeFinalScore({
    preScore: 77,
    freshness: 15,
    metrics: { replies: 1, reposts: 0, likes: 9, views: 2854, bookmarks: 11 },
  });

  assert.ok(lowPreHighMetrics.finalScore > highPreWeakMetrics.finalScore);
});

test('findLatestResultFile picks newest day result json', (t) => {
  const fs = require('node:fs');
  const os = require('node:os');
  const path = require('node:path');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gitxpost-day-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));

  fs.writeFileSync(path.join(dir, '2026-05-18_result.json'), '{}');
  fs.writeFileSync(path.join(dir, '2026-05-20.md'), '# report');
  fs.writeFileSync(path.join(dir, '2026-05-19_result.json'), '{}');

  assert.equal(findLatestResultFile(dir), path.join(dir, '2026-05-19_result.json'));
});

test('defaultOutputFileForResult writes opportunity json under xinfo/log/opportunities', () => {
  assert.equal(
    defaultOutputFileForResult('/repo/xinfo/log/day/2026-05-20_result.json'),
    '/repo/xinfo/log/opportunities/2026-05-20_opportunities.json',
  );
});

test('formatSummary prints compact opportunity list', () => {
  const summary = formatSummary({
    ok: true,
    resultFile: '/repo/xinfo/log/day/2026-05-20_result.json',
    outputFile: '/repo/xinfo/log/opportunities/2026-05-20_opportunities.json',
    totalCandidates: 349,
    cdpCandidates: 10,
    opportunities: [
      {
        account: 'mntruell',
        title: 'Composer 2.5 is now the most-chosen model in Cursor.',
        finalScore: 69.66,
        actionType: 'remix_post',
        metrics: { views: 26413728, replies: 273, reposts: 275, likes: 2896, bookmarks: 412 },
      },
    ],
  });

  assert.match(summary, /output: .*2026-05-20_opportunities\.json/);
  assert.match(summary, /1\. @mntruell .*remix_post/);
  assert.doesNotMatch(summary, /tweetText/);
});

test('parseLastJsonObject extracts final JSON from mixed output', () => {
  assert.deepEqual(parseLastJsonObject('log line\n{"ok":true,"value":1}'), {
    ok: true,
    value: 1,
  });
});

test('enrichOpportunityWithLLM adds LLM creation guidance fields', () => {
  const enriched = enrichOpportunityWithLLM({
    account: 'mntruell',
    title: 'Composer 2.5 is now the most-chosen model in Cursor.',
    url: 'https://x.com/mntruell/status/2056780569380626686#m',
    actionType: 'remix_post',
    scoreBreakdown: { topic: 'coding' },
    metrics: { views: 26413728, replies: 274, reposts: 275, likes: 2906, bookmarks: 412 },
    tweetText: 'Composer 2.5 is now the most-chosen model in Cursor.',
  }, {
    runner: () => ({
      status: 0,
      stdout: JSON.stringify({
        ok: true,
        trafficMotif: 'AI coding 工具真实使用迁移',
        myAngle: '开发者不是选择模型，而是在选择工作流默认入口。',
        recommendedAction: 'write_standalone_post',
        draftPrompts: {
          standalonePost: '写一条 Cursor Composer 2.5 独立观点帖',
          reply: '回复 @mntruell，补充 builder 视角',
          quotePost: '引用并说明工作流入口变化',
        },
      }),
      stderr: '',
    }),
  });

  assert.equal(enriched.llmExplanationOk, true);
  assert.equal(enriched.trafficMotif, 'AI coding 工具真实使用迁移');
  assert.match(enriched.myAngle, /工作流/);
  assert.equal(enriched.recommendedAction, 'write_standalone_post');
  assert.match(enriched.draftPrompts.standalonePost, /Cursor Composer 2.5/);
  assert.match(enriched.draftPrompts.reply, /@mntruell/);
});

test('enrichOpportunityWithLLM marks errors without hard-rule fallback', () => {
  const enriched = enrichOpportunityWithLLM({
    account: 'mntruell',
    title: 'Composer 2.5 is now the most-chosen model in Cursor.',
  }, {
    runner: () => ({
      status: 1,
      stdout: JSON.stringify({ ok: false, error: 'LLM failed' }),
      stderr: '',
    }),
  });

  assert.equal(enriched.llmExplanationOk, false);
  assert.equal(enriched.llmExplanationError, 'LLM failed');
  assert.equal(enriched.trafficMotif, undefined);
  assert.equal(enriched.myAngle, undefined);
  assert.equal(enriched.draftPrompts, undefined);
});
