# Sidekick 支持国服（腾讯服）可行性评估

> 评估日期：2026-06-12  
> 参考：[国服交易系统 API 知识库](file:///e:/python_space/MyPoeAssist/docs/base_knownage.md)  
> 基准：Sidekick 当前实现（仅支持国际服）

---

## 一、总评分

| 维度 | 难度 | 工作量 | 可行性 |
|------|------|--------|--------|
| 鉴权机制 | 🔴 极高 | 大 | 有条件可行 |
| API 兼容性 | 🟢 低 | 小 | 可行 |
| 数据源替代 | 🟡 中 | 中 | 有条件可行 |
| 道具解析 | 🟡 中 | 中 | 可行 |
| 限流适配 | 🟢 低 | 小 | 可行 |
| **综合评价** | **中高难度** | **数周~数月** | **可行但有条件** |

---

## 二、核心障碍分析

### 障碍 1：鉴权机制（最大障碍）

**现状（国际服）：** Sidekick 使用匿名 `HttpClient` 直接调用 `pathofexile.com/api/trade2/`，仅需处理 Cloudflare 人机验证。

**国服要求：** 腾讯服强制要求 QQ/微信 OAuth 登录，必须携带完整 Cookie 链才能访问 API。

**需要实现的能力：**

1. **浏览器登录流程** — 内嵌 WebView2 打开腾讯登录页面，让用户完成 QQ/微信扫码
2. **Cookie 捕获** — 从 WebView2 中提取登录后的完整 Cookie（包括 `POESESSID`、`POETOKEN`、腾讯系 cookie 如 `RK`、`ptcz`、`eas_sid` 等）
3. **Token 刷新** — `POETOKEN` 是 JWT，约 1 天过期，每次成功请求后服务器会 `Set-Cookie` 新的 Token，需要持续跟踪刷新
4. **Cookie 持久化** — Sidekick 已有 [HttpClientCookie 表](file:///e:/python_space/Sidekick/src/Sidekick.Common.Database/Tables/HttpClientCookie.cs) 用于存储 Cookie，但当前仅用于 Cloudflare 挑战后的 Cookie 暂存，需要扩展为完整的 Cookie 管理方案
5. **多用户支持** — 不同用户使用不同 WeGame 账号登录

**参考实现思路：**
```
用户首次查价 → 检测未登录 → 弹出 WebView2 窗口
    → 用户扫码登录腾讯服 → 捕获全部 Cookie
    → 加密持久化到本地 SQLite → 后续请求自动携带
    → 检测 POETOKEN 过期 → 自动刷新或提示重新登录
```

**对比现有的 Cloudflare 挑战机制：**  
Sidekick 已有 [CloudflareService](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Common/Cloudflare/CloudflareService.cs)，它弹 WebView2 让用户完成 Cloudflare 验证。国服鉴权可复用此模式，但复杂度要高得多：
- 不是一次性的挑战，而是完整的 OAuth 流程
- Cookie 数量和品类远多于 Cloudflare
- Token 有保质期需要定期刷新

---

### 障碍 2：数据源不可用

**现状：** Sidekick 的 POE2 估价依赖两个数据源：

| 数据源 | 用途 | 国服是否可用 |
|--------|------|-------------|
| poe2scout.com | 24h 价格走势图 | ❌ 仅国际服 |
| poe.ninja | 市场价统计 | ❌ 仅国际服 |
| GGG Trade API | 实时挂牌 | 🔄 需要替换为腾讯 API |

**替代方案：**

1. **实时挂牌** — 将 GGG Trade API 调用改为腾讯服 API 调用（API 结构高度相似，改动成本低）
2. **价格走势/市场价统计** — 需要自建或接入国服特有的数据源，例如：
   - **POE2Lens**（poe2lens.com）— 国服专属查价站，但不确定是否提供公开 API
   - **自行爬取**国服交易站数据建立价格数据库（法律和服务条款风险）
   - **众包方案** — 让用户安装插件贡献匿名价格数据，累积建立价格指数
3. **poeprices.info** 的机器学习估价 — 目前 POE2 国际服都没有，国服更不可能有

**结论：** 实时挂牌功能可以替代；价格走势和市场统计功能需要另寻数据源或自建。

---

### 障碍 3：道具文本解析

**现状：** Sidekick 支持 10 种游戏语言，但使用的是繁体中文（`GameLanguageZh`）对应 `pathofexile.tw`（台服）。

**国服要求：** 腾讯服使用简体中文，且文本内容可能与国际服/台服有差异。

**影响范围：**

| 模块 | 影响 | 改动量 |
|------|------|--------|
| `GameLanguageZh` | 需要新增简体中文实现 | 中（新增 200+ 属性） |
| 稀有度/属性/词缀正则匹配 | 需要简体中文版本的文本映射 | 中 |
| 道具定义匹配 | `data/poe2/items/zh.json` 需确认是否兼容 | 小 |
| 物品分类 | `data/poe2/item-classes/zh.json` 需确认 | 小 |
| 交易过滤器 | `data/poe2/trade/filters.zh.json` 需确认来源 | 小 |

**好消息：** Sidekick 的语言体系是插件化的（`IGameLanguage` 接口），添加新的语言实现有既有模式可循。

---

### 障碍 4：API 兼容性

**文件：** [国服知识库](file:///e:/python_space/MyPoeAssist/docs/base_knownage.md#3-api-端点)

**国服 API 与国际服对比：**

| 维度 | 国际服 | 国服 | 兼容性 |
|------|--------|------|--------|
| 搜索 URL | `POST /api/trade2/search/{league}` | `POST /api/trade2/search/poe2/{league}` | 🟢 路径几乎一致 |
| 获取 URL | `GET /api/trade2/fetch/{id}?query={q}` | `GET /api/trade2/fetch/{id}?query={q}` | 🟢 完全一致 |
| 域名 | `www.pathofexile.com` | `poe.game.qq.com` | 🔄 需要配置化 |
| 联赛名 | 英文（如 `Runes of Aldur`） | 中文（如 `奥杜尔秘符`） | 🟡 需处理 URL 编码 |
| 请求体格式 | JSON 标准格式 | 几乎一致 | 🟢 兼容 |
| 响应体格式 | 标准格式 | 几乎一致 | 🟢 兼容 |
| 错误码 | HTTP 状态码 | JSON 内 `error.code` | 🔄 需额外处理 |

**需要改动的 Sidekick 代码：**

1. `IGameLanguage` 接口 → 新增国服专用的 Base URL 属性（`PoeCnTradeBaseUrl` / `PoeCnTradeApiBaseUrl`）
2. `GameType` 枚举 → 可选：新增 `PathOfExile2Cn` 类型，或通过配置区分
3. `TradeApiHandler` → 去除对中文语言的屏蔽逻辑，替换为国服鉴权逻辑
4. 联赛数据源 → 联赛列表需从国服 API 获取或静态配置

---

## 三、改动方案

### 方案 A：最小改动（推荐）

**策略：** 在现有架构上新增"国服模式"，与国际服代码共用核心逻辑。

```
┌─────────────────────────────────────────┐
│             现有 Sidekick 架构           │
├─────────────────────────────────────────┤
│  ItemParser  │  PropertyParser          │
│  StatParser  │  PseudoParser            │
│  TradeFilter │  UI 组件                │ ← 核心逻辑基本不动
├─────────────────────────────────────────┤
│            新增"国服适配层"               │
├─────────────────────────────────────────┤
│  ① GameLanguageCn (简中语言实现)         │
│  ② CnTradeApiHandler (国服鉴权管道)      │
│  ③ CnCookieProvider (腾讯Cookie管理)     │
│  ④ CnLeagueProvider (国服联赛)           │
│  ⑤ CnTradeApiClient (poe.game.qq.com)   │
│  ⑥ CnScoutProvider (国服价格走势源)       │
└─────────────────────────────────────────┘
```

**需要改动的文件清单：**

| 文件 | 改动内容 | 预估工时 |
|------|----------|---------|
| [IGameLanguage.cs](file:///e:/python_space/Sidekick/src/Sidekick.Data/Languages/IGameLanguage.cs) | 新增国服 Base URL 属性 | 1h |
| `GameLanguageCn.cs`（新建） | 简体中文语言实现 | 8h |
| [TradeApiHandler.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Clients/TradeApiHandler.cs) | 去除中文屏蔽，或创建 CnTradeApiHandler | 4h |
| `CnCookieService.cs`（新建） | 腾讯 Cookie 获取/刷新/持久化 | 40h |
| [TradeApiClient.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Clients/TradeApiClient.cs) | 支持国服域名和静态数据 | 2h |
| [ItemTradeService.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Trade/ItemTradeService.cs) | 支持国服路由 | 4h |
| [LeagueProvider.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe.Trade/Leagues/LeagueProvider.cs) | 国服联赛列表 | 2h |
| [ScoutClient.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe2Scout/Clients/ScoutClient.cs) | 替换为国服价格数据源 | 40h+（取决于数据源） |
| [ScoutItemProvider.cs](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Poe2Scout/Items/ScoutItemProvider.cs) | 适配国服物品 | 8h |
| 道具定义 JSON 文件 | 简体中文版本 | 16h |
| UI 组件 | 国服模式切换/登录状态显示 | 8h |
| **总计** | | **~133h（约1个月）** |

### 方案 B：插件化（更可持续）

在方案 A 的基础上，将"国服支持"做成独立插件/模块，不影响国际服功能：

```
Sidekick.sln
├── src/Sidekick.Apis.Poe.Trade/          ← 国际服（不动）
├── src/Sidekick.Apis.PoeCn.Trade/        ← 新增：国服交易插件
│   ├── CnTradeApiHandler.cs
│   ├── CnCookieService.cs
│   └── ...
├── src/Sidekick.Apis.Poe2Scout/          ← 国际服（不动）
├── src/Sidekick.Apis.Poe2ScoutCn/        ← 新增：国服价格走势
├── src/Sidekick.Data/                    ← 扩展语言接口
└── src/Sidekick.Modules.Items/           ← UI 扩展
```

---

## 四、关键代码对比

### 4.1 API 调用差异

**国际服（现存）：**
```csharp
// ItemTradeService.cs - 匿名调用
var uri = new Uri($"{language.GetTradeApiBaseUrl(item.Game)}search/{league}");
using var httpClient = httpClientFactory.CreateClient(TradeApiClient.ClientName);
var response = await httpClient.PostAsync(uri, body);
```

**国服需要改为：**
```csharp
// 需要：① 携带 Cookie ② 处理 OAuth ③ 处理 POETOKEN 刷新
var uri = new Uri($"https://poe.game.qq.com/api/trade2/search/poe2/{Uri.EscapeDataString(league)}");
using var httpClient = httpClientFactory.CreateClient("PoeCnTradeClient");
httpClient.DefaultRequestHeaders.Add("Cookie", await cnCookieService.GetCookieString());
var response = await httpClient.PostAsync(uri, body);
// 更新 POETOKEN（从 Set-Cookie 响应头）
await cnCookieService.UpdateCookies(response.Headers.GetValues("Set-Cookie"));
```

### 4.2 鉴权流程（新增）

```csharp
public class CnAuthService
{
    // Step 1: 检查是否有有效 Cookie
    public async Task<bool> IsAuthenticated()
    {
        var cookies = await cookieStore.GetAll();
        return cookies.ContainsKey("POESESSID") && cookies.ContainsKey("POETOKEN");
    }

    // Step 2: 弹出 WebView2 让用户登录
    public async Task Authenticate()
    {
        // 复用现有的 CloudflareService 弹窗机制
        // 导航到 https://poe.game.qq.com/trade2
        // 用户完成 QQ/微信扫码登录
        // 从 WebView2 捕获所有 Cookie
        // 持久化到数据库
    }

    // Step 3: 验证并刷新 Token
    public async Task<bool> RefreshIfNeeded()
    {
        // 检查 POETOKEN 是否过期（JWT 解码检查 exp）
        // 如过期，用 Refresh Token 或提示重新登录
    }
}
```

### 4.3 限流处理（可复用）

**文件：** [国服知识库 #4](file:///e:/python_space/MyPoeAssist/docs/base_knownage.md#4-频率限制)

国服的限流机制使用 `X-Rate-Limit-*` 响应头，Sidekick 现有的 [ApiLimiterProvider](file:///e:/python_space/Sidekick/src/Sidekick.Apis.Common/Limiter/ApiLimiterProvider.cs) 可以直接适配，只需调整限流策略参数：

```csharp
// 国服示例：每 5 秒最多 10 次，超限封禁 10 秒
// X-Rate-Limit-Client: 10:5:10
// 现有 LimitRule 可以解析此格式
```

---

## 五、风险与限制

### 不可控风险

| 风险 | 等级 | 说明 |
|------|------|------|
| **服务条款** | 🔴 高 | GGG 服务条款明确禁止逆向 API。腾讯服可能也有类似条款。Sidekick 本身已声明不官方关联 GGG。需要法律评估。 |
| **Cookie 时效性** | 🟡 中 | 腾讯登录态可能随时过期，需要用户重新扫码，影响用户体验。 |
| **API 反向不兼容** | 🟡 中 | 腾讯服的 API 可能在赛季更新时发生变化，需要持续跟进。 |
| **第三方数据源** | 🟡 中 | POE2Lens 等第三方国服数据源可能不提供公开 API，或随时关闭。 |

### 已知限制

| 限制 | 说明 |
|------|------|
| **无价格走势图** | 国服没有类似 poe2scout.com 的公开价格历史数据源 |
| **无机器学习估价** | poeprices.info 不支持国服，也没有替代品 |
| **流通数据差异** | 国服市场与国际服完全隔离，物价差异巨大，国际服的参考数据无用 |
| **首次使用门槛** | 用户需要 QQ/微信账号 + WeGame，登录流程比国际服复杂 |

---

## 六、结论与建议

### 可行性结论

| 功能模块 | 可行性 | 说明 |
|----------|--------|------|
| ✅ 实时挂牌搜索 | **可行** | API 结构高度兼容，主要工作量在鉴权 |
| ⚠️ 挂牌详情展示 | **可行** | 数据格式基本一致，UI 可复用 |
| ⚠️ 道具解析 | **有条件可行** | 需新增简体中文语言实现 + 文本适配 |
| ❌ 价格走势图 | **当前不可行** | 缺乏公开的国服价格历史数据源 |
| ❌ 市场价统计 | **当前不可行** | poe.ninja 仅国际服，国服无替代品 |
| ✅ 词缀筛选 | **可行** | 筛选器结构一致，数据需从国服 API 拉取 |

### 建议路线

```
Phase 1（基础功能，2-3周）
├── 新增简体中文语言实现 + 道具定义
├── 实现腾讯 OAuth 登录流程（WebView2）
├── 实现 Cookie 持久化和自动刷新
├── 替换 API 路由到 poe.game.qq.com
└── 去除 TradeApiHandler 中的中文屏蔽

Phase 2（功能补齐，1-2周）
├── 适配国服联赛和过滤器数据
├── 调整限流策略适配国服
├── 调试文本解析的兼容性问题
└── UI 添加国服模式切换和登录状态

Phase 3（数据完善，持续）
├── 探索国服价格数据源（POE2Lens 等）
├── 或自行建立价格采集机制
└── 社区征集和迭代
```

### 最终建议

**技术上可行，但需要投入较大的工程资源（估计 1-2 人月），且有两个关键依赖：**

1. **用户登录体验** — 必须找到一种流畅的 QQ/微信扫码登录方案，不能让用户每次启动都重新登录
2. **价格数据源** — 没有价格走势和市场统计，查价工具的价值会大打折扣。建议先完成 Phase 1 让实时挂牌跑通，再在 Phase 3 探索数据源方案

如果这两个问题有解决方案，Sidekick 支持国服是完全可行的。