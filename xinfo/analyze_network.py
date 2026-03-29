#!/usr/bin/env python3
"""
X 创意雷达 - 数据分析工具

用途：
  1. 二度人脉发现：找出 TARGET 账号正在推荐的外部账号
  2. 账号发帖规律：频率 / 原创率 / 类型分布
  3. 最近活跃趋势：每日新增条数对比
  4. 热点话题提取：从推文标题+摘要提取高频关键词

运行：
  python3 analyze_network.py              # 默认：人类可读输出
  python3 analyze_network.py 7            # 只看最近 7 天
  python3 analyze_network.py --json       # JSON 输出（供 OpenClaw 解析）
  python3 analyze_network.py 7 --json     # 最近 7 天 + JSON 输出
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
SEEN_FILE  = os.path.join(BASE_DIR, 'log', '.ideas_seen.json')
IDEAS_FILE = os.path.join(BASE_DIR, 'log', 'ideas.md')
SCAN_FILE  = os.path.join(BASE_DIR, 'x_ideas_scan.py')
ACCOUNTS_FILE = os.path.join(BASE_DIR, 'accounts.json')
DAY_LOG    = os.path.join(BASE_DIR, 'log', 'day')

# ── 工具 ──────────────────────────────────────────────────────────────────────

def load_target_accounts() -> set:
    """从 accounts.json 读取活跃账号列表"""
    targets = set()
    if not os.path.exists(ACCOUNTS_FILE):
        return targets

    try:
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        accounts = data.get("accounts", [])
        for acc in accounts:
            if acc.get("status") == "active":
                targets.add(acc.get("handle"))

        return targets
    except Exception as e:
        print(f"读取账号配置失败: {e}")
        return targets



def load_records(days=None) -> list:
    """加载 seen.json，可按天数过滤"""
    if not os.path.exists(SEEN_FILE) or os.stat(SEEN_FILE).st_size == 0: # Add this check
        return []
    with open(SEEN_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    records = data.get('seen_urls', [])
    if records and isinstance(records[0], str):
        return []   # 旧格式，无法分析
    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        records = [r for r in records if r.get('seen_at', '') >= cutoff]
    return records


# ── 分析函数（统一返回 dict，不直接 print）────────────────────────────────────

def calc_network(records: list, known_targets: set) -> list:
    """二度人脉：被 TARGET 用户 RT 的外部账号"""
    rt_pairs = [
        (r['author'], r['source'])
        for r in records
        if r.get('type') == 'rt'
        and r.get('author') and r.get('source')
        and r['author'] != r['source']
        and r['author'].lower() not in {t.lower() for t in known_targets}
    ]
    count = Counter(a for a, _ in rt_pairs)
    result = []
    for author, n in count.most_common(20):
        sources = sorted(set(s for a, s in rt_pairs if a == author))
        multi = len(sources) >= 2
        level = 'recommend' if (n >= 3 or multi) else ('evaluate' if n == 2 else 'candidate')
        result.append({
            'account': author,
            'recommended_by_count': n,
            'recommended_by': sources,
            'multi_source': multi,
            'level': level,
        })
    return result


def calc_account_stats(records: list, known_targets: set) -> list:
    """账号发帖规律"""
    stats = defaultdict(lambda: {'total': 0, 'original': 0, 'rt': 0, 'reply': 0, 'pinned': 0})
    for r in records:
        src = r.get('source', '')
        if not src:
            continue
        stats[src]['total'] += 1
        t = r.get('type', '')
        if t in stats[src]:
            stats[src][t] += 1

    result = []
    for acc, s in sorted(stats.items(), key=lambda x: -x[1]['total']):
        rate = round(s['original'] / s['total'] * 100) if s['total'] else 0
        if s['total'] < 5:
            advice = 'few_samples'
        elif rate < 30:
            advice = 'mostly_rt'
        elif rate >= 60 and s['total'] >= 15:
            advice = 'high_quality'
        else:
            advice = 'normal'
        result.append({
            'account': acc,
            'in_target': acc in known_targets,
            'total': s['total'],
            'original': s['original'],
            'original_rate': rate,
            'rt': s['rt'],
            'reply': s['reply'],
            'advice': advice,
        })
    return result


def calc_recent_trend(records: list, top_days: int = 7) -> dict:
    """最近 N 天每日新增条数"""
    daily: dict = defaultdict(lambda: defaultdict(int))
    for r in records:
        seen_at = r.get('seen_at', '')
        src = r.get('source', '')
        if seen_at and src:
            daily[seen_at[:10]][src] += 1

    sorted_days = sorted(daily.keys())[-top_days:]
    all_accounts = sorted(set(src for d in daily.values() for src in d))
    rows = []
    for acc in all_accounts:
        row = {'account': acc, 'days': {}}
        for d in sorted_days:
            row['days'][d] = daily[d].get(acc, 0)
        row['total'] = sum(row['days'].values())
        rows.append(row)
    return {'dates': sorted_days, 'accounts': rows}


_STOP_ZH = set('的了是在有我他她它们我们你你们这那个一不也都很就说到要和会呢啊哈呀已经了吧来去么没了我好就和所有就是可以自己使用现在真的感觉觉得因为所以然后如果还是但是只有虽然虽然而且因此通过方式方法对于关于其实其中包括')
_STOP_EN = {
    'the','a','an','is','are','was','were','be','been','being',
    'have','has','had','do','does','did','will','would','could',
    'should','may','might','shall','can','to','of','in','on','at',
    'for','with','by','from','as','it','its','this','that','i',
    'you','he','she','we','they','and','or','but','if','not','no',
    'up','out','so','now','just','my','your','our','their',
    'all','more','about','what','how','when','who','which','than',
    'x','com','https','http','t','co',
    # 领域背景噪音词（高频但无信息量）
    'open','claw','claude','new','like','good','code','today',
    'one','people','team','very','get','use','see','make','build',
    'way','work','time','day','great','first','last','week','also',
    'some','here','there','think','even','only','still','back',
    'want','need','well','going','thing','way','every','into',
}

def _keywords(text: str) -> list:
    words = []
    for w in re.findall(r'[A-Za-z][a-z]{2,}', text):
        if w.lower() not in _STOP_EN:
            words.append(w.lower())
    zh = [c for c in re.findall(r'[\u4e00-\u9fff]', text) if c not in _STOP_ZH]
    for i in range(len(zh) - 1):
        words.append(zh[i] + zh[i+1])
    return words


def calc_hot_topics(top_n: int = 25) -> dict:
    """从 ideas.md 提取高频话题"""
    if not os.path.exists(IDEAS_FILE):
        return {'titles_count': 0, 'summaries_count': 0, 'hot': []}

    titles, summaries = [], []
    with open(IDEAS_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('- **') and line.endswith('**'):
                titles.append(line[4:-2].strip())
            elif '摘要:' in line:
                summaries.append(line.split('摘要:', 1)[-1].strip())

    kws = []
    for t in titles:
        kws.extend(_keywords(t) * 3)
    for s in summaries:
        kws.extend(_keywords(s))

    hot = [
        {'keyword': kw, 'count': n,
         'tier': 'hot' if n >= 6 else ('warm' if n >= 3 else 'mention')}
        for kw, n in Counter(kws).most_common(top_n * 2)
        if n >= 2
    ][:top_n]

    return {'titles_count': len(titles), 'summaries_count': len(summaries), 'hot': hot}


def calc_top_posts(days: int = 7, top_n: int = 5) -> list:
    """从 ideas.md 提取信息量最高的推文（修复亮点推文空白问题）。

    评分逻辑：关键词命中数 × 3（标题）+ 摘要长度加成 + 有摘要加分。
    返回 list[dict]：[{account, title, link, summary, score}]
    """
    if not os.path.exists(IDEAS_FILE):
        return []

    hot_topics = calc_hot_topics(top_n=50)
    hot_kws = {item['keyword'] for item in hot_topics.get('hot', [])
               if item['tier'] in ('hot', 'warm')}

    posts = []
    current_account = None
    current_post = {}
    cutoff_date = None
    if days:
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)

    def flush_post():
        if not current_post.get('title') or not current_post.get('link'):
            return
        title = current_post.get('title', '')
        summary = current_post.get('summary', '')
        # 评分：标题关键词命中
        title_kws = set(_keywords(title))
        summary_kws = set(_keywords(summary))
        score = len(title_kws & hot_kws) * 3 + len(summary_kws & hot_kws)
        # 摘要长度加成（有实质摘要的推文更有价值）
        if summary and len(summary) > 20:
            score += 2
        if score > 0:
            posts.append({
                'account': current_account,
                'title': title,
                'link': current_post.get('link', ''),
                'summary': summary[:150] + '...' if len(summary) > 150 else summary,
                'score': score,
            })

    with open(IDEAS_FILE, encoding='utf-8') as f:
        for line in f:
            line_s = line.strip()
            # 账号头
            m = re.match(r'^## @(\w+) -', line_s)
            if m:
                if current_post:
                    flush_post()
                current_account = m.group(1)
                current_post = {}
                continue
            # 推文标题
            if line_s.startswith('- **') and '**' in line_s[4:]:
                if current_post:
                    flush_post()
                current_post = {'title': line_s[4:].rstrip('*').strip(), 'link': '', 'summary': ''}
                continue
            # 链接
            if '链接:' in line_s and current_post is not None:
                current_post['link'] = line_s.split('链接:', 1)[-1].strip()
                continue
            # 摘要
            if '摘要:' in line_s and current_post is not None:
                current_post['summary'] = line_s.split('摘要:', 1)[-1].strip()
                continue

    if current_post:
        flush_post()

    # 按评分排序，去重（同链接只保留最高分）
    seen_links = set()
    unique_posts = []
    for p in sorted(posts, key=lambda x: x['score'], reverse=True):
        if p['link'] not in seen_links:
            seen_links.add(p['link'])
            unique_posts.append(p)
        if len(unique_posts) >= top_n:
            break
    return unique_posts



def print_network(data: list):
    print("=" * 55)
    print("📡 二度人脉发现（排除已在 TARGET 的账号）")
    print("=" * 55)
    if not data:
        print("  暂无外部 RT 数据")
        return
    TAGS = {'recommend': '🔥 推荐加入 TARGET', 'evaluate': '⚡ 建议评估     ', 'candidate': '📌 备选         '}
    for d in data:
        tag = TAGS.get(d['level'], '   ')
        note = '  ← 多账号共同推荐' if d['multi_source'] else ''
        print(f"  {tag} @{d['account']:<20} 被推荐 {d['recommended_by_count']} 次 | 来自 {d['recommended_by']}{note}")


def print_account_stats(data: list):
    ADVICE = {
        'few_samples': '⚠️  样本太少',
        'mostly_rt':   '⚠️  RT 机器，考虑移除',
        'high_quality':'✅ 高质量',
        'normal':      '🆗 正常',
    }
    print()
    print("=" * 65)
    print("📊 账号发帖规律分析")
    print("=" * 65)
    print(f"  {'账号':<20} {'总量':>5} {'原创':>5} {'原创率':>6} {'RT':>5} {'回复':>5}  建议")
    print("  " + "-" * 62)
    for d in data:
        star = '★' if d['in_target'] else ' '
        print(f"  {star}@{d['account']:<19} {d['total']:>5} {d['original']:>5} "
              f"{d['original_rate']:>5}% {d['rt']:>5} {d['reply']:>5}  {ADVICE.get(d['advice'], '')}")
    print("  ★ = 当前 TARGET_ACCOUNTS 中的账号")


def print_trend(data: dict):
    dates = data['dates']
    rows  = data['accounts']
    if not dates or not rows:
        return
    print()
    print("=" * 65)
    print(f"📈 最近 {len(dates)} 天活跃趋势（每日扫描新增条数）")
    print("=" * 65)
    header = f"  {'账号':<20}" + "".join(f" {d[5:]:>8}" for d in dates)
    print(header)
    print("  " + "-" * (20 + 9 * len(dates)))
    for r in sorted(rows, key=lambda x: x['account']):
        row_str = f"  @{r['account']:<19}" + "".join(
            f" {r['days'].get(d, 0) or '.':>8}" for d in dates
        ) + f"  (共{r['total']})"
        print(row_str)


def print_hot_topics(data: dict):
    t, s = data['titles_count'], data['summaries_count']
    hot  = data['hot']
    print()
    print("=" * 55)
    print(f"🔥 近期热点话题（来自 {t} 条标题 + {s} 条摘要）")
    print("=" * 55)
    if not hot:
        print("  数据量不足，暂无明显热点（积累更多天数据后显现）")
        return
    tier1 = [d for d in hot if d['tier'] == 'hot']
    tier2 = [d for d in hot if d['tier'] == 'warm']
    tier3 = [d for d in hot if d['tier'] == 'mention']
    if tier1:
        print("  🌋 强热点（频次 ≥ 6）")
        for d in tier1:
            bar = '█' * min(d['count'], 20)
            print(f"     {d['keyword']:<12} {bar}  ({d['count']})")
    if tier2:
        print("  🔆 次热（频次 3-5）")
        print("     " + "  ".join(f"{d['keyword']}({d['count']})" for d in tier2[:15]))
    if tier3:
        print("  💡 出现（频次 2）")
        print("     " + "  ".join(d['keyword'] for d in tier3[:20]))


# ── JSON 结构化输出 ────────────────────────────────────────────────────────────

def build_json_report(records, known_targets, days) -> dict:
    network  = calc_network(records, known_targets)
    stats    = calc_account_stats(records, known_targets)
    trend    = calc_recent_trend(records, top_days=min(7, len({
        r.get('seen_at','')[:10] for r in records if r.get('seen_at')
    })))
    topics   = calc_hot_topics(top_n=25)

    return {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'scope_days': days,
        'total_records': len(records),
        'current_targets': sorted(known_targets),
        'network': {
            'description': '被 TARGET 账号转推的外部账号（二度人脉）',
            'items': network,
        },
        'account_stats': {
            'description': '各账号发帖规律统计',
            'items': stats,
        },
        'trend': {
            'description': '最近 N 天每日新增条数',
            'dates': trend['dates'],
            'accounts': trend['accounts'],
        },
        'hot_topics': {
            'description': '从推文标题+摘要提取的高频话题',
            'titles_analyzed': topics['titles_count'],
            'summaries_analyzed': topics['summaries_count'],
            'keywords': topics['hot'],
        },
        'topic_trend': calc_topic_diff(),
        'top_posts': {
            'description': '本周信息量最高的推文（按关键词密度评分）',
            'items': calc_top_posts(days=7, top_n=5),
        },
    }


def save_analysis_json(report: dict):
    """保存到 log/day/YYYY-MM-DD_analysis.json"""
    os.makedirs(DAY_LOG, exist_ok=True)
    path = os.path.join(DAY_LOG, datetime.now().strftime('%Y-%m-%d') + '_analysis.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


def save_weekly_trend_snapshot(topics: dict):
    """将 hot_topics 快照存入 log/trends/YYYY-WW.json
    每周只保留最新一份（重覆写入）。返回文件路径。
    """
    trends_dir = os.path.join(os.path.dirname(DAY_LOG), 'trends')
    os.makedirs(trends_dir, exist_ok=True)
    week_str = datetime.now().strftime('%Y-%W')
    path = os.path.join(trends_dir, f'{week_str}.json')
    snapshot = {
        'week': week_str,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'keywords': {item['keyword']: item['count'] for item in topics.get('hot', [])}
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    return path


def calc_topic_diff() -> dict:
    """对比最近两周的快照，返回趋势变化列表。
    返回格式: {rising, falling, new_this_week, prev_week, this_week}
    """
    trends_dir = os.path.join(os.path.dirname(DAY_LOG), 'trends')
    if not os.path.exists(trends_dir):
        return {'status': 'no_data', 'message': '尚无历史快照'}

    snapshots = sorted([
        f for f in os.listdir(trends_dir) if f.endswith('.json')
    ])
    if len(snapshots) < 2:
        return {'status': 'insufficient_data', 'message': '至少需要2周快照才能对比',
                'available_weeks': [s.replace('.json', '') for s in snapshots]}

    def load_snap(fname):
        with open(os.path.join(trends_dir, fname), encoding='utf-8') as f:
            return json.load(f)

    prev = load_snap(snapshots[-2])
    curr = load_snap(snapshots[-1])
    prev_kw = prev.get('keywords', {})
    curr_kw = curr.get('keywords', {})

    rising, falling, new_kws = [], [], []
    for kw, cnt in curr_kw.items():
        if kw not in prev_kw:
            new_kws.append({'keyword': kw, 'count': cnt})
        else:
            diff = cnt - prev_kw[kw]
            if diff >= 3:
                rising.append({'keyword': kw, 'count': cnt, 'delta': diff})
            elif diff <= -3:
                falling.append({'keyword': kw, 'count': cnt, 'delta': diff})

    rising.sort(key=lambda x: x['delta'], reverse=True)
    falling.sort(key=lambda x: x['delta'])
    new_kws.sort(key=lambda x: x['count'], reverse=True)

    return {
        'status': 'ok',
        'prev_week': prev.get('week'),
        'this_week': curr.get('week'),
        'rising': rising[:5],
        'falling': falling[:5],
        'new_this_week': new_kws[:5],
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    json_mode = '--json' in args
    day_args  = [a for a in args if a.isdigit()]
    days = int(day_args[0]) if day_args else None

    if not os.path.exists(SEEN_FILE):
        err = {'error': f'找不到 {SEEN_FILE}，请先运行 x_ideas_scan.py'}
        if json_mode:
            print(json.dumps(err, ensure_ascii=False, indent=2))
        else:
            print(f"❌ {err['error']}")
        return

    records       = load_records(days)
    known_targets = load_target_accounts()

    if json_mode:
        report = build_json_report(records, known_targets, days)
        saved  = save_analysis_json(report)
        # 同步保存本周热点快照（供下周趋势对比）
        snap_path = save_weekly_trend_snapshot(calc_hot_topics(top_n=25))
        # stdout 输出纯 JSON（OpenClaw 解析用）
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"\n# 已保存到: {saved}", file=sys.stderr)
        print(f"# 趋势快照: {snap_path}", file=sys.stderr)
    else:
        # 人类可读输出
        scope = f"最近 {days} 天" if days else "全部历史"
        print(f"\n📚 共加载 {len(records)} 条记录（{scope}）")
        print(f"🎯 当前 TARGET 账号: {sorted(known_targets)}\n")

        print_network(calc_network(records, known_targets))
        print_account_stats(calc_account_stats(records, known_targets))
        print_trend(calc_recent_trend(records, top_days=min(7, len({
            r.get('seen_at','')[:10] for r in records if r.get('seen_at')
        }))))
        print_hot_topics(calc_hot_topics(top_n=25))
        print()


if __name__ == '__main__':
    main()
