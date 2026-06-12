# Sidekick POE2 查价功能实现梳理

> 项目地址：https://github.com/Sidekick-Poe/Sidekick  
> 整体技术栈：C# (.NET 8) + Blazor UI + WPF (WebView2)

---

## 一、整体架构概览

查价流程分为 **5 个阶段**：

```
用户按下 Ctrl+D (快捷键)
    ↓
[1] 触发查价
    ├─ 模拟 Ctrl+C 从游戏窗口复制道具文本
    ├─ Base64 编码 → 导航到 /item/{encodedText}
    ↓
[2] 道具解析 (ItemParser)
    ├─ 提取稀有度 → 匹配道具定义 → 提取属性 → 提取词缀
    └─ 输出结构化 Item 对象
    ↓
[3] 价格数据获取 (三条链路并行)
    ├─ GGG Trade API → 实时挂牌列表 (官方交易API)
    ├─ poe2scout.com → 24h价格走势
    └─ poe.ninja → 市场价统计
    ↓
[4] 搜索+筛选 (TradeService)
    ├─ 构造 Query JSON → POST 搜索 → 获取结果ID列表
    ├─ GET 拉取挂牌详情 → 渲染列表
    └─ 支持用户交互调整筛选器后重新搜索
    ↓
[5] UI 渲染 (Blazor 组件)
    ├─ 左侧：可交互筛选器面板
    ├─ 中间：实时挂牌列表 (10条/页)
    └─ 底部：估价面板 (poe2scout + poe.ninja)
```

---

## 二、触发查价

### PriceCheckItemKeybindHandler

**文件：** [src/Sidekick.Modules.Items/Keybinds/PriceCheckItemKeybindHandler.cs](file:///e:/python_space/Sidekick/src/Sidekick.Modules.Items/Keybinds/PriceCheckItemKeybindHandler.cs)

- **默认快捷键：** `Ctrl + D`
- **触发条件：** 游戏进程必须在前台（`processProvider.IsPathOfExileInFocus`）
- **执行流程：**
  1. 调用 `clipboardProvider.Copy()` → 模拟 `Ctrl+C`，从游戏复制道具完整文本
  2. 将文本 `Base64Url` 编码
  3. 打开 Sidekick 覆盖层窗口，导航到 `/item/{encodedText}`

```csharp
public override async Task Execute(string keybind)
{
    var text = await clipboardProvider.Copy();    // 模拟 Ctrl+C
    if (text == null) { await keyboard.PressKey(keybind); return; }
    viewLocator.Open(SidekickViewType.Overlay, $"/item/{text.EncodeBase64Url()}");
}
```

---

## 三、道具解析

### 3.1 入口：ItemOverlay.razor

**文件：** [src/Sidekick.Modules.Items/ItemOverlay.razor](file:///e:/python_space/Sidekick/src/Sidekick.Modules.Items/ItemOverlay.razor)

导航到页面后，Base64 解码道具文本 → 调用 `ItemParser.ParseItem()`：

```csharp
protected override async Task OnParametersSetAsync()
{
    TradeService.Init();
    var itemText = ItemText.DecodeBase64Url();
    Item = ItemParser.ParseItem(itemText);   // 核心解析
}
```

### 3.2 ItemParser 解析链

**文件：** [src/Sidekick.Apis.Poe.Trade/Parser/ItemParser.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Parser/ItemParser.cs)

解析器按固定顺序处理游戏文本，各步骤有严格的依赖关系：

```csharp
public Item ParseItem(string? text)
{
    text = NormalizeText(text);             // 文本预处理
    var item = new Item(Game, language, text);

    propertyParser.GetDefinition<RarityProperty>().Parse(item);  // 1.稀有度(必须先解析)
    itemDefinitionParser.Parse(item);                            // 2.道具定义匹配
    propertyParser.Parse(item);                                  // 3.属性解析
    statParser.Parse(item);                                      // 4.词缀解析
    propertyParser.ParseAfterStats(item);                        // 5.后处理(依赖词缀结果)
    pseudoParser.Parse(item);                                    // 6.伪词缀计算

    return item;
}
```

#### 文本预处理步骤

| 步骤 | 功能 |
|------|------|
| 统一换行符 | 将所有换行符标准化为 `\n` |
| 移除不可用行 | 去除 "Unusable" 标记行 |
| 追加类别标记 | 识别 `{Implicit}`, `{Crafted}`, `{Fractured}` 等类别标记并追加后缀 |
| 合并进阶数值 | 对 `10(5-15)` 格式的数值进行去重合并，累加数值 |
| 移除进阶元数据 | 删除 `{...}` 标记行 |

### 3.3 POE2 专属属性解析器

Sidekick 通过在 `PropertyParser` 中按游戏类型注册解析器，区分 POE1/POE2 的差异化处理。以下是 POE2 专属或 POE2 有特殊处理的属性：

#### 精魂 (Spirit)

**文件：** [src/Sidekick.Apis.Poe.Trade/Parser/Properties/Definitions/SpiritProperty.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Parser/Properties/Definitions/SpiritProperty.cs)

- **仅在 POE2 中有效**：`if (game == GameType.PathOfExile1) return;`
- 仅对武器和装备类道具进行解析
- 提取精魂数值，标记是否为增强属性（Augmented）
- 生成 `SpiritFilter`，对应 API 请求中的 `equipment_filters.spirit`

```csharp
public override void Parse(Item item)
{
    if (!item.ItemClass.IsWeapon() && !item.ItemClass.IsEquipment()) return;
    if (game == GameType.PathOfExile1) return;        // POE1跳过

    item.Properties.Spirit = GetInt(Pattern, item.Text);
    // ...
}
```

#### 碑牌掉落概率 (Waystone Drop Chance)

**文件：** [src/Sidekick.Apis.Poe.Trade/Parser/Properties/Definitions/WaystoneDropChanceProperty.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Parser/Properties/Definitions/WaystoneDropChanceProperty.cs)

- **仅在 POE2 中有效**：`if (game != GameType.PathOfExile2) return;`
- 对应 API 请求中的 `map_filters.waystone_drop_chance`

#### 武器伤害 (Weapon Damage)

**文件：** [src/Sidekick.Apis.Poe.Trade/Parser/Properties/Definitions/WeaponDamageProperty.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Parser/Properties/Definitions/WeaponDamageProperty.cs)

- `ParseAfterStats` 步骤中，POE2 跳过元素伤害合并逻辑

#### 插槽 (Socket)

**文件：** [src/Sidekick.Apis.Poe.Trade/Parser/Properties/Definitions/SocketProperty.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Parser/Properties/Definitions/SocketProperty.cs)

- POE2 中插槽数直接取 `Sockets.Count`（POE1 取最大链接组数）

#### 物品等级 (ilvl)

**文件：** [src/Sidekick.Apis.Poe.Trade/Trade/Requests/Filters/TypeFilters.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Trade/Requests/Filters/TypeFilters.cs)

- POE2 中物品等级筛选在 `type_filters` 下（POE1 在 `misc_filters`）

```csharp
/// <remarks>
/// POE2 的物品等级筛选在 type_filters 下，而不是 misc_filters。
/// </remarks>
[JsonPropertyName("ilvl")]
public StatFilterValue? ItemLevel { get; set; }
```

---

## 四、价格数据源

三个数据源**并行**获取，互不依赖。

### 4.1 数据源 A：GGG Trade API（实时挂牌）

这是查价功能的核心——在玩家决定道具价格时，最直观的参考是「当前市场上类似道具卖多少钱」。

GGF 提供的是**官方交易 REST API**，Sidekick 通过它与 `pathofexile.com/trade2` 交互。

#### API 基础 URL

| 语言 | 交易站 URL | API URL |
|------|-----------|---------|
| 英文 | `https://www.pathofexile.com/trade2/` | `https://www.pathofexile.com/api/trade2/` |
| 德文 | `https://de.pathofexile.com/trade2/` | `https://de.pathofexile.com/api/trade2/` |
| 法文 | `https://fr.pathofexile.com/trade2/` | `https://fr.pathofexile.com/api/trade2/` |
| 日文 | `https://jp.pathofexile.com/trade2/` | `https://jp.pathofexile.com/api/trade2/` |
| 繁中 | `http://www.pathofexile.tw/trade2/` | `http://www.pathofexile.tw/api/trade2/` |
| 等其他语言... | 各地子域名 | 对应子域名 + `/api/trade2/` |

**实现代码：** [src/Sidekick.Data/Languages/IGameLanguage.cs](file:///e:/python_space/Sidekick/src/Sidekick.Data/Languages/IGameLanguage.cs)

```csharp
public string GetTradeApiBaseUrl(GameType game) => game switch
{
    GameType.PathOfExile2 => Poe2TradeApiBaseUrl,   // POE2 使用 /trade2/
    _ => PoeTradeBaseUrl,                            // POE1 使用 /trade/
};
```

#### 两步 API 调用

**Step 1：POST 搜索 → 获取结果 ID 列表**

```http
POST https://www.pathofexile.com/api/trade2/search/{联赛名}
Content-Type: application/json

{
  "query": {
    "status": { "option": "online" },
    "type": "Ring",
    "name": "环箍",
    "stats": [],
    "filters": {
      "type_filters": { "filters": { "category": { "option": "ring" }, "rarity": { "option": "unique" } } },
      "trade_filters": { "filters": { "price": { "option": "chaos" } } }
    }
  },
  "sort": { "price": "asc" }
}
```

**响应：**
```json
{
  "id": "8b5c3a2d1f...",   // 查询ID
  "total": 247,              // 总匹配数
  "result": ["id1", "id2", "id3", ...]  // 默认返回10个ID
}
```

**Step 2：GET 批量获取挂牌详情**

```http
GET https://www.pathofexile.com/api/trade2/fetch/id1,id2,id3?query=8b5c3a2d1f...
```

**响应：**
```json
{
  "result": [
    {
      "id": "id1",
      "listing": {
        "indexed": "2026-06-12T10:30:00Z",
        "account": { "name": "玩家名" },
        "price": { "amount": 50, "currency": "chaos", "type": "exact" }
      },
      "item": {
        "name": "环箍",
        "typeLine": "珊瑚戒指",
        "identified": true,
        "ilvl": 85,
        "frameType": 3,           // 3=Unique
        "icon": "https://...",
        "explicitMods": ["+50 生命", "+40% 火焰抗性"],
        "requirements": [...],
        "properties": [...],
        "sockets": [...],
        "influences": {}
      }
    }
  ]
}
```

#### 核心服务类

**文件：** [src/Sidekick.Apis.Poe.Trade/Trade/ItemTradeService.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Trade/ItemTradeService.cs)

```csharp
public class ItemTradeService : IItemTradeService
{
    // Step 1: 搜索
    public async Task<TradeSearchResult<string>> Search(Item item, List<TradeFilter>? filters)
    {
        var useEnglish = await settingsService.GetBool(UseInvariantTradeResults);
        var language = useEnglish ? currentGameLanguage.InvariantLanguage : currentGameLanguage.Language;

        var query = GetQueryFromDefinition(useEnglish ? item.Invariant : item.Definition);
        foreach (var filter in filters ?? [])
            filter.PrepareTradeRequest(query, item);   // 应用所有筛选器

        var league = await settingsService.GetLeague();
        var uri = new Uri($"{language.GetTradeApiBaseUrl(item.Game)}search/{league}");

        var json = JsonSerializer.Serialize(new QueryRequest() { Query = query });
        var response = await httpClient.PostAsync(uri, new StringContent(json, Encoding.UTF8, "application/json"));

        return await JsonSerializer.DeserializeAsync<TradeSearchResult<string>>(...);
    }

    // Step 2: 获取详情
    public async Task<List<TradeResult>> GetResults(GameType game, string queryId, List<string> ids)
    {
        var language = ...;
        var response = await httpClient.GetAsync(
            language.GetTradeApiBaseUrl(game) + "fetch/" + string.Join(",", ids) + "?query=" + queryId);

        var result = await JsonSerializer.DeserializeAsync<FetchResult<TradeResult?>>(...);
        return result.Result.Where(x => x != null).ToList()!;
    }
}
```

#### 查询构建：Query 模型

**文件：** [src/Sidekick.Apis.Poe.Trade/Trade/Requests/Query.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Trade/Requests/Query.cs)

```csharp
public class Query
{
    public Status Status { get; set; } = new();         // 在线状态
    public string? Name { get; set; }                    // 暗金道具名称
    public object? Type { get; set; }                    // 道具类型
    public string? Term { get; set; }                    // 关键词搜索
    public List<StatFilterGroup> Stats { get; set; } = []; // 词缀筛选
    public SearchFilters Filters { get; set; } = new();    // 属性筛选
}
```

#### 筛选器分组

**文件：** [src/Sidekick.Apis.Poe.Trade/Trade/Requests/Filters/SearchFilters.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Trade/Requests/Filters/SearchFilters.cs)

| JSON Key | C# 类型 | 用途 |
|----------|---------|------|
| `type_filters` | `TypeFilterGroup` | 物品分类、稀有度、ilvl（POE2专用） |
| `weapon_filters` | `WeaponFilterGroup` | DPS、暴击率、攻速 |
| `armour_filters` | `ArmourFilterGroup` | 护甲、闪避、护盾 |
| `equipment_filters` | `EquipmentFilterGroup` | POE2 特有（精魂等） |
| `socket_filters` | `SocketFilterGroup` | 插槽数、链接数 |
| `req_filters` | `RequirementsFilterGroup` | 等级、属性需求 |
| `misc_filters` | `MiscFilterGroup` | 品质、腐化、分裂 |
| `map_filters` | `MapFilterGroup` | 地图阶位、碑牌概率 |
| `trade_filters` | `TradeFilterGroup` | 价格类型、玩家状态 |
| `heist_filters` | `HeistFilterGroup` | 盗城契约相关 |
| `equipment_filters` | `EquipmentFilterGroup` | POE2装备属性 |

#### 请求管道：限流 + Cloudflare 处理

**文件：** [src/Sidekick.Apis.Poe.Trade/Clients/TradeApiHandler.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Clients/TradeApiHandler.cs)

所有 Trade API 请求都经过 `TradeApiHandler`（DelegatingHandler 管道中间件），处理：

| 问题 | 处理方式 |
|------|----------|
| **Cloudflare 保护** | 检测重定向到 Cloudflare → 弹 WebView2 让用户完成人机验证 → 带上新 Cookie 重试 |
| **国服检测** | 检测到中文语言设置时报错中断（国服需要 OAuth 认证） |
| **速率限制 (429)** | 令牌桶限流器自动控制请求速率 |
| **查询太复杂 (400)** | 捕获 `"Query is too complex."` 错误，给用户友好提示 |
| **未授权 (401)** | 明确提示不支持的认证方式 |

```csharp
protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
{
    // 1. Cloudflare Cookie 注入
    await cloudflareService.InitializeHttpRequest(TradeApiClient.ClientName, request, ct);

    // 2. 速率限制：获取令牌
    var limitHandler = limitProvider.Get(TradeApiClient.ClientName);
    using var lease = await limitHandler.Lease(cancellationToken: ct);

    // 3. 发送请求
    var response = await base.SendAsync(request, ct);

    // 4. 异常处理
    response = await HandleRedirect(request, response, ct);    // 重定向/Cloudflare
    response = await HandleForbidden(request, response, ct);    // 403 CF挑战
    await HandleTooManyRequests(response, ct);                  // 429 限流
    HandleUnauthorized(response);                               // 401 未授权
    await HandleBadRequest(response, ct);                       // 400 查询太复杂

    // 5. 更新限流状态
    limitHandler.HandleResponse(response, ct);
    return response;
}
```

#### 数据回退机制

**文件：** [src/Sidekick.Apis.Poe.Trade/Clients/TradeApiClient.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Clients/TradeApiClient.cs)

`TradeApiClient.FetchData()` 在调用 GGG 的 `/data/` 静态数据端点（如物品过滤器、词缀列表）时，如果 API 不可用，会自动读取本地 JSON 文件作为 fallback：

```csharp
// 尝试从 API 获取
var response = await httpClient.GetAsync(language.GetTradeApiBaseUrl(game) + "data/" + path);
// ...若失败，读取本地缓存
var dataFilePath = Path.Combine(AppContext.BaseDirectory,
    "wwwroot/data/" + GetDataFileName(game, language, path));
```

---

### 4.2 数据源 B：poe2scout.com（价格走势）

这是 POE2 查价的**核心价格趋势数据源**，提供 24 小时价格历史。

#### API 集成

**文件：** [src/Sidekick.Apis.Poe2Scout/Clients/ScoutClient.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe2Scout/Clients/ScoutClient.cs)

```csharp
private static readonly Uri apiBaseUrl = new("https://poe2scout.com/api/");
```

所有请求经过统一的 `Fetch<TResponse>()` 方法，处理：
- 联赛参数注入
- 路径路由（items/categories → items → items/{id}/history → currencyExchange/PairHistory）
- JSON 反序列化
- 错误日志 + null 安全返回

**API 端点映射：**

| Sidekick 方法 | API 路径 | 用途 |
|--------------|---------|------|
| `Fetch("items/categories")` | `{game}/Items/Categories` | 获取物品分类列表 |
| `Fetch("items")` | `{game}/Leagues/{league}/Items` | 获取所有物品列表 |
| `Fetch("items/{id}/history")` | `{game}/Leagues/{league}/Items/{id}/History` | 获取单个物品价格历史 |
| `Fetch("currencyExchange/PairHistory")` | `{game}/Leagues/{league}/Currencies/Pairs/{id1}/{id2}/History` | 获取通货汇率历史 |

#### 物品匹配流程

**文件：** [src/Sidekick.Apis.Poe2Scout/Items/ScoutItemProvider.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe2Scout/Items/ScoutItemProvider.cs)

```csharp
public async Task<ScoutItem?> GetItem(string text)
{
    // 仅 POE2 有效
    if (game == GameType.PathOfExile1) return null;

    var items = await GetOrFetchItems();  // 优先读缓存，否则请求API
    // 三重匹配策略：
    var item = items.FirstOrDefault(x => x.Name == text);
    item ??= items.FirstOrDefault(x => x.Type == text);
    item ??= items.FirstOrDefault(x => x.Text == text);
    return item;
}
```

匹配顺序：`Name → Type → Text`

**缓存机制：** `ICacheProvider.GetOrSet()`，缓存 key 为 `"poe2scout.{game}.items"`，仅当结果不为空时才写入。

#### 价格历史

**文件：** [src/Sidekick.Apis.Poe2Scout/History/ScoutHistoryProvider.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe2Scout/History/ScoutHistoryProvider.cs)

提供两种历史查询：

1. **物品价格历史：** 获取以 Exalted Orb 计价的 24 小时价格日志
2. **通货汇率历史：** 获取与 Exalted/Chaos/Divine 三种参考货币的汇率对历史

```csharp
public async Task<ScoutHistory?> GetItemHistory(int itemId)
{
    return new ScoutHistory()
    {
        Exalted = await GetItemLogs(itemId, "exalted"),
    };
}

public async Task<ScoutHistory?> GetCurrencyHistory(int itemId)
{
    return new ScoutHistory()
    {
        Exalted = await GetCurrencyLogs(itemId, exaltedOrbId),
        Chaos = await GetCurrencyLogs(itemId, chaosOrbId),
        Divine = await GetCurrencyLogs(itemId, divineOrbId),
    };
}
```

**数据结构：**
```csharp
// ScoutHistory.cs
public class ScoutHistory
{
    public List<ScoutHistoryLog>? Exalted { get; init; }  // 以E计价的价格日志
    public List<ScoutHistoryLog>? Chaos { get; init; }    // 以C计价的价格日志
    public List<ScoutHistoryLog>? Divine { get; init; }   // 以D计价的价格日志
}

public class ScoutHistoryLog
{
    public decimal Price { get; set; }          // 价格
    public int Quantity { get; set; }           // 成交量
    public DateTimeOffset Time { get; set; }    // 时间点
}
```

#### 物品分类

**文件：** [src/Sidekick.Apis.Poe2Scout/Categories/ScoutCategoryProvider.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe2Scout/Categories/ScoutCategoryProvider.cs)

用于区分通货物品和暗金物品，影响 ninja 数据源的选择。

---

### 4.3 数据源 C：poe.ninja（市场统计）

提供通货汇率、暗金价格等统计数据。

#### 存储架构

POE2 的 ninja 数据文件位于：`data/poe2/raw/ninja/`

```
data/poe2/raw/ninja/
├── Currency.json              # 通货价格
├── UncutGems.json             # 未切割宝石
├── Essences.json              # 精髓
├── Breach.json                # 裂隙
├── Fragments.json             # 碎片
├── Expedition.json            # 探险/日志
├── Ultimatum.json             # 试炼/ inscribed ultimatums
├── Delirium.json              #  delirium
├── Runes.json                 # 符文
├── Abyss.json                 # 深渊
├── Ritual.json                # 祭祀
├── Talismans.json             # 护身符
└── LineageSupportGems.json    #  lineage support gems
```

#### 两种查询模式

**文件：** [src/Sidekick.Apis.PoeNinja/Exchange/NinjaExchangeProvider.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.PoeNinja/Exchange/NinjaExchangeProvider.cs)  
**文件：** [src/Sidekick.Apis.PoeNinja/Stash/NinjaStashProvider.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.PoeNinja/Stash/NinjaStashProvider.cs)

1. **Exchange 模式：** 获取通货兑换汇率（如 Exalted → Chaos），带 Sparkline 走势
2. **Stash 模式：** 获取具体道具的 Stash 价格快照

Sidekick 先在道具定义中判断，如果 `NinjaItems` 中有 `Exchange` 属性则走 Exchange 模式，有 `Stash` 则走 Stash 模式：

```csharp
// 来自 WealthProvider.cs（逻辑类似估价组件）
if (invariantDefinition.NinjaItems?.Any(x => x.Exchange != null) ?? false)
{
    // 通货类：用 Exchange API
    var info = await ninjaExchangeProvider.GetInfo(invariantDefinition);
    price = info?.Trades.FirstOrDefault(x => x.ExchangeId == "chaos")?.Value ?? 0;
}
else
{
    // 道具类：用 Stash API
    var stashes = await ninjaStashProvider.GetInfo(invariantDefinition, item);
    price = stashes.FirstOrDefault()?.ChaosValue ?? 0;
}
```

---

## 五、TradeService（业务编排）

**文件：** [src/Sidekick.Modules.Items/Trade/TradeService.cs](file:///e:/python_space/Sidekick/src/Sidekick.Modules.Items/Trade/TradeService.cs)

`TradeService` 是查价业务的**编排层**，连接 UI 与 API：

```csharp
public class TradeService(IItemTradeService itemTradeService)
{
    public bool IsLoading { get; private set; }
    public TradeSearchResult<string>? ItemTradeResult { get; private set; }  // 搜索结果
    public List<TradeResult> TradeItems { get; private set; } = [];         // 挂牌详情列表
    public event Action? Changed;                                            // UI 变更通知

    public void Init() { /* 初始化 */ }
    public void Clear() { /* 清空结果 */ }

    public async Task SearchItems(Item item, List<TradeFilter> filters)
    {
        IsLoading = true;
        Clear();
        ItemTradeResult = await itemTradeService.Search(item, filters);  // Step 1: 搜索
        IsLoading = false;
        await LoadMoreItems(item.Game);                                  // Step 2: 拉取详情
        Changed?.Invoke();                                               // 通知UI更新
    }

    public async Task LoadMoreItems(GameType game)
    {
        // 每次取10条结果
        var ids = ItemTradeResult.Result.Skip(TradeItems.Count).Take(10).ToList();
        var result = await itemTradeService.GetResults(game, ItemTradeResult.Id, ids);
        TradeItems.AddRange(result);   // 追加到现有列表
        Changed?.Invoke();
    }
}
```

**分页策略：** 每次 `LoadMoreItems()` 取 10 条，滚动加载。GGG API 的搜索结果列表默认包含 10 个 ID（可通过参数调整），但 Sidekick 保持默认 10 条/次。

---

## 六、UI 展示

### 6.1 主页面

**文件：** [src/Sidekick.Modules.Items/ItemOverlay.razor](file:///e:/python_space/Sidekick/src/Sidekick.Modules.Items/ItemOverlay.razor)

```
┌──────────────────────────────────────────────────────┐
│  顶部栏：设置按钮 | 关闭按钮                          │
├──────────┬───────────────────────────────────────────┤
│ 左侧面板  │  中间内容区                               │
│ (筛选器)  │  Tab: 交易 | 估价 | 资料库 | 交换 | ...  │
│          │  ┌───────────────────────────────────────┐│
│ 类别筛选   │  │  挂牌列表 (ItemComponent.razor)        ││
│ 稀有度筛选 │  │  ┌─────┬──────────────────────────┐ ││
│ 价格筛选   │  │  │道具图 │ 名称 · 稀有度 · 词缀    │ ││
│ 词缀勾选   │  │  │片/插槽 │ 价格 · 卖家 · 时间    │ ││
│          │  │  └─────┴──────────────────────────┘ ││
│          │  │  ... 更多挂牌 ...                     ││
│          │  │  [加载更多]                           ││
│          │  └───────────────────────────────────────┘│
│          │                                           │
│          │  底部估价面板 (ValuationResult.razor)      │
│          │  ┌───────────────────────────────────────┐│
│          │  │  PoeNinjaResults (poe.ninja市场价)    ││
│          │  │  Poe2ScoutResult (24h价格走势)         ││
│          │  └───────────────────────────────────────┘│
├──────────┴───────────────────────────────────────────┤
│  底部状态栏：API状态 · 速率限制信息                   │
└──────────────────────────────────────────────────────┘
```

### 6.2 估价面板集成

**文件：** [src/Sidekick.Modules.Items/Valuation/ValuationResult.razor](file:///e:/python_space/Sidekick/src/Sidekick.Modules.Items/Valuation/ValuationResult.razor)

```razor
<div class="flex flex-col gap-4">
    <PoeNinjaResults/>        <!-- poe.ninja 市场均价 -->
    <Poe2ScoutResult/>        <!-- poe2scout.com 价格走势 -->
    <PoePricesResult/>        <!-- poeprices.info 估价(仅POE1) -->
</div>
```

> **注意：** `PoePricesResult`（基于机器学习的估价）仅支持 POE1，POE2 目前没有类似的服务。

### 6.3 Poe2ScoutResult 组件

**文件：** [src/Sidekick.Modules.Items/Poe2Scout/Poe2ScoutResult.razor](file:///e:/python_space/Sidekick/src/Sidekick.Modules.Items/Poe2Scout/Poe2ScoutResult.razor)

- **仅 POE2 显示：** `if (Item.Game == GameType.PathOfExile1) return;`
- 显示 poe2scout.com 的标志 + 三种货币（Exalted/Chaos/Divine）的 24 小时价格走势图表
- 底部链接到 poe2scout.com 网站查看完整数据

```razor
@if (ScoutHistory == null)
{
    <AlertInfo Flat="true">@Resources["NoCurrencyExchangeData"]</AlertInfo>
}
else
{
    <Poe2ScoutPanel Currency="exalted" Logs="@ScoutHistory.Exalted" />
    <Poe2ScoutPanel Currency="chaos" Logs="@ScoutHistory.Chaos" />
    <Poe2ScoutPanel Currency="divine" Logs="@ScoutHistory.Divine" />
    <Poe2ScoutWebsite History="ScoutHistory" Item="ScoutItem" />
}
```

### 6.4 ItemComponent 挂牌组件

**文件：** [src/Sidekick.Modules.Items/Trade/Items/ItemComponent.razor](file:///e:/python_space/Sidekick/src/Sidekick.Modules.Items/Trade/Items/ItemComponent.razor)

每个挂牌项渲染：
- **道具头部：** 名称、类型、稀有度颜色、影响标记
- **属性区：** 品质、精魂、护甲/闪避/护盾、武器伤害、插槽
- **词缀区：** 隐式、显式、工艺、腐化等
- **价格区：** 金额 + 通货图标（通过 `PriceDisplay` 组件渲染）
- **卖家信息：** 角色名 + 挂牌时间

---

## 七、POE1 vs POE2 差异总结

| 维度 | POE1 | POE2 |
|------|------|------|
| **API 基础路径** | `/api/trade/` | `/api/trade2/` |
| **交易站 URL** | `.../trade/` | `.../trade2/` |
| **精魂 (Spirit)** | 不支持 | 新增属性，`equipment_filters.spirit` |
| **碑牌掉落** | 不支持 | 新增属性，`map_filters.waystone_drop_chance` |
| **物品等级** | `misc_filters` | `type_filters.ilvl` |
| **插槽计数** | 最大链接组数 | 总插槽数 |
| **武器伤害** | 需解析元素伤害合并（`ParseAfterStats`） | 跳过合并逻辑 |
| **价格走势源** | poe.ninja + poeprices.info | poe2scout.com + poe.ninja |
| **机器学习估价** | poeprices.info（有） | 无 |
| **装备过滤器** | `weapon_filters` + `armour_filters` | 新增 `equipment_filters` |
| **数据文件** | `data/poe1/` | `data/poe2/` |
| **联赛** | `pathofexile.com/trade` 标准联赛 | `/trade2/` 中的 POE2 联赛 |

---

## 八、关键文件索引

| 模块 | 文件 | 说明 |
|------|------|------|
| 快捷键触发 | [PriceCheckItemKeybindHandler.cs](file:///e:/python_space/Sidekick/src/Sidekick.Modules.Items/Keybinds/PriceCheckItemKeybindHandler.cs) | Ctrl+D 触发查价 |
| 道具解析 | [ItemParser.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Parser/ItemParser.cs) | 文本→结构化对象 |
| 精魂属性 | [SpiritProperty.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Parser/Properties/Definitions/SpiritProperty.cs) | POE2 专属精魂解析 |
| 碑牌概率 | [WaystoneDropChanceProperty.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Parser/Properties/Definitions/WaystoneDropChanceProperty.cs) | POE2 专属掉落率解析 |
| GGG API 搜索 | [ItemTradeService.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Trade/ItemTradeService.cs) | Trade API 搜索+获取 |
| API 扩展属性 | [IGameLanguage.cs](file:///e:/python_space/Sidekick/src/Sidekick.Data/Languages/IGameLanguage.cs) | URL 路由（trade vs trade2） |
| API 管道 | [TradeApiHandler.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Clients/TradeApiHandler.cs) | 限流+Cloudflare+错误处理 |
| API 静态数据 | [TradeApiClient.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Clients/TradeApiClient.cs) | 静态数据 + fallback |
| 筛选器 | [TradeFilterProvider.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Filters/TradeFilterProvider.cs) | 筛选器生成 |
| 筛选器分组 | [SearchFilters.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Trade/Requests/Filters/SearchFilters.cs) | 筛选器模型定义 |
| 筛选器类型 | [TypeFilters.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Trade/Requests/Filters/TypeFilters.cs) | 含 ilvl POE2 注释 |
| 业务编排 | [TradeService.cs](file:///e:/python_space/Sidekick/src/Sidekick.Modules.Items/Trade/TradeService.cs) | 搜索+分页+状态管理 |
| 主页面 | [ItemOverlay.razor](file:///e:/python_space/Sidekick/src/Sidekick.Modules.Items/ItemOverlay.razor) | 查价主页面 |
| 估价面板 | [ValuationResult.razor](file:///e:/python_space/Sidekick/src/Sidekick.Modules.Items/Valuation/ValuationResult.razor) | 价格汇总面板 |
| poe2scout 客户端 | [ScoutClient.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe2Scout/Clients/ScoutClient.cs) | poe2scout.com API 客户端 |
| poe2scout 物品 | [ScoutItemProvider.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe2Scout/Items/ScoutItemProvider.cs) | 物品匹配逻辑 |
| poe2scout 历史 | [ScoutHistoryProvider.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe2Scout/History/ScoutHistoryProvider.cs) | 价格历史查询 |
| poe2scout UI | [Poe2ScoutResult.razor](file:///e:/python_space/Sidekick/src/Sidekick.Modules.Items/Poe2Scout/Poe2ScoutResult.razor) | POE2 专属估价展示 |
| poe.ninja UI | [PoeNinjaResults.razor](file:///e:/python_space/Sidekick/src/Sidekick.Modules.Items/PoeNinja/PoeNinjaResults.razor) | poe.ninja 估价展示 |
| 挂牌详情 | [ItemComponent.razor](file:///e:/python_space/Sidekick/src/Sidekick.Modules.Items/Trade/Items/ItemComponent.razor) | 单个挂牌渲染 |
| 价格显示 | [PriceDisplay.razor](file:///e:/python_space/Sidekick/src/Sidekick.Modules.Items/Components/PriceDisplay.razor) | 价格+通货图标 |
| POE2 ninja 数据 | `data/poe2/raw/ninja/*.json` | 通货/精髓/裂隙等统计 |
| POE2 联赛 | `data/poe2/leagues.json` | POE2 联赛列表 |
| POE2 过滤器 | `data/poe2/trade/filters.*.json` | 多语言交易筛选器 |
| 启动注册 | [StartupExtensions.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/StartupExtensions.cs) | 依赖注入注册 |