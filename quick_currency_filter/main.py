#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国服 POE2 通货过滤器一键生成
1. 检查价格 JSON 是否在 12 小时内，是则跳过拉取
2. 生成 currency.filter 过滤器文件
"""

import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRICES_FILE = os.path.join(SCRIPT_DIR, "poe2_currency_prices.json")
MAX_AGE_SECONDS = 12 * 3600  # 12 小时


def prices_fresh():
    """价格文件是否存在且未超过 12 小时"""
    if not os.path.exists(PRICES_FILE):
        return False
    mtime = os.path.getmtime(PRICES_FILE)
    age = time.time() - mtime
    return age < MAX_AGE_SECONDS


def main():
    print("=" * 60)
    print("国服 POE2 通货过滤器 - 一键生成")
    print("=" * 60)

    # 1. 价格数据
    if prices_fresh():
        age_min = int((time.time() - os.path.getmtime(PRICES_FILE)) / 60)
        print(f"[价格] 文件未超过 12 小时（已存在 {age_min} 分钟），跳过拉取")
    else:
        if os.path.exists(PRICES_FILE):
            age_hr = int((time.time() - os.path.getmtime(PRICES_FILE)) / 3600)
            print(f"[价格] 文件已过期（{age_hr} 小时前），重新拉取...")
        else:
            print("[价格] 文件不存在，首次拉取...")

        # 调用 fetch_currency_prices.py
        from fetch_currency_prices import main as fetch_main
        fetch_main()

    print()

    # 2. 生成过滤器
    print("[过滤器] 生成中...")
    from generate_filter import main as gen_main
    gen_main()

    print()
    print("=" * 60)
    print("全部完成!")
    print(f"  价格文件: {PRICES_FILE}")
    print(f"  过滤器:   {os.path.join(SCRIPT_DIR, 'currency.filter')}")
    print("=" * 60)


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
