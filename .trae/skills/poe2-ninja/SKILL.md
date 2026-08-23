---
name: "poe2-ninja"
description: "从 poe.ninja 获取 PoE2 的榜单构建、角色技能/装备、经济价格等数据。适用于用户想查某职业/升华/关键被动/技能宝石的上榜构建、看高玩怎么配装或触发某个机制时使用。"
---

# poe2-ninja — 从 poe.ninja 查询 PoE2 数据

本文档记录从 [poe.ninja](https://poe.ninja/poe2) 获取 PoE2 数据的技术，包含两种方式：

1. **网页抓取（推荐，无需逆向）**：直接对榜单/角色页面发起 `WebFetch`，解析页面内容。
2. **公开 API**：调用 poe.ninja 未公开但稳定的 JSON 端点，适合程序化批量获取。

使用前先确认用户要查的性质（构建榜单 / 单个角色细节 / 经济价格），再选对应方式。

---

## 何时使用本技能

- 用户想查某个 **职业(class)** / **升华(ascendancy)** / **关键被动(keypassive)** / **灵魂宝石(spiritgem)** 的上榜构建，例如“有哪些人用 COC 触发”。
- 用户想看某高玩角色的 **配装、技能连法、升华点法、触发机制**。
- 用户想查当前联盟的 **经济/通货/物品价格**。

---

## 一、网页抓取（推荐）

页面即 HTML，`WebFetch` 可直接拿到结构化 Markdown 文本，无需 API 密钥。

### 1. 榜单列表页（Builds 首页）

URL 模板：

```
https://poe.ninja/poe2/builds/<league>?<filter参数>
```

- `league` 用联盟短名，例如当前联盟 `runesofaldur`（可在页面顶部 League 下拉框看到）。
- 过滤器参数均需 **URL 编码**（空格用 `+`）。

**常用过滤器参数**（可组合，全部可选）：

| 参数 | 含义 | 示例 |
|---|---|---|
| `class` | 职业 | `class=Shaman` |
| `ascendancy` | 升华 | `ascendancy=Bringer+of+the+Apocalypse` |
| `keypassives` | 关键被动（升华/关键点） | `keypassives=Bringer+of+the+Apocalypse` |
| `spiritgems` | 灵魂宝石（含触发宝石） | `spiritgems=Cast+on+Critical` |
| `mainskills` | 主技能 | `mainskills=Comet` |
| `sort` | 排序，如按 DPS | `sort=dps` |

**真实示例**（本次任务所用）：

```
https://poe.ninja/poe2/builds/runesofaldur?class=Shaman&keypassives=Bringer+of+the+Apocalypse&spiritgems=Cast+on+Critical
```

**页面返回内容**：
- 顶部“Found **N** characters”给出符合条件的人数。
- 一个表格：角色名、等级、生命/ES/EHP/DPS、关键点、上榜 snip 图标。
- 每个角色名是到角色详情页的链接。

> 注意：`WebFetch` 返回的是降噪后的文本，表格会被转成 Markdown 表格，作者/装饰图标等会丢失，但数字与链接保留。

### 2. 角色详情页

点击角色进入后 URL 模板：

```
https://poe.ninja/poe2/builds/<league>/character/<accountName>/<charName>?i=<index>&search=<原过滤器>
```

例如：

```
https://poe.ninja/poe2/builds/runesofaldur/character/Ghostpaws-0724/พ่อมา
```

**页面返回内容（按区块）**：
- **Profile / Account**：账户名、`Last fetched`（数据新鲜度）。
- **Equipment**：装备、Vaal 部位、基础珠宝。
- **Stats**：角色属性、防御、模拟 EHP / Max Hit。
- **Skill DPS Estimation**：各技能的估计 DPS、暴击率/暴击伤害、命中次数。
- **Ascendancy & Keystones**：升华与关键被动点法（含说明文本）。
- **Skills**：技能列表，触发宝石会标 `(trigger)`，并列出其链接的宝石。

### 3. 解析技巧（实战经验）

判断“拿什么触发某个机制”（如 COC 用什么触发）：

1. 看 `Skills` 区块里被标 `(trigger)` 的宝石，例如 `Cast on Critical (trigger)`，其下一层就是它链接施放的技能。
2. 找**暴击源技能**：通常是升华赋予的技能（如 `Bringer of the Apocalypse` 给的 `Apocalypse`），或自施的 `Arc`/`Spark` 等高频命中技能。
3. 用 `Skill DPS Estimation` 交叉验证：暴击率（如 100%）和暴击伤害（如 900%）越高的技能，越可能是暴击源。
4. 结合 `Ascendancy & Keystones` 看暴击增伤来源（如 `Pain Attunement` 低血增伤、`Elemental Equilibrium`、专用珠宝）。

---

## 二、公开 API（程序化获取）

poe.ninja 无官方公开页面，但存在稳定可用的 JSON 端点（无需鉴权）。

### 1. PoE2 构建/榜单元数据

```
GET https://poe.ninja/poe2/api/data/build-index-state
```

- 无需鉴权，裸请求即可。
- 返回各当前联盟的**上榜职业/升华使用占比（share-of-ladder）及趋势标志**，适合做“主流套路的宏观占比”分析。

### 2. 经济 / 物品价格（PoE1 为主）

经济端点结构统一，按 `type` 区分数据类目：

```
https://poe.ninja/poe1/api/economy/stash/current/<type>/overview?league=<league>&type=<type>
```

其中 `<type>` 可选：`Currency`、`Fragment`、`SkillGem`、`DivinationCard`、`UniqueMap`、`UniqueWeapon`、`UniqueArmour` 等。

> PoE2 的经济/构建具体 JSON 端点变化较快，且未被官方文档化。**优先用网页抓取**，如确需 JSON，先在浏览器 Network 面板观察请求路径，再按实际路径调用。

### 3. 相关官方 API（参考）

- GGG 官方开发者 API：`https://www.pathofexile.com/developer/docs/reference`（账户/角色/仓库等，需 OAuth）。
- GGG 交易 API：`https://www.pathofexile.com/api/trade/search/<league>`（交易搜索，需 POST JSON）。
- poe.ninja 不提供经济价格，GGG 官方也不提供，价格数据只能来自 poe.ninja 这类爬取站。

---

## 三、注意事项 / 限制

- **数据新鲜度**：每个角色页有 `Last fetched` 字段，老存档可能过期（如 218 days ago），解读时注意。
- **字段变动**：经济端点字段名偶有变化（如 `sparkline` → `sparkLine`），解析时做容错。
- **URL 编码**：多词过滤器必须 URL 编码，空格用 `+`，否则请求失败或结果为空。
- **链接可用性**：`WebFetch` 对需登录/鉴权的页面无效；poe.ninja 公开页无需鉴权，可直接抓。
- **联盟名**：从页面顶部 League 下拉框取当前有效联盟短名，不同联盟 URL 不同。