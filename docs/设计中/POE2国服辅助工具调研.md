# POE2 国服辅助工具调研笔记

> 调研日期：2026-06-26
> 调研目的：评估 XileHUD（开源 POE overlay）改造用于《流放之路2》国服的可行性与数据资源
> 关联项目：[XileHUD/poe_overlay](https://github.com/XileHUD/poe_overlay) · [leeween/poe2-trade-pob](https://github.com/leeween/poe2-trade-pob) · [ninja.710421059.xyz](https://ninja.710421059.xyz/)

---

## 一、XileHUD 项目分析

### 1.1 技术栈

- **Electron 28.3.0** —— 桌面应用框架
- **TypeScript** —— 主要开发语言
- **uiohook-napi** —— 系统级键盘/鼠标钩子库
- **Vite 5** —— 构建工具

### 1.2 核心工作机制

| 模块 | 关键文件 | 作用 |
|------|---------|------|
| 剪贴板监控 | [src/main/clipboard-monitor.ts](file:///e:/python_space/poe_overlay/src/main/clipboard-monitor.ts) | 500ms 轮询系统剪贴板，正则匹配物品格式 |
| 系统级键鼠钩子 | [src/main/hotkeys/uiohook-trigger.ts](file:///e:/python_space/poe_overlay/src/main/hotkeys/uiohook-trigger.ts) | 注册全局键盘/鼠标事件，可模拟按键（如模拟 Ctrl+C） |
| 物品解析 | [src/main/item-parser.ts](file:///e:/python_space/poe_overlay/src/main/item-parser.ts) | 解析剪贴板中的物品文本 → 结构化数据 |
| 词缀数据库 | [src/main/modifier-database.ts](file:///e:/python_space/poe_overlay/src/main/modifier-database.ts) | 加载 JSON 数据 + 词缀过滤/权重计算 |
| 覆盖层渲染 | Electron `BrowserWindow` | 半透明、置顶的覆盖窗口 |

### 1.3 工作流

```
用户手动 Ctrl+C (游戏内) → 剪贴板轮询检测 → 解析物品 → 显示在覆盖窗口
```

本质上是一个 **"智能增强型剪贴板查看器"**，类似 PoE Trade Macro。

---

## 二、国服安全性评估

### 2.1 安全方面（不容易被检测为外挂）

- ✅ 不修改游戏内存（无内存扫描/修改）
- ✅ 不注入游戏进程（无 DLL 注入、API Hook）
- ✅ 不拦截/修改网络包（不代理游戏网络流量）
- ✅ 仅读取系统剪贴板（用户主动复制 → 工具读取）
- ✅ 不自动操作游戏角色

### 2.2 风险方面（可能被检测的因素）

| 风险点 | 风险等级 | 说明 |
|--------|---------|------|
| uiohook-napi 全局钩子 | ⚠️ 高 | 系统级键鼠钩子，腾讯 ACE 反作弊敏感 |
| 模拟按键（triggerCopyShortcut） | ⚠️ 高 | 会触发反作弊的自动化输入检测 |
| 透明覆盖窗口 | ⚠️ 中高 | Electron 透明 Overlay 与游戏重叠可能被检测 |
| 进程特征 | ⚠️ 中 | 反作弊可能扫描 Electron 进程签名 |

### 2.3 国服特有风险

国服由腾讯代理，使用 **ACE（Anti-Cheat Expert）** 反作弊系统，特点：

- 驱动级检测（运行在内核级别，可检测用户态钩子）
- 更激进的 Overlay 检测策略
- 行为分析 + 进程黑白名单

---

## 三、"纯剪贴板 + 第二屏"安全策略

### 3.1 核心原则

| 策略 | 说明 |
|------|------|
| ❌ 不与游戏窗口重叠 | 覆盖层显示在另一块显示器上 |
| ❌ 不注入/钩取游戏进程 | 无 uiohook、无 DLL 注入 |
| ❌ 不模拟任何按键 | 不使用 triggerCopyShortcut |
| ✅ 只读剪贴板 | 用户手动 Ctrl+C，工具读剪贴板响应 |

### 3.2 可安全保留的功能

| 模块 | 安全性 | 备注 |
|------|-------|------|
| [clipboard-monitor.ts](file:///e:/python_space/poe_overlay/src/main/clipboard-monitor.ts) | ✅ 低风险 | 需改造：用 Electron `globalShortcut` 替代 uiohook |
| [item-parser.ts](file:///e:/python_space/poe_overlay/src/main/item-parser.ts) | ✅ 零风险 | 纯数据处理 |
| [modifier-database.ts](file:///e:/python_space/poe_overlay/src/main/modifier-database.ts) | ✅ 零风险 | 纯本地数据+计算 |
| 物品词缀展示面板 | ✅ 零风险 | 数据展示 |
| Character Planner 系列 | ✅ 零风险 | 宝石/天赋/升华数据 |
| 交易历史记录 | ✅ 零风险 | 纯本地记录 |
| Crafting 辅助面板 | ✅ 零风险 | 通货/精华数据展示 |

### 3.3 必须移除/改造的高风险模块

| 模块 | 处理方式 | 原因 |
|------|---------|------|
| [uiohook-trigger.ts](file:///e:/python_space/poe_overlay/src/main/hotkeys/uiohook-trigger.ts) | ❌ 彻底移除 | 系统级键鼠钩子，ACE 敏感 |
| [keyboard-monitor.ts](file:///e:/python_space/poe_overlay/src/main/keyboard-monitor.ts) | ❌ 彻底移除 | 同样基于 iohook 的全局钩子 |
| `triggerCopyShortcut()` | ❌ 彻底移除 | 模拟按键触发复制，高风险 |
| 透明 Overlay 窗口 | ⚠️ 改造 | 改为第二屏普通窗口 |

### 3.4 可扩展的新功能

基于"第二屏显示"策略，可以扩展：

| 功能 | 说明 |
|------|------|
| 即时配装评分器 | 复制物品后自动对比当前装备 |
| 词缀价值估算 | 根据 Tier/ILvl/基底给出价值参考 |
| 工艺台辅助 | 显示装备可用工艺选项及成本 |
| 地图/异界图辅助 | 复制 Waystone 后分析词缀难度 |
| 通货/精华计算器 | 复制一组通货显示折合价值 |
| 装备对比工具 | 多件装备并排对比词缀差异 |
| POB 集成增强 | 复制装备后导入 POB 查看 Build 影响 |
| 掉落分析仪表盘 | 长期记录掉落数据统计分析 |
| 配方检查器 | 复制一组物品提示可用 Vendor 配方 |
| 升级路线规划 | 显示当前等级的可用装备基底和宝石 |

---

## 四、国服数据库现状

### 4.1 调研结论

XileHUD 项目的**所有数据文件均为英文，且无任何国际化/本地化架构**：

| 文件 | 示例 | 国服对应 |
|------|------|---------|
| [Currency.json](file:///e:/python_space/poe_overlay/data/poe2/Rise%20of%20the%20Abyssal/Currency.json) | `"Chaos Orb"`, `"Removes a random modifier..."` | 混沌石，移除一个随机词缀... |
| [Bases.json](file:///e:/python_space/poe_overlay/data/poe2/Rise%20of%20the%20Abyssal/Bases.json) | `"Crude Claw"`, `"Wolfbone Claw"` | 粗糙之爪，狼骨之爪 |
| 词缀数据库 | `"#% increased Fire Damage"` | 增加 #% 火焰伤害 |

[item-parser.ts](file:///e:/python_space/poe_overlay/src/main/item-parser.ts) 中所有正则和关键字也全部针对英文硬编码。

### 4.2 改造难度评估

| 模块 | 工作量 | 难度 |
|------|--------|------|
| 剪贴板检测模式 → 中文 | 小 | 低 |
| ItemParser 解析正则 → 中文 | 中 | 中 |
| **词缀数据库 → 中文** | **大** | **高** |
| 基底名称 → 中文 | 中 | 中 |
| 通货/精华/预兆数据 → 中文 | 中 | 中 |

总体估计：一个人完整改造需要 **2-4 周**，其中大部分时间花在中文数据采集和验证上。

---

## 五、关键发现：现成的国服中英翻译字典

### 5.1 🎯 [leeween/poe2-trade-pob](https://github.com/leeween/poe2-trade-pob)

**这个项目就是为了解决"国服简中词缀 → 英文"翻译而生的**：

- **[poe2-lang-sc.json](https://github.com/leeween/poe2-trade-pob/blob/main/poe2-lang-sc.json)** — 英文原文 → 简体中文 翻译字典
- 数据来源：[ninja.710421059.xyz](https://ninja.710421059.xyz/) 国服专属 poe.ninja 镜像
- 配套 Python 脚本 [poe2-pob-dict-build.py](https://github.com/leeween/poe2-trade-pob/blob/main/poe2-pob-dict-build.py) 可反向生成中→英查表

**直接复用该字典就能把英文数据翻译成中文显示**。

字典结构示例：

```json
{
  "Increased Fire Damage": "增加火焰伤害",
  "Adds 1-2 Physical Damage": "附加 1-2 物理伤害"
}
```

### 5.2 数据源：[ninja.710421059.xyz](https://ninja.710421059.xyz/)

- 国服专属的 poe.ninja 镜像
- 提供 Economy / Builds / Atlas Trees / Passives 等完整数据
- 与 [leeween/poe2-trade-pob](https://github.com/leeween/poe2-trade-pob) 字典同源

---

## 六、国服相关项目与资源汇总

### 6.1 🎯 国服数据资源（重点）

| 资源 | 用途 | 备注 |
|------|------|------|
| [poe2-trade-pob (GitHub)](https://github.com/leeween/poe2-trade-pob) | **简中↔英文 词缀翻译字典** | ✅ **现成的国服数据库** |
| [ninja.710421059.xyz](https://ninja.710421059.xyz/) | **国服 poe.ninja 镜像** | ✅ **国服专属数据源** |
| [POE2DB 多语言信息助手](https://greasyfork.org/zh-CN/scripts/559966) | poe2db 三语对照 | Greasemonkey 脚本 |
| [Data of Exile - POE2Data (iOS)](https://apps.apple.com/cn/app/data-of-exile-poe2data/id6746666681) | iOS 中文数据库 App | 付费 ¥12 |
| [流亡编年史 poedb.tw/cn](https://poedb.tw/cn/) | 中文版 Wiki/数据库 | 在线浏览 |
| [POE2 Lens](https://poe2lens.com/) | 国服交易数据 | 在线 |
| [Pathofexile 维基:中英对照](https://pathofexile.fandom.com/zh/wiki/Pathofexile_%E7%BB%B4%E5%9F%BA:%E8%A7%84%E8%8C%83/%E4%B8%AD%E8%8B%B1%E5%AF%B9%E7%85%A7) | 中英文术语对照规范 | 社区维护 |

### 6.2 类似工具项目（英文版为主）

| 项目 | 类型 | GitHub |
|------|------|--------|
| **XileHUD**（已分析） | Electron overlay | github.com/XileHUD/poe_overlay |
| **Lailloken/Exile-UI** | AHK 轻量级 overlay | github.com/Lailloken/Exile-UI |
| **ExileXP** | 升级指引 overlay | github.com/andreins/ExileXP |
| **PoE Overlay** | Overwolf overlay | github.com/PoE-Overlay |
| **Path of Building 2** | 离线 BD 模拟器 | github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2 |

---

## 七、推荐方案：XileHUD + 国服字典的混合改造

### 7.1 核心思路

**XileHUD（现有）的英文数据** + **poe2-lang-sc.json（国服字典）** = 完整的国服中文数据

- 底层数据保持英文（自动跟随国际服更新）
- 显示层通过字典翻译成中文
- 解析层用中英双匹配正则

### 7.2 代码改造清单

| 文件 | 改造内容 |
|------|---------|
| 新建 `src/main/i18n.ts` | 翻译字典加载 + `t()` 函数 |
| 新建 `data/poe2-lang-sc.json` | 直接复用 leeween 项目的字典 |
| [item-parser.ts](file:///e:/python_space/poe_overlay/src/main/item-parser.ts) | 剪贴板正则：中英文双匹配 |
| [clipboard-monitor.ts](file:///e:/python_space/poe_overlay/src/main/clipboard-monitor.ts) | 物品检测关键字中英都支持 |
| [modifier-database.ts](file:///e:/python_space/poe_overlay/src/main/modifier-database.ts) | 词缀展示前过翻译表 |

### 7.3 关键代码示例

**翻译模块（新建）**：

```typescript
// 加载 poe2-lang-sc.json
import translationDict from './data/poe2-lang-sc.json';

// 翻译函数
function t(text: string): string {
  return translationDict[text] || text;
}

// 翻译解析出的物品
const item = parser.parse(clipboardText);
const translatedItem = {
  ...item,
  name: t(item.name),
  baseType: t(item.baseType),
  itemClass: t(item.itemClass),
  modifiers: item.modifiers.map(t),
};
```

**item-parser.ts 中正则改造示例**：

```typescript
// 原始英文匹配
/^Item Class:/m
/^Rarity:\s*(\w+)/

// 改造后中英双匹配
/^(Item Class|物品类别):/m
/^(Rarity|稀有度):\s*(\S+)/
```

### 7.4 方案优势

- ✅ **不需要任何中文游戏内数据反编译**——直接复用开源字典
- ✅ **不需要从 poe2db 抓取**——字典已经做好
- ✅ **底层数据是英文（最新版本）**——中文只是显示层
- ✅ **大部分代码逻辑零改动**——只需在显示处套一层翻译
- ✅ **第二屏策略不变**——仍然是非透明、显示在另一显示器的 Electron 窗口

---

## 八、最终结论

| 维度 | 结论 |
|------|------|
| 安全性 | 采用"纯剪贴板 + 第二屏"策略，**风险接近零** |
| 改造工作量 | 中等：底层数据复用，仅需改造解析+显示层 |
| 数据资源 | **leeween/poe2-trade-pob 字典 + ninja.710421059.xyz 数据源** 现成可用 |
| 维护成本 | 低：英文数据自动跟随国际服更新，中文字典复用开源项目 |
| 推荐 | ✅ **XileHUD + 国服字典** 是当前最优改造路径 |

---

## 参考链接

- [XileHUD GitHub](https://github.com/XileHUD/poe_overlay)
- [leeween/poe2-trade-pob GitHub](https://github.com/leeween/poe2-trade-pob)
- [ninja.710421059.xyz 国服 ninja 镜像](https://ninja.710421059.xyz/)
- [流放之路2常用工具网站 (ali213)](https://3g.ali213.net/gl/html/1778631.html)
- [POE2DB 多语言信息助手 (Greasyfork)](https://greasyfork.org/zh-CN/scripts/559966)
- [Lailloken/Exile-UI GitHub](https://github.com/Lailloken/Exile-UI)
- [ExileXP 论坛介绍](https://www.pathofexile.com/forum/view-thread/3934202)
- [Data of Exile - POE2Data (iOS App Store)](https://apps.apple.com/cn/app/data-of-exile-poe2data/id6746666681)
- [poe2db.tw 冰霜伤害中文版](https://poe2db.tw/cn/Cold_damage)
- [Path of Exile 维基: 中英对照规范](https://pathofexile.fandom.com/zh/wiki/Pathofexile_%E7%BB%B4%E5%9F%BA:%E8%A7%84%E8%8C%83/%E4%B8%AD%E8%8B%B1%E5%AF%B9%E7%85%A7)
