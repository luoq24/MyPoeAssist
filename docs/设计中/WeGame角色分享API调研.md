# WeGame POE2 角色分享 API 调研

> 调研日期：2026-06-26
> 调研目的：摸清国服角色分享链接背后的 API 接口，为「通过分享链接实时查询角色装备详情」的自用工具提供技术基础
> 数据来源：开源项目 [cn-poe-community/poexport-extension](https://github.com/cn-poe-community/poexport-extension) 源码分析 + 实际接口调用验证

***

## 一、背景

《流放之路2》国服（腾讯服）通过 WeGame 提供角色分享功能，玩家登录 WeGame 后可一键生成角色专属分享链接，格式为：

```
https://www.wegame.com.cn/helper/poe2/#/share/{shareCode}
```

《易刷》、pobzh.cn、poexport-extension 等工具均通过解析此链接，将国服角色数据导入 POB（Path of Building）。本次调研通过分析 poexport-extension 的源码（`utils/poe2_wg_api.ts`），找到了其调用的底层 API，并实测验证可用。

***

## 二、API 端点总览

所有接口均为 `POST` 请求，`Content-Type: application/json`，Host：`https://www.wegame.com.cn`

| 接口            | 路径                                                 | 用途       | 需要 role\_id |
| ------------- | -------------------------------------------------- | -------- | :---------: |
| GetRoleInfo   | `/api/v1/wegame.pallas.poe2.Profile/GetRoleInfo`   | 获取角色基本信息 |      否      |
| GetEquipments | `/api/v1/wegame.pallas.poe2.Profile/GetEquipments` | 获取装备栏道具  |      是      |
| GetTalentTree | `/api/v1/wegame.pallas.poe2.Profile/GetTalentTree` | 获取天赋树    |      是      |
| GetJewels     | `/api/v1/wegame.pallas.poe2.Profile/GetJewels`     | 获取珠宝     |      是      |
| GetSkills     | `/api/v1/wegame.pallas.poe2.Profile/GetSkills`     | 获取技能     |      是      |

***

## 三、调用流程

```
分享链接 https://www.wegame.com.cn/helper/poe2/#/share/{shareCode}
    │
    ├─① GetRoleInfo(share_code) → 拿到 role_id
    │
    └─② 并行调用（需 role_id + share_code）:
         ├─ GetEquipments → 装备列表
         ├─ GetJewels    → 珠宝列表
         ├─ GetSkills    → 技能列表
         └─ GetTalentTree → 天赋树
```

**关键点**：必须先调 GetRoleInfo 拿到 `role_id`，后续接口都依赖它。四个后续接口相互独立，可并行调用（poexport-extension 源码中正是用 `Promise.all` 并行请求）。

***

## 四、接口详情与实测数据

### 4.1 GetRoleInfo —— 获取角色基本信息

**请求体：**

```json
{
  "share_code": "HGcIsXcQZj_KJuoSXIDtUfPJuYTuBdG5tZV9QUIL9p0FBhj-rWclK_42q480DDRC",
  "area": 0,
  "from_src": "poe2_helper"
}
```

| 字段          | 类型     | 说明                    |
| ----------- | ------ | --------------------- |
| share\_code | string | 从分享链接中提取的分享码          |
| area        | int    | 区服，固定 0               |
| from\_src   | string | 来源标识，固定 `poe2_helper` |

**实测响应：**

```json
{
  "result": {
    "error_code": 0,
    "error_message": "success"
  },
  "nick_name": "",
  "role": {
    "openid": "12332682962743348914",
    "role_id": "3295052",
    "area": 0,
    "name": "浅滩冰射突突突",
    "icon": "",
    "level": 96,
    "phrase": "异界T16",
    "class_id": 0,
    "class_name": "Amazon",
    "created_time": "1780624199",
    "total_game_duration": "319835",
    "season_game_duration": "319835",
    "last_login_time": "1781083564",
    "league_id": "1152921504606848321",
    "account_name": "浅岸的沙滩#3962"
  },
  "share_code": "ogixBwOJLMYVu8uIxxYhT930qOJSiLJAR4TSYvY0GHuOCi7ya78RAzUCpk2ywBW4"
}
```

**role 对象字段说明：**

| 字段                     | 说明                        |
| ---------------------- | ------------------------- |
| role\_id               | 角色 ID，后续接口必需              |
| name                   | 角色名                       |
| level                  | 等级                        |
| phrase                 | 当前进度描述（如「异界T16」）          |
| class\_name            | 职业英文名（如 Amazon、Warrior 等） |
| created\_time          | 创角时间（Unix 时间戳，秒）          |
| total\_game\_duration  | 总游戏时长（秒）                  |
| season\_game\_duration | 本赛季游戏时长（秒）                |
| last\_login\_time      | 最后登录时间（Unix 时间戳，秒）        |
| league\_id             | 联赛 ID                     |
| account\_name          | 账号名（带#后缀）                 |

***

### 4.2 GetEquipments —— 获取装备栏道具

**请求体：**

```json
{
  "area": 0,
  "openid": "",
  "role_id": "3295052",
  "share_code": "HGcIsXcQZj_KJuoSXIDtUfPJuYTuBdG5tZV9QUIL9p0FBhj-rWclK_42q480DDRC",
  "from_src": "poe2_helper"
}
```

**响应结构：**

```json
{
  "result": { "error_code": 0, "error_message": "success" },
  "equipments": [ ...物品数组... ]
}
```

**单件装备字段（以暗金箭袋为例）：**

```json
{
  "baseType": "精工箭袋",
  "name": "卡迪罗的赌局",
  "rarity": "Unique",
  "frameType": 3,
  "frameTypeId": "Unique",
  "corrupted": true,
  "ilvl": 69,
  "inventoryId": "Offhand",
  "league": "奥杜尔秘符",
  "realm": "poe2",
  "icon": "https://poecdn.game.qq.com/gen/image/...",
  "identified": true,
  "verified": false,
  "typeLine": "精工箭袋",
  "descrText": "只能在使用弓时装备。",
  "explicitMods": ["每支射出的箭都是渐强、裂片、回转、金刚、贪婪或钝击箭矢"],
  "implicitMods": ["攻击速度提高 9%"],
  "flavourText": [""无论如何抹除，世间总有机遇。\r", "只要机制得当，一切果效都能转为己用……"\r", "——卡迪罗·佩兰德斯"],
  "properties": [{ "name": "[Quiver|箭袋]", "type": 109, "values": [] }],
  "requirements": [{ "displayMode": 0, "name": "等级", "type": 62, "values": [["66", 0]] }],
  "w": 2,
  "h": 3,
  "x": 0,
  "y": 0
}
```

**装备字段说明：**

| 字段                   | 说明                                                                                              |
| -------------------- | ----------------------------------------------------------------------------------------------- |
| baseType             | 基底类型（简体中文）                                                                                      |
| name                 | 物品名（暗金/传奇有名字，普通/魔法为空）                                                                           |
| typeLine             | 类型行，通常同 baseType                                                                                |
| rarity / frameTypeId | 稀有度：`Normal`/`Magic`/`Rare`/`Unique`                                                            |
| frameType            | 稀有度数字编码（0=普通,1=魔法,2=稀有,3=暗金）                                                                    |
| ilvl                 | 物品等级                                                                                            |
| inventoryId          | 装备位置：`Weapon`/`Offhand`/`Helmet`/`BodyArmour`/`Gloves`/`Boots`/`Amulet`/`Ring`/`Belt`/`Flask` 等 |
| league               | 联赛名（简体中文，如「奥杜尔秘符」）                                                                              |
| icon                 | 物品图标 URL（poecdn.game.qq.com）                                                                    |
| corrupted            | 是否已腐化                                                                                           |
| identified           | 是否已鉴定                                                                                           |
| explicitMods         | 显式词缀数组（简体中文）                                                                                    |
| implicitMods         | 隐式词缀数组（简体中文）                                                                                    |
| properties           | 属性数组（含 name/type/values）                                                                        |
| requirements         | 需求数组（等级/力量/敏捷/智力）                                                                               |
| flavourText          | 背景故事文本                                                                                          |
| w / h / x / y        | 物品在背包中的宽/高/坐标                                                                                   |

**实测观察到的 inventoryId 取值：** `Flask`、`Offhand`（此角色仅装备了药剂和箭袋）

***

### 4.3 其他接口

GetJewels / GetSkills / GetTalentTree 的请求体格式与 GetEquipments 完全一致（都需要 `role_id` + `share_code`），返回结构类似：

```json
{
  "result": { "error_code": 0, "error_message": "success" },
  ...各自的数据字段...
}
```

本次实测未深入展开这三个接口的响应结构，后续如需可补充。

***

## 五、关键特性

| 特性         | 说明                                               |
| ---------- | ------------------------------------------------ |
| **无需登录鉴权** | 分享码是公开的，不需要 QQ/微信 OAuth、不需要 Cookie、不需要 POESESSID |
| **实时数据**   | 反映角色当前状态，可重复查询获取最新数据                             |
| **简体中文**   | 所有文本原生简体中文，无需翻译字典                                |
| **标准格式**   | 与官方 POE API 物品 JSON 格式一致，可复用现有解析逻辑               |
| **数据丰富**   | 包含词缀、属性、需求、图标 URL 等完整信息                          |
| **并行友好**   | 四个数据接口互相独立，可并行请求                                 |

***

## 六、重要限制

### 6.1 只返回「已装备」的道具，不含背包/仓库

WeGame 分享链接的设计目的是展示角色 BD（构筑），因此 API **只返回角色身上已装备的物品**：

- 已装备的装备（武器、护甲、药剂、咒符等）
- 已镶嵌的珠宝
- 已配置的技能
- 天赋树

**无法通过此 API 查询背包/仓库中的未装备道具。**

### 6.2 分享码可能有时效性

分享码由 WeGame 生成，目前未观察到过期现象，但长期使用需关注是否存在失效机制（如玩家取消分享、赛季更替等）。

### 6.3 没有官方文档

这些接口是通过逆向工程发现的，无官方文档，存在腾讯随时变更的风险。

***

## 七、与国服交易 API 的对比

| 维度   | 交易 API（poe.game.qq.com）                                                        | 角色分享 API（wegame.com.cn） |
| ---- | ------------------------------------------------------------------------------ | ----------------------- |
| 鉴权   | 🔴 需 QQ/微信 OAuth + Cookie 持续管理                                                 | 🟢 无需鉴权                 |
| 用途   | 搜索/查询市场挂牌                                                                      | 查询指定角色的装备/天赋/技能         |
| 数据范围 | 全服玩家挂牌的道具                                                                      | 单个角色的已装备道具              |
| 文本语言 | 简体中文                                                                           | 简体中文                    |
| 开发难度 | 高（鉴权是最大障碍）                                                                     | 低                       |
| 参考文档 | [POE2国服支持可行性评估](file:///e:/python_space/MyPoeAssist/ref_docs/POE2国服支持可行性评估.md) | 本文档                     |

**结论**：如果需求是「查看自己/他人的角色装备详情」，角色分享 API 是远优于交易 API 的方案——开发简单、无需登录。

***

## 八、参考来源

| 来源                                                                                            | 说明                                      |
| --------------------------------------------------------------------------------------------- | --------------------------------------- |
| [cn-poe-community/poexport-extension](https://github.com/cn-poe-community/poexport-extension) | 源码 `utils/poe2_wg_api.ts` 包含全部 API 接口定义 |
| [NGA 帖子：国服p2的角色怎么导出到pob](https://bbs.nga.cn/read.php?tid=46952197)                            | 介绍了 WeGame 分享链接的获取方式                    |
| [pobzh.cn 在线 POB 工具](https://pobzh.cn)                                                        | 使用相同 API 实现国服角色导入                       |
| [易刷](https://www.esshuа.com)                                                                  | 内置 POB 导出功能，基于相同 API                    |

***

## 九、附录：实测可用的公开分享链接

调研期间使用的公开分享链接（来自 NGA 帖子）：

```
https://www.wegame.com.cn/helper/poe2/#/share/HGcIsXcQZj_KJuoSXIDtUfPJuYTuBdG5tZV9QUIL9p0FBhj-rWclK_42q480DDRC
```

分享码：`HGcIsXcQZj_KJuoSXIDtUfPJuYTuBdG5tZV9QUIL9p0FBhj-rWclK_42q480DDRC`

对应角色：浅滩冰射突突突（亚马逊 Lv.96，奥杜尔秘符赛季）

***

## 十、深入探索：能否获取背包/仓库数据？

### 10.1 WeGame Profile API 完整端点探测

通过分析 WeGame helper 前端 JS bundle（`player-CLrwMewX.js`），发现了 **完整的 Profile 服务端点列表**（共 14 个方法）：

| 端点                       | 路径                                                            | 用途        | 分享码可调 | 实测结果       |
| ------------------------ | ------------------------------------------------------------- | --------- | :---: | ---------- |
| GetRoleInfo              | `/api/v1/wegame.pallas.poe2.Profile/GetRoleInfo`              | 角色基本信息    |   ✅   | 成功         |
| GetEquipments            | `/api/v1/wegame.pallas.poe2.Profile/GetEquipments`            | 装备栏       |   ✅   | 成功         |
| GetTalentTree            | `/api/v1/wegame.pallas.poe2.Profile/GetTalentTree`            | 天赋树       |   ✅   | 成功         |
| GetJewels                | `/api/v1/wegame.pallas.poe2.Profile/GetJewels`                | 珠宝        |   ✅   | 成功         |
| GetSkills                | `/api/v1/wegame.pallas.poe2.Profile/GetSkills`                | 技能        |   ✅   | 成功         |
| GetRoleProfile           | `/api/v1/wegame.pallas.poe2.Profile/GetRoleProfile`           | 天赋数量+技能   |   ✅   | 成功         |
| GetRoleKeyData           | `/api/v1/wegame.pallas.poe2.Profile/GetRoleKeyData`           | 角色关键数据    |   ✅   | 成功         |
| GetRolePlaySummary       | `/api/v1/wegame.pallas.poe2.Profile/GetRolePlaySummary`       | 关卡/Boss统计 |   ✅   | 成功         |
| GetSeasonCurrencySummary | `/api/v1/wegame.pallas.poe2.Profile/GetSeasonCurrencySummary` | 赛季通货统计    |   ✅   | 成功         |
| GetDimensionEvaluation   | `/api/v1/wegame.pallas.poe2.Profile/GetDimensionEvaluation`   | 维度评分      |   ✅   | 成功         |
| GetRoleSummary           | `/api/v1/wegame.pallas.poe2.Profile/GetRoleSummary`           | 角色摘要      |   ✅   | 成功         |
| GetRoleList              | `/api/v1/wegame.pallas.poe2.Profile/GetRoleList`              | 角色列表      |   ❌   | 需登录 openid |
| GetBossKilledRecord      | `/api/v1/wegame.pallas.poe2.Profile/GetBossKilledRecord`      | Boss击杀记录  |   ❌   | 需额外参数      |
| GetRolePlayData          | `/api/v1/wegame.pallas.poe2.Profile/GetRolePlayData`          | 游戏数据      |   ❌   | 需登录        |

**结论：WeGame Profile 服务的全部 14 个方法都是角色展示型数据，没有任何背包/仓库/库存相关接口。**

### 10.2 暴力探测：猜测可能的隐藏端点

对 `wegame.pallas.poe2.Profile` 服务尝试了 38 个候选方法名（GetInventory、GetStash、GetBackpack、GetWarehouse、GetItems、GetChest、GetVault、GetBag 等），全部返回错误：

- **error\_code 8000114**：「rpc name invalid, current service: wghttp.pallas.poe2.Profile」—— 方法未注册
- **error\_code 8000119**：「illegal body format」—— 请求体格式错误

对 15 个候选服务名（Stash、Inventory、Trade、Market、Character、Account、Item、Assets 等）× 5 个方法名进行交叉探测，75 个组合全部返回 `error_code 8000102`（服务不存在/无权限）。

**结论：WeGame 不存在任何隐藏的背包/仓库 API 端点。**

### 10.3 国服 POE 官方 API（poe.game.qq.com）

GGG 官方 API 文档（poedb.tw/poe-api）显示 `poe.game.qq.com` 作为 Tencent China Site 同样支持以下端点：

| 端点                                      | 用途            | 实测状态    |
| --------------------------------------- | ------------- | ------- |
| `GET /character-window/get-items`       | 获取角色装备+**背包** | 401 需认证 |
| `GET /character-window/get-characters`  | 获取角色列表        | 401 需认证 |
| `GET /character-window/get-stash-items` | 获取仓库标签页物品     | 401 需认证 |
| `GET /character-window/get-passives`    | 获取天赋          | 401 需认证 |

**所有端点均返回 401 未经授权**，需要用户登录 poe.game.qq.com 后获取 `POESESSID` Cookie 才能访问。

### 10.4 POE2 官方 OAuth API（api.pathofexile.com）

GGG 官方 API 文档中，POE2 相关的端点状态：

| 端点                           |   POE2 支持   | 说明                                      |
| ---------------------------- | :---------: | --------------------------------------- |
| `GET /character/poe2/<name>` |      ✅      | 返回 equipment + **inventory** + passives |
| `GET /stash/<league>`        | ❌ PoE1 only | POE2 无仓库 API                            |
| `GET /public-stash-tabs`     | ❌ PoE1 only | POE2 无公开仓库流                             |
| `GET /guild/stash/<league>`  | ❌ PoE1 only | POE2 无公会仓库 API                          |

**关键发现**：POE2 官方 API 的 `GET /character/poe2/<name>` 返回数据中包含 `inventory`（背包），但：

1. 需要 OAuth Token（注册 GGG OAuth 应用）
2. 仅适用于国际服账号
3. 国服玩家无法使用（国服账号与国际服不互通）

### 10.5 各方案可行性总结

| 方案                       |   能否获取背包   | 鉴权要求             |  国服可用 |   开发难度   |
| ------------------------ | :--------: | ---------------- | :---: | :------: |
| WeGame 分享 API            |   ❌ 仅装备栏   | 无需鉴权             |   ✅   |   🟢 低   |
| 国服 character-window API  | ✅ 装备+背包+仓库 | POESESSID Cookie |   ✅   |   🔴 高   |
| POE2 官方 OAuth API        |   ✅ 装备+背包  | OAuth Token      | ❌ 国际服 |   🟡 中   |
| WeGame 开发者 Container API |    理论上可以   | 游戏开发者权限          |   ✅   |   🔴 极高  |
| 游戏内 Ctrl+C 复制            |   ✅ 单件物品   | 无                |   ✅   | 🟢 低（手动） |

### 10.6 结论

**通过公开的 WeGame 分享链接，无法获取背包数据。** WeGame 的 Profile 服务只提供角色展示型数据（装备栏、天赋、技能、统计），设计目的是 BD 分享，不包含背包/仓库内容。

获取背包数据的唯一可行途径是 **国服 character-window API**（`poe.game.qq.com/character-window/get-items`），但这需要解决用户登录认证问题（获取 POESESSID Cookie），与 [POE2国服支持可行性评估](file:///e:/python_space/MyPoeAssist/ref_docs/POE2国服支持可行性评估.md) 中分析的「鉴权障碍」一致。

如果需求仅为「实时查询已装备的道具详情」，WeGame 分享 API 已完全满足，且开发成本极低。
