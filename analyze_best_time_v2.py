#!/usr/bin/env python3
"""
分析最佳发布时间 V2
基于真实的雷达数据中的帖子发布时间
"""

import json
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
import glob
from zoneinfo import ZoneInfo

AUDIENCE_WEIGHT = 0.70
COMPETITION_WEIGHT = 0.20
OVERLAP_WEIGHT = 0.10

def parse_time(time_str):
    """解析时间字符串（GMT）并转换为北京时间（Asia/Shanghai）的小时"""
    try:
        # "Wed, 29 Apr 2026 16:55:34 GMT"
        # 兼容不同系统对 %Z 的解析，我们先去掉末尾的 GMT 字符串，并显式指定为 UTC 时区
        time_str_clean = time_str.replace(" GMT", "").strip()
        dt_utc = datetime.strptime(time_str_clean, "%a, %d %b %Y %H:%M:%S")
        dt_utc = dt_utc.replace(tzinfo=ZoneInfo('UTC'))
        # 转换为北京时间 (CST, UTC+8)
        dt_bj = dt_utc.astimezone(ZoneInfo('Asia/Shanghai'))
        return dt_bj.hour
    except:
        return None

def get_hour_reason(pt_hour):
    """根据硅谷时间小时返回时间段的特征描述"""
    if 7 <= pt_hour < 9:
        return "早通勤段，用户醒来刷手机"
    elif 9 <= pt_hour < 11:
        return "上午工作/浏览黄金档"
    elif 11 <= pt_hour < 13:
        return "午休时段，小憩社交"
    elif 13 <= pt_hour < 17:
        return "下午工作间隙浏览"
    elif 17 <= pt_hour < 19:
        return "下班通勤/晚餐闲暇"
    elif 19 <= pt_hour < 22:
        return "晚间黄金高峰期，深度阅读最佳"
    elif 22 <= pt_hour < 24:
        return "深夜尾声，流量开始衰退"
    else:
        return "深夜/凌晨睡眠时段，流量低谷"

def get_local_activity(hour):
    """返回本地小时的活跃系数 (0.0 - 1.0)。"""
    activity_curve = {
        0: 0.2, 1: 0.1, 2: 0.05, 3: 0.05, 4: 0.1, 5: 0.2, 6: 0.4,
        7: 0.7, 8: 0.9, 9: 1.0, 10: 0.95, 11: 0.85, 12: 0.9, 13: 0.85,
        14: 0.8, 15: 0.75, 16: 0.7, 17: 0.65, 18: 0.7, 19: 0.9, 20: 0.95,
        21: 1.0, 22: 0.75, 23: 0.4
    }
    return activity_curve.get(hour, 0.5)

def get_region_hours(bj_hour, is_dst=True):
    """返回北京时间对应的欧美主要区域小时。"""
    et_offset = -12 if is_dst else -13
    pt_offset = -15 if is_dst else -16
    cet_offset = -6 if is_dst else -7
    return {
        'et': (bj_hour + et_offset) % 24,
        'pt': (bj_hour + pt_offset) % 24,
        'cet': (bj_hour + cet_offset) % 24,
        'ap': bj_hour,
    }

def get_europe_us_traffic_score(bj_hour, is_dst=True):
    """
    根据北京时间小时计算欧美受众活跃基准分 (0-10)
    目标受众：
    1. 北美地区 (权重 70%): 美东 35% + 美西 35%
    2. 欧洲地区 (权重 25%): 英国/中欧主工作生活时段
    3. 亚太地区 (权重 5%): 仅作为少量兜底，不主导推荐
    """
    region_hours = get_region_hours(bj_hour, is_dst=is_dst)

    # 1. 亚太活跃度 (北京时间)，只保留少量权重
    ap_activity = get_local_activity(region_hours['ap'])

    # 2. 美东活跃度
    et_activity = get_local_activity(region_hours['et'])

    # 3. 美西活跃度
    pt_activity = get_local_activity(region_hours['pt'])

    # 4. 欧洲活跃度
    cet_activity = get_local_activity(region_hours['cet'])

    traffic_score = (
        et_activity * 0.35 +
        pt_activity * 0.35 +
        cet_activity * 0.25 +
        ap_activity * 0.05
    ) * 10  # 放大到 0-10 分

    return traffic_score

def get_western_overlap_score(bj_hour, is_dst=True):
    """奖励美东、美西、欧洲同时处于可触达时段的窗口。"""
    region_hours = get_region_hours(bj_hour, is_dst=is_dst)
    activities = [
        get_local_activity(region_hours['et']),
        get_local_activity(region_hours['pt']),
        get_local_activity(region_hours['cet']),
    ]
    active_regions = sum(1 for activity in activities if activity >= 0.65)
    return min(10.0, active_regions * 3.0 + min(activities))

def score_release_window(bj_hour, competition_score, is_dst=True):
    """综合评分：欧美活跃主导，避堵辅助，连续重叠窗口加稳定性。"""
    audience_score = get_europe_us_traffic_score(bj_hour, is_dst=is_dst)
    overlap_score = get_western_overlap_score(bj_hour, is_dst=is_dst)
    final_score = (
        audience_score * AUDIENCE_WEIGHT +
        competition_score * COMPETITION_WEIGHT +
        overlap_score * OVERLAP_WEIGHT
    )
    return {
        'audience_score': audience_score,
        'competition_score': competition_score,
        'overlap_score': overlap_score,
        'final_score': final_score,
    }

def load_radar_posts(result_files):
    """从雷达结果中读取 preview 样本帖子。"""
    posts = []
    days_with_posts = 0

    for result_file in result_files:
        try:
            with open(result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            day_posts = data.get('summary', {}).get('new_ideas_preview', [])
            if day_posts:
                days_with_posts += 1
                posts.extend(day_posts)
        except Exception as e:
            print(f"⚠️  读取 {result_file} 失败: {e}")

    return posts, {
        'source': 'preview',
        'days_with_posts': days_with_posts,
    }

def analyze_radar_posting_times(result_files=None, output_file=None):
    """分析雷达中大V的发帖时间分布"""

    print("=" * 60)
    print("基于真实雷达数据的最佳发布时间分析")
    print("=" * 60)
    print()

    # 读取最近7天的雷达数据
    if result_files is None:
        result_files = sorted(glob.glob('xinfo/log/day/*_result.json'))[-7:]
    else:
        result_files = [str(path) for path in result_files]

    print(f"📊 分析数据范围: 最近 {len(result_files)} 天")
    for f in result_files:
        date = Path(f).stem.replace('_result', '')
        print(f"  - {date}")
    print()

    # 统计每小时的发帖数量
    hour_counts = defaultdict(int)
    total_posts = 0

    posts, source_stats = load_radar_posts(result_files)
    for item in posts:
        time_str = item.get('time')
        if time_str:
            hour = parse_time(time_str)
            if hour is not None:
                hour_counts[hour] += 1
                total_posts += 1

    print(f"✅ 成功分析 {total_posts} 条帖子的发布时间（数据源: new_ideas_preview）")
    print()

    # 计算每小时的发帖占比
    print("📈 雷达大V发帖时间分布（北京时间）")
    print("-" * 60)

    hour_stats = []
    for hour in range(24):
        count = hour_counts.get(hour, 0)
        percentage = (count / total_posts * 100) if total_posts > 0 else 0
        hour_stats.append({
            'hour': hour,
            'count': count,
            'percentage': percentage
        })

    # 排序：从多到少
    hour_stats_sorted = sorted(hour_stats, key=lambda x: x['count'], reverse=True)

    print("发帖最多的时间段（竞争最激烈）:")
    for i, stat in enumerate(hour_stats_sorted[:5], 1):
        bar = '█' * int(stat['percentage'] / 2)
        print(f"  {i}. {stat['hour']:02d}:00 - {stat['count']:3d}条 ({stat['percentage']:5.2f}%) {bar}")

    print()
    print("发帖最少的时间段（竞争最小）:")
    for i, stat in enumerate(reversed(hour_stats_sorted[-5:]), 1):
        bar = '░' * int(stat['percentage'] / 2) if stat['percentage'] > 0 else ''
        print(f"  {i}. {stat['hour']:02d}:00 - {stat['count']:3d}条 ({stat['percentage']:5.2f}%) {bar}")

    print()

    # 完整24小时分布
    print("完整24小时分布:")
    for stat in sorted(hour_stats, key=lambda x: x['hour']):
        bar = '█' * int(stat['percentage'] / 2)
        print(f"  {stat['hour']:02d}:00 - {stat['count']:3d}条 ({stat['percentage']:5.2f}%) {bar}")

    print()

    # 综合推荐 (全面评估 24 小时每一小时的黄金窗口)
    print("🎯 每日 24 小时发布窗口评分与推荐 (目标受众: 欧美用户，北京时间输出)")
    print("-" * 60)

    # 1. 动态获取当前的北京时间和硅谷时间，以确定当前是否处于夏令时(DST)
    now_bj = datetime.now(ZoneInfo('Asia/Shanghai'))
    now_pt = now_bj.astimezone(ZoneInfo('America/Los_Angeles'))
    is_dst = now_pt.dst() != timedelta(0)

    # 获取竞争度分布的最大和最小值，以进行比例拉伸归一化
    percentages = [stat['percentage'] for stat in hour_stats]
    max_pct = max(percentages) if percentages else 1.0
    min_pct = min(percentages) if percentages else 0.0
    pct_range = max_pct - min_pct
    if pct_range == 0:
        pct_range = 1.0

    recommendations = []

    for bj_hour in range(24):
        # 构造今天北京时间该小时的 datetime 对象
        dt_bj = datetime.combine(
            now_bj.date(),
            datetime.min.time().replace(hour=bj_hour),
            tzinfo=ZoneInfo('Asia/Shanghai')
        )
        # 转换为硅谷时间
        dt_pt = dt_bj.astimezone(ZoneInfo('America/Los_Angeles'))
        pt_hour = dt_pt.hour

        # 真实雷达竞争统计
        count = hour_counts.get(bj_hour, 0)
        percentage = (count / total_posts * 100) if total_posts > 0 else 0

        # 归一化避堵竞争评分 (0-10 分，发帖占比越低表示竞争越小，分数越高)
        competition_score = 10 * (max_pct - percentage) / pct_range

        score = score_release_window(bj_hour, competition_score, is_dst=is_dst)

        recommendations.append({
            'hour': bj_hour,
            'time': f"北京时间 {bj_hour:02d}:00-{bj_hour+1:02d}:00 (对应硅谷 {pt_hour:02d}:00)",
            'audience_score': score['audience_score'],
            'competition_score': score['competition_score'],
            'overlap_score': score['overlap_score'],
            'final_score': score['final_score'],
            'reason': get_hour_reason(pt_hour),
            'radar_posts': count,
            'radar_percentage': percentage,
            'pt_hour': pt_hour
        })

    # 按综合评分降序排列
    recommendations.sort(key=lambda x: x['final_score'], reverse=True)

    print("🏆 最佳发布窗口排行 (Top 5)")
    for i, rec in enumerate(recommendations[:5], 1):
        print(f"{i}. {rec['time']} (综合评分: {rec['final_score']:.2f}/10)")
        print(f"   欧美受众活跃: {rec['audience_score']:.1f}/10 | 避堵竞争度: {rec['competition_score']:.1f}/10 | 欧美重叠: {rec['overlap_score']:.1f}/10")
        print(f"   特征: {rec['reason']}")
        print(f"   竞争实况: 雷达监控发帖 {rec['radar_posts']}条 ({rec['radar_percentage']:.2f}%)")
        print()

    print("✅ 每日固定推荐窗口（不随当前时间变化）")
    for i, rec in enumerate(recommendations[:5], 1):
        print(f"  {i}. {rec['time']} | 综合评分 {rec['final_score']:.2f}/10")
    print()

    # 保存结果
    result = {
        'analysis_time': now_bj.isoformat(),
        'target_audience': '欧美用户',
        'data_source': source_stats,
        'data_range': [Path(f).stem.replace('_result', '') for f in result_files],
        'total_posts_analyzed': total_posts,
        'hour_distribution': hour_stats,
        'recommendations': recommendations,
        'daily_recommendations': recommendations[:5],
    }

    output_file = Path(output_file) if output_file else Path('xinfo/log/best_time_analysis_v2.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"📄 详细结果已保存到: {output_file}")
    print()

    return result

if __name__ == '__main__':
    analyze_radar_posting_times()
