#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国服 POE2 通货过滤器生成脚本
读取 poe2_currency_prices.json，按堆叠数量分档隐藏低价值通货，输出 currency.filter

规则（对应 template.filter）:
  - 按堆叠数量分 5 档: 1个、2个、3个、4个、5个以上
  - 每档隐藏条件: 单件 chaosValue × 堆叠数 < 0.5 混沌石
  - 即: 单件 chaosValue < 0.5 / 堆叠数 的通货在该档位被隐藏
"""

import json
import os
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRICES_FILE = os.path.join(SCRIPT_DIR, "poe2_currency_prices.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "currency.filter")

# 阈值：总价值低于此值（混沌石等价）的通货堆将被隐藏
THRESHOLD_CHAOS = 0.5

# 白名单：这些通货无论价格高低都不隐藏（中文名或英文名均可）
WHITELIST = {
    "Simulacrum Splinter",   # 拟像裂片
    "Vaal Orb",              # 瓦尔宝珠
    "Breach Splinter",       # 裂隙碎片     
    "Verisium",              # 维金
    "Exceptional Verisium",  # 卓越维金
}

# 每个 Hide 块中 BaseType 的最大数量（避免单行过长）
CHUNK_SIZE = 50

# 堆叠数量分档: (描述, 最小堆叠数, StackSize 过滤条件)
TIERS = [
    ("单个",    1, "StackSize = 1"),
    ("2个",     2, "StackSize = 2"),
    ("3个",     3, "StackSize = 3"),
    ("4个",     4, "StackSize = 4"),
    ("5个以上", 5, "StackSize >= 5"),
]


def get_base_type(item):
    """获取用于过滤器匹配的英文名称"""
    return (item.get("name_en")
            or item.get("baseType_en")
            or item.get("name")
            or "").strip()


def generate_filter(data):
    meta = data.get("meta", {})
    currencies = data.get("currencies", [])

    lines = []
    # 文件头
    lines.append("# ============================================")
    lines.append("# 国服 POE2 通货过滤器 - 自动生成")
    lines.append(f"# 联赛: {meta.get('league', '未知')} (leagueType={meta.get('leagueType', '?')})")
    lines.append(f"# 生成时间: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"# 规则: 隐藏总价值 < {THRESHOLD_CHAOS} 混沌石 的通货（按堆叠数分档）")
    lines.append(f"# 通货总数: {meta.get('currencyCount', '?')}")
    lines.append("# ============================================")
    lines.append("")

    # 过滤有效通货（有名称、有价格、不在白名单中）
    valid = []
    for c in currencies:
        name = get_base_type(c)
        if not name:
            continue
        if name in WHITELIST or c.get("name", "") in WHITELIST:
            continue  # 白名单通货不隐藏
        cv = c.get("chaosValue", 0)
        if cv <= 0:
            continue  # 无价格通货不隐藏（默认显示）
        valid.append({
            "name": name,
            "chaosValue": cv,
            "totalStacksize": c.get("totalStacksize", 0),
        })

    # 按分档生成 Hide 块
    for desc, stack_size, stack_cond in TIERS:
        threshold = THRESHOLD_CHAOS / stack_size
        # 找出该档位需要隐藏的通货:
        #   单件 chaosValue < 0.5 / stack_size
        #   且该通货实际可能出现此堆叠数 (totalStacksize >= stack_size 或未知)
        to_hide = []
        for c in valid:
            if c["chaosValue"] < threshold:
                ts = c["totalStacksize"]
                if ts > 0 and ts < stack_size:
                    continue  # 该通货最大堆叠数不足，不可能出现此堆叠
                to_hide.append(c["name"])

        # 去重并排序
        to_hide = sorted(set(to_hide))

        lines.append(
            f"# 隐藏低价值通货({desc})，条件：总价值 < {THRESHOLD_CHAOS} 混沌石"
        )

        if not to_hide:
            lines.append("# (无符合条件的通货)")
            lines.append("")
            continue

        # 分块生成 Hide 块（避免单个 BaseType 行过长）
        for i in range(0, len(to_hide), CHUNK_SIZE):
            chunk = to_hide[i:i + CHUNK_SIZE]
            base_type_str = " ".join(f'"{n}"' for n in chunk)
            lines.append("Hide")
            lines.append(f"    BaseType {base_type_str}")
            lines.append(f"    {stack_cond}")
            lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("国服 POE2 通货过滤器生成")
    print("=" * 60)

    print(f"[读取] {PRICES_FILE}")
    with open(PRICES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("meta", {})
    currencies = data.get("currencies", [])
    print(f"[数据] 联赛: {meta.get('league')}, 通货数: {meta.get('currencyCount')}")
    print(f"[规则] 隐藏总价值 < {THRESHOLD_CHAOS} 混沌石 的通货")
    print()

    # 统计各档位情况
    for desc, stack_size, _ in TIERS:
        threshold = THRESHOLD_CHAOS / stack_size
        count = sum(
            1 for c in currencies
            if 0 < c.get("chaosValue", 0) < threshold
        )
        print(f"  {desc:>6} (单件 < {threshold:.5f} chaos): {count} 种通货将被隐藏")

    # 生成过滤器
    filter_text = generate_filter(data)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(filter_text)

    print()
    print(f"[输出] {OUTPUT_FILE}")
    print("完成!")


if __name__ == "__main__":
    main()
