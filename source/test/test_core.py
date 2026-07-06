import re
from collections import defaultdict

# ---------------------------
# 模板（按优先级顺序排好）
# 每个模板: (类别, 组名, 模板字符串)
# 注意：同一组可以出现多条模板（多行），只有所有行都被匹配才算该组命中
# ---------------------------
templates = [
    ("prefix", "前缀1", "怪物移动速度加快 #%"),
    ("prefix", "前缀1", "怪物攻击速度加快 #%"),
    ("prefix", "前缀1", "怪物施法速度加快 #%"),
    ("prefix", "前缀2", "怪物的击中有 #% 的几率造成流血"),
    ("prefix", "前缀3", "怪物移动速度加快 #%"),   # 与前缀1有重叠
    ("prefix", "前缀3", "怪物护甲提高 #%"),
    ("suffix", "后缀1", "怪物受到的诅咒效果总降 #%"),
    ("suffix", "后缀2", "召唤生物的伤害穿透 #% 元素抗性"),
]

# ---------------------------
# 要匹配的道具词缀（示例）
# ---------------------------
item_mods = [
    "怪物移动速度加快 23%",
    "怪物护甲提高 23%",
    "怪物攻击速度加快 22%",
    "怪物施法速度加快 24%",
    "怪物的击中有 20% 的几率造成流血",
    "怪物受到的诅咒效果总降 40%",
    "召唤生物的伤害穿透 15% 元素抗性",
]

# ---------------------------
# 编译模板为正则：支持模板中出现多个 "#%" 占位
# num_pattern 允许整数或小数，允许数字与 % 之间有可选空白
# ---------------------------
def compile_templates(template_list):
    compiled = []
    num_pattern = r"([+-]?\d+(?:\.\d+)?)\s*%"  # 捕获数字（可能是小数），允许空格然后%
    for t_type, group, tmpl in template_list:
        parts = tmpl.split("#%")
        # 用分段拼接来避免 re.escape 把占位符干扰
        pattern = "^"
        for i, part in enumerate(parts):
            pattern += re.escape(part)
            if i != len(parts) - 1:
                pattern += num_pattern
        pattern += "$"
        compiled.append({
            "type": t_type,
            "group": group,
            "tmpl": tmpl,
            "regex": re.compile(pattern)
        })
    return compiled

compiled = compile_templates(templates)

# ---------------------------
# 分配逻辑（核心）
# 按模板顺序遍历 compiled 列表（优先级顺序），
# 对每个模板查找第一个尚未被占用且能匹配的 item_mods，
# 一旦找到就“占用”该词缀（一个词缀不能同时分配给多个模板）。
# ---------------------------
used_mod = [False] * len(item_mods)             # 标记哪个实际词缀已被占用
assignments = [None] * len(compiled)            # 每个模板（按索引）分配到的实际词缀信息或 None

for t_idx, templ in enumerate(compiled):
    regex = templ["regex"]
    for m_idx, mod in enumerate(item_mods):
        if used_mod[m_idx]:
            continue
        m = regex.match(mod)
        if m:
            # 将该实际词缀分配给当前模板（按模板顺序优先）
            assignments[t_idx] = {
                "mod_index": m_idx,
                "mod_text": mod,
                "values": list(m.groups())  # 支持多个 #%
            }
            used_mod[m_idx] = True
            break  # 模板分配成功，继续下一个模板

# ---------------------------
# 聚合：按组检查“所有行是否都已分配”
# 如果组内所有模板都有对应 assignment，则该组命中
# ---------------------------
group_to_template_idxs = defaultdict(list)
group_type = {}  # 记录每个组对应的 type（prefix/suffix）

for idx, templ in enumerate(compiled):
    g = templ["group"]
    group_to_template_idxs[g].append(idx)
    if g not in group_type:
        group_type[g] = templ["type"]

matched_groups = {}
for g, tidx_list in group_to_template_idxs.items():
    assigned_info = []
    all_assigned = True
    for tidx in tidx_list:
        a = assignments[tidx]
        assigned_info.append({
            "template_index": tidx,
            "template_str": compiled[tidx]["tmpl"],
            "assigned": a is not None,
            "assigned_mod_index": a["mod_index"] if a else None,
            "assigned_mod_text": a["mod_text"] if a else None,
            "captured_values": a["values"] if a else None
        })
        if a is None:
            all_assigned = False
    matched_groups[g] = {
        "type": group_type[g],
        "required_count": len(tidx_list),
        "all_assigned": all_assigned,
        "details": assigned_info
    }

# ---------------------------
# 统计前缀/后缀数量（按组去重），并输出详细信息
# ---------------------------
prefix_count = sum(1 for ginfo in matched_groups.values() if ginfo["type"] == "prefix" and ginfo["all_assigned"])
suffix_count = sum(1 for ginfo in matched_groups.values() if ginfo["type"] == "suffix" and ginfo["all_assigned"])

# 输出：模板分配情况（按模板顺序）
print("=== 模板分配（按模板优先级顺序） ===")
for tidx, templ in enumerate(compiled):
    a = assignments[tidx]
    if a:
        print(f"[模板#{tidx}] {templ['type']} {templ['group']} | 模板文本: '{templ['tmpl']}'")
        print(f"    -> 分配到词缀 #{a['mod_index']}: '{a['mod_text']}' 捕获值: {a['values']}")
    else:
        print(f"[模板#{tidx}] {templ['type']} {templ['group']} | 模板文本: '{templ['tmpl']}'")
        print("    -> 未分配到任何词缀")

# 输出：哪些实际词缀未被占用（未匹配或被保留）
print("\n=== 未被占用的实际词缀（未匹配或被优先级吞掉） ===")
for m_idx, mod in enumerate(item_mods):
    if not used_mod[m_idx]:
        print(f"#{m_idx}: {mod}")

# 输出：每个组是否全部匹配
print("\n=== 组命中情况（要求组内所有模板行均被匹配） ===")
for g, info in matched_groups.items():
    status = "命中" if info["all_assigned"] else "未命中"
    print(f"组 {g} ({info['type']}), 需要 {info['required_count']} 行: {status}")
    for d in info["details"]:
        if d["assigned"]:
            print(f"    模板 '{d['template_str']}' -> 匹配词缀 #{d['assigned_mod_index']}: '{d['assigned_mod_text']}' 捕获: {d['captured_values']}")
        else:
            print(f"    模板 '{d['template_str']}' -> 未匹配")

print("\n=== 最终汇总 ===")
print(f"前缀数量 (按组计): {prefix_count}")
print(f"后缀数量 (按组计): {suffix_count}")
print("命中的前缀组: ", sorted([g for g,v in matched_groups.items() if v["type"]=="prefix" and v["all_assigned"]]))
print("命中的后缀组: ", sorted([g for g,v in matched_groups.items() if v["type"]=="suffix" and v["all_assigned"]]))
