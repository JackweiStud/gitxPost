#!/usr/bin/env python3
"""
X 粉丝数据采集器
使用共享浏览器会话层 (browser_cdp_session.py)
通过 patchright + headless Chrome 抓取 X profile 页面的粉丝/关注数

数据存储: xinfo/log/followers.json（时间序列追加）
"""

import os
import sys
import time
import json
import re
import argparse
from pathlib import Path
from typing import Set
from datetime import datetime, timedelta, timezone

# 导入共享浏览器会话层
from browser_cdp_session import ChromeCDPSession, create_session

try:
    from patchright.sync_api import Error as PlaywrightError
    from patchright.sync_api import TimeoutError as PlaywrightTimeoutError
    from patchright.sync_api import Page
except Exception:
    PlaywrightError = Exception
    PlaywrightTimeoutError = Exception
    Page = object

# 配置
PROFILE_DIR = os.environ.get("XPOST_PROFILE_DIR")
if PROFILE_DIR:
    USER_DATA_DIR = Path(PROFILE_DIR)
else:
    USER_DATA_DIR = Path(__file__).parent / "chrome_data_mirror"

# 数据存储路径
XINFO_LOG_DIR = Path(__file__).parent / "xinfo" / "log"
FOLLOWERS_JSON = XINFO_LOG_DIR / "followers.json"


def _log(msg, level="INFO"):
    """输出日志到 stderr（不污染 stdout 的 JSON 输出）"""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", file=sys.stderr, flush=True)


def _parse_count_text(text: str) -> int:
    """解析 X profile 上的数字文本 → int
    
    示例:
      "79" → 79
      "1,234" → 1234
      "12.5K" → 12500
      "1.2M" → 1200000
    """
    if not text:
        return -1
    text = text.strip().replace(",", "").replace(" ", "")
    
    multiplier = 1
    if text.endswith("K") or text.endswith("k"):
        multiplier = 1000
        text = text[:-1]
    elif text.endswith("M") or text.endswith("m"):
        multiplier = 1_000_000
        text = text[:-1]
    elif text.endswith("B") or text.endswith("b"):
        multiplier = 1_000_000_000
        text = text[:-1]
    
    try:
        return int(float(text) * multiplier)
    except (ValueError, TypeError):
        return -1


def fetch_profile_stats(page: Page, username: str, timeout: int = 30) -> dict:
    """从 X profile 页面提取粉丝数据

    Returns:
        dict with keys: followers, following (or -1 if not found)
    """
    url = f"https://x.com/{username}"
    _log(f"📡 打开 profile 页面: {url}")

    page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)

    # 等待页面渲染完成（等待 follower 链接出现）
    _log("⏳ 等待页面渲染...")
    followers_selector = f'a[href="/{username}/verified_followers"], a[href="/{username}/followers"]'
    following_selector = f'a[href="/{username}/following"]'

    try:
        page.wait_for_selector(followers_selector, state="visible", timeout=15000)
    except PlaywrightTimeoutError:
        _log("⚠️  follower 链接未出现，尝试继续解析", "WARN")

    time.sleep(2)  # 额外等待确保数字渲染

    result = {"followers": -1, "following": -1}

    # 方法 1: 通过链接文本提取 (最可靠)
    try:
        # Followers
        for sel in [f'a[href="/{username}/verified_followers"]', f'a[href="/{username}/followers"]']:
            el = page.query_selector(sel)
            if el:
                text = el.inner_text()
                # 文本格式: "79 Followers" 或 "79\nFollowers"
                num_match = re.search(r'([\d,.]+[KkMmBb]?)', text)
                if num_match:
                    result["followers"] = _parse_count_text(num_match.group(1))
                    _log(f"✅ Followers: {result['followers']} (from text: {text.strip()!r})")
                break

        # Following
        el = page.query_selector(following_selector)
        if el:
            text = el.inner_text()
            num_match = re.search(r'([\d,.]+[KkMmBb]?)', text)
            if num_match:
                result["following"] = _parse_count_text(num_match.group(1))
                _log(f"✅ Following: {result['following']}")
    except Exception as e:
        _log(f"方法 1 提取失败: {e}", "WARN")

    # 方法 2: 通过 JS 提取 (兜底)
    if result["followers"] == -1:
        try:
            _log("🔄 使用 JS 兜底提取...")
            js_result = page.evaluate(r"""() => {
                const links = document.querySelectorAll('a[role="link"]');
                const stats = {};
                for (const link of links) {
                    const href = link.getAttribute('href') || '';
                    const text = link.innerText || '';
                    if (href.includes('follower')) {
                        const m = text.match(/([\d,.]+[KkMmBb]?)/);
                        if (m) stats.followers = m[1];
                    }
                    if (href.includes('following')) {
                        const m = text.match(/([\d,.]+[KkMmBb]?)/);
                        if (m) stats.following = m[1];
                    }
                }
                return stats;
            }""")
            if js_result.get("followers"):
                result["followers"] = _parse_count_text(js_result["followers"])
                _log(f"✅ Followers (JS): {result['followers']}")
            if js_result.get("following"):
                result["following"] = _parse_count_text(js_result["following"])
                _log(f"✅ Following (JS): {result['following']}")
        except Exception as e:
            _log(f"方法 2 JS 提取失败: {e}", "WARN")

    # 方法 3: 从页面全文中正则匹配 (最后兜底)
    if result["followers"] == -1:
        try:
            body_text = page.evaluate("() => document.body.innerText")
            # 匹配 "79 Followers"
            m = re.search(r'([\d,.]+[KkMmBb]?)\s*Followers', body_text)
            if m:
                result["followers"] = _parse_count_text(m.group(1))
                _log(f"✅ Followers (regex): {result['followers']}")
            m2 = re.search(r'([\d,.]+[KkMmBb]?)\s*Following', body_text)
            if m2:
                result["following"] = _parse_count_text(m2.group(1))
                _log(f"✅ Following (regex): {result['following']}")
        except Exception as e:
            _log(f"方法 3 正则提取失败: {e}", "WARN")

    return result


def _parse_tweet_datetime_utc(datetime_str: str):
    """解析 X 的 ISO 时间字符串并统一转成 UTC。"""
    if not datetime_str:
        return None
    try:
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _migrate_activity_records(records: list[dict]) -> list[dict]:
    """统一历史记录结构到 activity_24h。"""
    migrated = []
    for record in records:
        row = dict(record)
        if "activity_24h" in row:
            try:
                row["activity_24h"] = max(0, int(row.get("activity_24h", 0)))
            except Exception:
                row["activity_24h"] = 0
        else:
            total = 0
            for key in ("posts", "replies", "articles"):
                try:
                    total += max(0, int(row.get(key, 0)))
                except Exception:
                    continue
            row["activity_24h"] = total
        row.pop("posts", None)
        row.pop("replies", None)
        row.pop("articles", None)
        migrated.append(row)
    return migrated


def fetch_activity_stats(page: Page, username: str, timeout: int = 30) -> dict:
    """抓取用户近 24 小时活动统计。"""
    _log("📊 开始采集近 24 小时活动统计...")

    activity_ok = False
    activity_24h = 0
    seen_ids: Set[str] = set()
    all_discovered_ids: Set[str] = set()
    max_idle_rounds = 6
    max_rounds = 30
    url = f"https://x.com/{username}/with_replies"
    window_end_utc = datetime.now(timezone.utc)
    window_start_utc = window_end_utc - timedelta(hours=24)

    try:
        last_err = None
        for attempt in range(2):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                last_err = None
                break
            except Exception as e:
                last_err = e
                _log(f"⚠️  打开 {url} 失败 (第 {attempt + 1} 次): {e}", "WARN")
                time.sleep(2.0)
        if last_err is not None:
            raise last_err

        try:
            page.wait_for_selector(
                'article[data-testid="tweet"]',
                state="visible",
                timeout=min(15000, timeout * 1000),
            )
        except Exception:
            pass

        _log("📡 活动采集 — Posts & replies: " + url)
        _log("  ⏳ 首屏等待 4.0s ...")
        time.sleep(4.0)

        _log("  🐢 慢速预热滚动（8 步 × 700px + 1.5s，再二次向下扫）...")
        for _ in range(8):
            try:
                page.evaluate("window.scrollBy(0, 700)")
            except Exception:
                break
            time.sleep(1.5)
        for _ in range(4):
            try:
                page.evaluate("window.scrollBy(0, 700)")
            except Exception:
                break
            time.sleep(1.0)
        try:
            page.evaluate("window.scrollTo(0, 0)")
        except Exception:
            pass
        time.sleep(1.5)
        _log("  ✅ 预热完成，开始正式采集轮次")
        idle_streak = 0
        for rnd in range(max_rounds):
            before_total = len(all_discovered_ids)
            before_window = len(seen_ids)
            try:
                raw_metas = page.evaluate(
                    r"""(username) => {
                        const results = [];
                        const seenPairs = new Set();

                        function pathOf(href) {
                            try {
                                return new URL(href, location.origin).pathname || '';
                            } catch {
                                return href || '';
                            }
                        }

                        function extractSid(pathname) {
                            const m = pathname.match(/\/status\/(\d+)/);
                            return m ? m[1] : null;
                        }

                        function isOwnProfileLink(pathname) {
                            return pathname === `/${username}`;
                        }

                        function isTweetPath(pathname) {
                            return pathname.startsWith(`/${username}/status/`) || pathname.startsWith('/i/status/');
                        }

                        function extractMeta(art) {
                            const userNameNode = art.querySelector('[data-testid="User-Name"]');
                            const ownAuthorLink = userNameNode
                                ? Array.from(userNameNode.querySelectorAll('a[href]')).find((a) => isOwnProfileLink(pathOf(a.getAttribute('href') || '')))
                                : null;
                            if (!ownAuthorLink) return null;

                            const anchors = Array.from(art.querySelectorAll('a[href]'));
                            const ownTweetAnchors = anchors.filter((a) => isTweetPath(pathOf(a.getAttribute('href') || '')));

                            for (const a of ownTweetAnchors) {
                                const pathname = pathOf(a.getAttribute('href') || '');
                                const sid = extractSid(pathname);
                                const timeEl = a.querySelector('time[datetime]');
                                const dt = timeEl ? timeEl.getAttribute('datetime') : null;
                                if (sid && dt) {
                                    return { sid, dt };
                                }
                            }

                            for (const t of art.querySelectorAll('time[datetime]')) {
                                const dt = t.getAttribute('datetime');
                                if (!dt) continue;
                                const nearestAnchor = t.closest('a[href]');
                                if (!nearestAnchor) continue;
                                const pathname = pathOf(nearestAnchor.getAttribute('href') || '');
                                if (!isTweetPath(pathname)) continue;
                                const sid = extractSid(pathname);
                                if (sid) {
                                    return { sid, dt };
                                }
                            }

                            for (const a of ownTweetAnchors) {
                                const pathname = pathOf(a.getAttribute('href') || '');
                                const sid = extractSid(pathname);
                                if (!sid) continue;
                                const timeEl = art.querySelector('time[datetime]');
                                const dt = timeEl ? timeEl.getAttribute('datetime') : null;
                                if (dt) {
                                    return { sid, dt };
                                }
                            }

                            return null;
                        }

                        for (const art of document.querySelectorAll('article[data-testid="tweet"]')) {
                            const meta = extractMeta(art);
                            if (!meta) continue;
                            const key = meta.sid + '|' + meta.dt;
                            if (seenPairs.has(key)) continue;
                            seenPairs.add(key);
                            results.push(meta);
                        }
                        return results;
                    }"""
                    ,
                    username,
                )
            except Exception as e:
                _log(f"❌ 抓取页面 Metadata 失败: {e}", "ERROR")
                return {"activity_24h": 0, "activity_ok": False}

            for item in raw_metas:
                sid = item["sid"]
                all_discovered_ids.add(sid)
                dt = _parse_tweet_datetime_utc(item["dt"])
                if dt is None or dt < window_start_utc or dt > window_end_utc:
                    continue
                seen_ids.add(sid)

            new_total = len(all_discovered_ids) - before_total
            new_window = len(seen_ids) - before_window
            _log(
                f"  📝 [Posts & replies] 第 {rnd + 1}/{max_rounds} 轮: DOM 发现 {len(raw_metas)} 对时标, "
                f"新 ID {new_total} 条 (近24h新 {new_window} 条, 总计 {len(seen_ids)} 条)"
            )

            if new_total == 0:
                idle_streak += 1
                _log(f"  ⏸️  持续无新内容 ({idle_streak}/{max_idle_rounds})")
                if idle_streak >= max_idle_rounds:
                    _log("  ⏹️  [Posts & replies] 连续无新推文，结束本段")
                    break
            else:
                idle_streak = 0

            if rnd >= max_rounds - 1:
                break
            try:
                page.evaluate("window.scrollBy(0, 900)")
            except Exception as e:
                _log(f"❌ 滚动失败: {e}", "ERROR")
                return {"activity_24h": 0, "activity_ok": False}
            time.sleep(1.5)

        activity_24h = len(seen_ids)
        activity_ok = True
        _log(f"✅ 近 24 小时活动统计: Activity(24h)={activity_24h}")
    except Exception as e:
        _log(f"❌ 活动统计失败: {e}", "ERROR")

    return {
        "activity_24h": activity_24h,
        "activity_ok": activity_ok,
    }


def save_stats(username: str, stats: dict) -> dict:
    """将数据追加到 followers.json 时间序列文件
    
    文件格式:
    {
        "username": "jackaiwison",
        "records": [
            {"date": "2026-03-30", "time": "10:30:00", "followers": 79, "following": 482},
            ...
        ]
    }
    """
    XINFO_LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 读取现有数据
    data = {"username": username, "records": []}
    if FOLLOWERS_JSON.exists():
        try:
            data = json.loads(FOLLOWERS_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    data["records"] = _migrate_activity_records(data.get("records", []))
    
    # 更新 username（支持后续切换）
    data["username"] = username
    
    now = datetime.now()
    activity_ok = stats.get("activity_ok", True)

    record = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "followers": stats.get("followers", -1),
        "following": stats.get("following", -1),
        "activity_24h": stats.get("activity_24h", 0),
    }

    # 检查今天是否已有记录 → 更新而非追加
    today = record["date"]
    existing_idx = None
    for i, r in enumerate(data.get("records", [])):
        if r.get("date") == today:
            existing_idx = i
            break

    if existing_idx is not None and not activity_ok:
        old = data["records"][existing_idx]
        _log(
            "⚠️  活动统计未成功，保留今日已有的 activity_24h",
            "WARN",
        )
        record["activity_24h"] = old.get("activity_24h", record["activity_24h"])

    if existing_idx is not None:
        old = data["records"][existing_idx]
        _log(
            f"📝 更新今日记录 (之前: followers={old.get('followers')}, "
            f"following={old.get('following')}, activity_24h={old.get('activity_24h', 0)})"
        )
        data["records"][existing_idx] = record
    else:
        data["records"].append(record)
    
    # 原子写入
    tmp_path = FOLLOWERS_JSON.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(FOLLOWERS_JSON)
    
    _log(f"💾 已保存到 {FOLLOWERS_JSON} (共 {len(data['records'])} 条记录)")
    
    # 计算变化
    records = data["records"]
    change = None
    if len(records) >= 2:
        prev = records[-2] if existing_idx is None else (records[existing_idx - 1] if existing_idx > 0 else None)
        if prev and prev.get("followers", -1) >= 0 and record["followers"] >= 0:
            diff = record["followers"] - prev["followers"]
            change = {
                "previous_date": prev["date"],
                "previous_followers": prev["followers"],
                "diff": diff,
                "direction": "up" if diff > 0 else ("down" if diff < 0 else "same"),
            }
    
    return {**record, "change": change, "total_records": len(records)}


def main():
    parser = argparse.ArgumentParser(
        description="X 粉丝数据采集器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  %(prog)s jackaiwison               # 采集粉丝数
  %(prog)s jackaiwison --headless     # 无头模式
  %(prog)s jackaiwison --json-only    # 仅输出 JSON
""")
    
    parser.add_argument("username", help="X username (不含 @)")
    parser.add_argument("--headless", action="store_true", default=True,
                        help="以无头模式运行 (默认: True)")
    parser.add_argument("--no-headless", action="store_true",
                        help="显示浏览器窗口")
    parser.add_argument("--json-only", action="store_true",
                        help="仅输出 JSON 到 stdout")
    parser.add_argument("--timeout", type=int, default=30,
                        help="页面加载超时秒数 (默认: 30)")
    
    args = parser.parse_args()
    headless = not args.no_headless
    
    session = None
    try:
        # 启动浏览器
        _log("🌐 启动浏览器...")
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        session = create_session(profile_dir=USER_DATA_DIR, headless=headless)
        page = session.create_task_page()
        
        # 采集粉丝数据
        stats = fetch_profile_stats(page, args.username, timeout=args.timeout)

        if stats["followers"] == -1:
            result = {
                "ok": False,
                "error": f"无法获取 @{args.username} 的粉丝数据，可能需要先登录",
                "username": args.username,
            }
            if args.json_only:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"❌ 无法获取 @{args.username} 的粉丝数据")
                print("   可能原因: 未登录 / 账号不存在 / 网络问题")
                print("   建议: 先运行 `xpost post-login` 完成登录")
            return 1

        # 采集活动数据（过去 24 小时，来自 /with_replies）
        _log("📊 采集近 24 小时活动数据...")
        activity_stats = fetch_activity_stats(page, args.username, timeout=args.timeout)

        # 合并数据
        stats.update(activity_stats)

        # 保存数据
        save_result = save_stats(args.username, stats)
        
        result = {
            "ok": True,
            "username": args.username,
            "followers": stats["followers"],
            "following": stats["following"],
            "activity_24h": stats["activity_24h"],
            "activity_ok": stats.get("activity_ok", True),
            "date": save_result["date"],
            "time": save_result["time"],
            "change": save_result.get("change"),
            "total_records": save_result["total_records"],
            "data_file": str(FOLLOWERS_JSON),
        }
        
        if args.json_only:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"\n{'='*50}")
            print(f"📊 @{args.username} 数据统计")
            print(f"{'='*50}")
            print(f"  👥 Followers: {stats['followers']}")
            print(f"  👤 Following: {stats['following']}")
            print(f"  📝 Activity(24h): {stats['activity_24h']}")
            ao = stats.get("activity_ok", True)
            print(f"  {'✅' if ao else '⚠️ '} 近 24 小时活动采集: {'成功' if ao else '失败（已尽量保留上次写入）'}")
            if save_result.get("change"):
                c = save_result["change"]
                arrow = "📈" if c["diff"] > 0 else ("📉" if c["diff"] < 0 else "➡️")
                sign = "+" if c["diff"] > 0 else ""
                print(f"  {arrow} 变化: {sign}{c['diff']} (vs {c['previous_date']})")
            print(f"  📅 时间: {save_result['date']} {save_result['time']}")
            print(f"  💾 数据: {FOLLOWERS_JSON}")
            print(f"  📊 累计: {save_result['total_records']} 条记录")
            print(f"{'='*50}")
        
        return 0
    
    except KeyboardInterrupt:
        _log("用户中断")
        return 130
    except Exception as e:
        _log(f"错误: {e}", "ERROR")
        if args.json_only:
            print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False, indent=2))
        else:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        return 1
    finally:
        if session:
            _log("🔒 关闭浏览器...")
            session.close()


if __name__ == "__main__":
    sys.exit(main())
