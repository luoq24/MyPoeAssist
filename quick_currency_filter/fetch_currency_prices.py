#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国服 POE2 通货价格获取脚本
基于 ref_docs/国服通货价格获取方案.md 实现

流程: 获取联赛列表 -> 拉取价格文件 -> base64+gzip解码 -> 过滤通货 -> 价格归一化 -> 输出JSON
"""

import base64
import gzip
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

# ============================================================
# 配置
# ============================================================
CDN_BASE = "https://cf.981001.xyz"
FALLBACK_BASE = "https://www.710421059.xyz/file"
PLATFORM = "tx2"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# 脚本所在目录，结果文件也输出到此处
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "poe2_currency_prices.json")


# ============================================================
# HTTP 工具
# ============================================================
def get_timestamp():
    """分钟级时间戳（毫秒），用于命中 CDN 缓存"""
    return (int(time.time() * 1000) // 60000) * 60000


def http_get(url, max_redirects=5):
    """HTTP GET 请求，自动跟随重定向，返回响应体文本"""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=30) as resp:
        # 处理重定向
        if 300 <= resp.status < 400 and "Location" in resp.headers:
            if max_redirects <= 0:
                raise RuntimeError("重定向次数过多")
            location = resp.headers["Location"]
            # 处理相对路径重定向
            if location.startswith("/"):
                from urllib.parse import urlparse

                parsed = urlparse(url)
                location = f"{parsed.scheme}://{parsed.netloc}{location}"
            return http_get(location, max_redirects - 1)
        # 读取并解码
        raw = resp.read()
        return raw.decode("utf-8")


# ============================================================
# 联赛列表
# ============================================================
def fetch_leagues():
    """获取联赛列表，返回 tx2 平台的联赛"""
    node = random.randint(1, 9)
    ts = get_timestamp()
    url = f"{CDN_BASE}/{node}/remoteCode/league.json?t={ts}"
    print(f"[联赛] 请求: {url}")
    text = http_get(url)
    leagues = json.loads(text)
    tx2_leagues = [l for l in leagues if l.get("plat") == PLATFORM]
    print(f"[联赛] 获取到 {len(tx2_leagues)} 个 tx2 联赛:")
    for l in tx2_leagues:
        print(f"  - leagueType={l.get('leagueType')}, name={l.get('id', l.get('name', '未知'))}")
    return tx2_leagues


def pick_current_league(leagues):
    """
    从联赛列表中选取当前赛季（非永久、非专家）。
    永久=leagueType 1 或 11, 专家=名称(id)含"专家"。
    """
    for l in leagues:
        lt = l.get("leagueType", 0)
        league_id = l.get("id", l.get("name", ""))
        if lt in (1, 11):
            continue  # 永久/永久专家
        if "专家" in league_id:
            continue  # 赛季专家
        return l
    # 兜底：取 leagueType 最小的非永久联赛
    non_permanent = [l for l in leagues if l.get("leagueType") not in (1, 11)]
    if non_permanent:
        return sorted(non_permanent, key=lambda x: x.get("leagueType", 999))[0]
    return None


# ============================================================
# 价格拉取与解码
# ============================================================
def fetch_prices(league_type):
    """拉取指定联赛的价格文件，解码返回 JSON 数组"""
    ts = get_timestamp()
    file_name = f"fkhprice_{PLATFORM}_{league_type}.txt"
    node = random.randint(1, 9)
    primary_url = f"{CDN_BASE}/{node}/{file_name}?t={ts}"
    fallback_url = f"{FALLBACK_BASE}/{file_name}?t={ts}"

    text = None
    # 主 URL
    try:
        print(f"[价格] 请求主 CDN: {primary_url}")
        text = http_get(primary_url)
        print(f"[价格] 主 CDN 成功, 响应长度: {len(text)} 字符")
    except Exception as e:
        print(f"[价格] 主 CDN 失败: {e}")

    # 备用 URL
    if text is None:
        try:
            print(f"[价格] 请求备用 URL: {fallback_url}")
            text = http_get(fallback_url)
            print(f"[价格] 备用 URL 成功, 响应长度: {len(text)} 字符")
        except Exception as e:
            print(f"[价格] 备用 URL 也失败: {e}")
            raise RuntimeError("无法获取价格文件，主/备用 URL 均不可用")

    # 解码: trim -> base64 -> gunzip -> JSON
    print("[价格] 开始解码 (base64 -> gunzip -> JSON)...")
    raw_bytes = base64.b64decode(text.strip())
    json_bytes = gzip.decompress(raw_bytes)
    data = json.loads(json_bytes.decode("utf-8"))
    print(f"[价格] 解码完成, 共 {len(data)} 条物品")
    return data


# ============================================================
# 通货过滤与归一化
# ============================================================
def process_currencies(prices):
    """
    过滤通货条目 (frameType=5) 并做价格归一化。
    归一化基准: 混沌石 (Chaos Orb) 的 calculated 值。
    """
    currencies = [p for p in prices if p.get("frameType") == 5]
    print(f"[通货] frameType=5 通货条目: {len(currencies)}")

    # 找混沌石基准
    chaos = None
    for c in currencies:
        if c.get("name") == "混沌石" or c.get("name_en") == "Chaos Orb":
            chaos = c
            break

    if chaos:
        chaos_base = chaos.get("calculated", 1)
        print(f"[通货] 混沌石基准: calculated={chaos_base}")
    else:
        chaos_base = 1
        print("[通货] 警告: 未找到混沌石，使用基准=1")

    # 归一化
    result = []
    for c in currencies:
        calculated = c.get("calculated", 0)
        chaos_value = round(calculated / chaos_base, 6) if chaos_base else 0
        item = {
            "name": c.get("name", ""),
            "name_en": c.get("name_en", ""),
            "baseType": c.get("baseType", ""),
            "baseType_en": c.get("baseType_en", ""),
            "category": c.get("category", ""),
            "chaosValue": chaos_value,       # 混沌石等价价格（归一化后）
            "divineValue": round(c.get("calculatedDiv", 0), 6),  # 神圣石等价价格
            "rawValue": calculated,           # 原始价格
            "chaosBase": chaos_base,          # 归一化基准（混沌石的 calculated）
            "count": c.get("count", 0),       # 市场在售数量
            "totalStacksize": c.get("totalStacksize", 0),
            "leagueType": c.get("leagueType", 0),
            "icon": c.get("icon", ""),
            "detailsUrl": c.get("detailsUrl", ""),
        }
        result.append(item)

    # 按混沌石价格降序排列
    result.sort(key=lambda x: x["chaosValue"], reverse=True)
    return result, chaos_base


# ============================================================
# 主流程
# ============================================================
def main():
    # 1. 获取联赛列表，确定当前赛季
    print("=" * 60)
    print("国服 POE2 通货价格获取")
    print("=" * 60)

    league = None
    try:
        leagues = fetch_leagues()
        league = pick_current_league(leagues)
    except Exception as e:
        print(f"[警告] 获取联赛列表失败: {e}，将使用默认 leagueType=2")

    if league:
        league_type = league.get("leagueType", 2)
        league_name = league.get("id", league.get("name", "未知"))
        print(f"\n[选定联赛] {league_name} (leagueType={league_type})")
    else:
        league_type = 2
        league_name = "奥杜尔秘符(默认)"
        print(f"\n[选定联赛] {league_name} (leagueType={league_type})")

    # 2. 拉取价格文件
    print()
    prices = fetch_prices(league_type)

    # 3. 过滤通货 + 归一化
    print()
    currencies, chaos_base = process_currencies(prices)

    # 4. 构建输出
    now = datetime.now(timezone.utc)
    output = {
        "meta": {
            "description": "国服 POE2 通货价格表",
            "league": league_name,
            "leagueType": league_type,
            "platform": PLATFORM,
            "fetchTime": now.isoformat(),
            "priceSource": "poecurrency.top (via CDN)",
            "chaosBase": chaos_base,
            "totalItems": len(prices),
            "currencyCount": len(currencies),
        },
        "currencies": currencies,
    }

    # 5. 写入 JSON 文件（固定文件名，每次覆盖）
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print(f"完成! 共 {len(currencies)} 条通货")
    print(f"输出文件: {OUTPUT_FILE}")

    # 打印前 20 条预览
    print()
    print("--- 价格 TOP 20 ---")
    print(f"{'名称':<20} {'英文名':<30} {'混沌石等价':>12} {'神圣石等价':>12}")
    print("-" * 80)
    for c in currencies[:20]:
        name = c["name"][:18]
        name_en = c["name_en"][:28]
        print(f"{name:<20} {name_en:<30} {c['chaosValue']:>12.4f} {c['divineValue']:>12.6f}")

    return OUTPUT_FILE


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
