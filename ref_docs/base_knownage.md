# PoE 腾讯服（QQ服）交易系统 API 知识库

> 记录日期：2026-06-11
> 整理自对 `https://poe.game.qq.com/trade2` 的逆向分析

---

## 目录

1. [基础信息](#1-基础信息)
2. [鉴权机制](#2-鉴权机制)
3. [API 端点](#3-api-端点)
4. [频率限制](#4-频率限制)
5. [页面结构](#5-页面结构)
6. [Cookie 清单](#6-cookie-清单)
7. [注意事项](#7-注意事项)

---

## 1. 基础信息

| 项目 | 值 |
|------|-----|
| 基础地址 | `https://poe.game.qq.com` |
| 交易系统路径 | `/trade2` |
| 服务器 | openresty/1.21.4.1 |
| 当前联赛（2026-06） | 奥杜尔秘符（PoE2） |
| 区域（Realm） | poe2 |
| 前端框架 | Vue.js SPA + require.js |
| 静态资源 CDN | `https://poecdn.game.qq.com` |
| 可用联赛 | 奥杜尔秘符、奥杜尔秘符（专家）、永久、永久（专家） |

---

## 2. 鉴权机制

### 2.1 匿名访问

匿名访问交易页面或 API 会被重定向到腾讯登录页面，返回登录表单 HTML。

登录选项：
- **QQ 登录**：`graph.qq.com` OAuth
- **微信登录**：`open.weixin.qq.com` OAuth

### 2.2 Cookie 认证

需要提供完整的 Cookie 字符串才能访问 API。仅提供 `POETOKEN` 是不够的，必须包含所有关键 Cookie（参见 [6. Cookie 清单](#6-cookie-清单)）。

认证失败的 HTTP 状态码：
- `401 Unauthorized` — Cookie 过期或无效
- 页面返回登录表单而非交易界面

### 2.3 认证流程

```
浏览器登录腾讯服 → 获取完整 Cookie → 携带 Cookie 请求 API
```

---

## 3. API 端点

### 3.1 获取查询详情（GET）

```
GET https://poe.game.qq.com/api/trade2/search/poe2/{league}/{query_id}
```

**参数：**

| 参数 | 说明 | 示例 |
|------|------|------|
| `league` | 联赛名（URL 编码后） | `奥杜尔秘符` |
| `query_id` | 查询 ID | `lV7P5oVUV` |

**响应示例：**

```json
{
  "id": "lV7P5oVUV",
  "query": {
    "name": "森林灵像",
    "type": "克己权杖",
    "stats": [{ "type": "and", "filters": [] }],
    "status": { "option": "any" }
  }
}
```

---

### 3.2 获取搜索结果（GET）

```
GET https://poe.game.qq.com/api/trade2/fetch/{query_id}
```

**参数：**

| 参数 | 说明 | 示例 |
|------|------|------|
| `query_id` | 查询 ID | `lV7P5oVUV` |

**响应：** 返回商品结果列表（若无结果则返回 `{"result":[null]}`）。

> 此端点实际需要额外的 `id` 参数（fetch 商品的具体 ID 列表），例如：
> `GET https://poe.game.qq.com/api/trade2/fetch/{query_id}?ids=id1,id2,...`

---

### 3.3 执行搜索（POST）

```
POST https://poe.game.qq.com/api/trade2/search/poe2/{league}
```

**请求体（JSON）：**

```json
{
  "query": {
    "name": "物品名",
    "type": "物品类型",
    "stats": [{ "type": "and", "filters": [] }],
    "status": { "option": "any" }
  },
  "sort": { "price": "asc" }
}
```

**错误响应：**

```json
{
  "error": {
    "code": 2,
    "message": "查询丢失"
  }
}
```

| Code | 说明 |
|------|------|
| 0 | Accepted（已接受） |
| 1 | Resource not found |
| 2 | Invalid query |
| 3 | Rate limit exceeded |
| 4 | Internal error |
| 5 | Unexpected content type |
| 6 | Forbidden |
| 7 | Temporarily Unavailable |
| 8 | Unauthorized |
| 9 | Method not allowed |
| 10 | Unprocessable Entity |

---

### 3.4 其他可能端点（待验证）

参考国际服官方 API，可能还有以下端点：
- `GET /api/trade2/data/leagues` — 获取联赛列表
- `GET /api/trade2/data/static` — 获取静态数据（物品类型、词缀等）
- `GET /api/trade2/data/stats` — 获取词缀列表

---

## 4. 频率限制

### 4.1 机制概述

PoE API 采用**动态频率限制**，所有限制参数通过响应头返回，没有固定数值。限制可能随时调整。

### 4.2 响应头字段

| 响应头 | 说明 |
|--------|------|
| `X-Rate-Limit-Policy` | 当前请求所属的限流策略名 |
| `X-Rate-Limit-Rules` | 适用的规则类型（逗号分隔），如 `ip`, `account`, `client` |
| `X-Rate-Limit-{rule}` | 规则定义，格式见下方 |
| `X-Rate-Limit-{rule}-State` | 当前请求的限流状态，格式见下方 |
| `Retry-After` | 被限流后需等待的秒数 |

### 4.3 限流规则格式

`X-Rate-Limit-{rule}` 和 `X-Rate-Limit-{rule}-State` 的格式均为：

```
max_hits:period_seconds:ban_seconds
```

**举例：**

```
X-Rate-Limit-Client: 10:5:10
X-Rate-Limit-Client-State: 1:5:0
```

解读：每 5 秒最多 10 次请求，超限封禁 10 秒；当前已用 1 次，未被限流。

### 4.4 限流状态码

`429 Too Many Requests` — 被限流，必须等待 `Retry-After` 指定的秒数。

### 4.5 无效请求阈值

频繁发送导致 4xx 错误的请求（401、403、429 等）会触发**无效请求阈值**，导致访问被暂时或永久限制。

### 4.6 最佳实践

1. **解析并遵守 `X-Rate-Limit-*` 响应头**，动态控制请求频率
2. **携带有效 Cookie**（`POESESSID`）可获得更高限额
3. 请求间隔建议 **200~500ms**
4. 设置可识别的 `User-Agent` 头（官方推荐格式：`OAuth {clientId}/{version} (contact: {email})`）
5. 避免在短时间内密集发送无效请求
6. 实现指数退避（exponential backoff）策略处理 429 响应

---

## 5. 页面结构

### 5.1 入口页面

HTML 骨架 + Vue.js SPA：

```html
<div id="app"></div>
<!-- 动态加载 -->
<script>
import('https://poecdn.game.qq.com/dist/js/trade.4q7RFFcOPatP.js')
  .then(({ default: app }) => { app.mount(); });
</script>
```

### 5.2 配置注入

页面底部通过 `window.tradeOpts` 注入初始配置：

```javascript
window.tradeOpts = {
  "tab": "search",
  "realm": "poe2",
  "realms": [],
  "leagues": [
    {"id":"奥杜尔秘符","realm":"poe2","text":"《流放之路：降临》 - 奥杜尔秘符"},
    {"id":"奥杜尔秘符（专家）","realm":"poe2","text":"《流放之路：降临》 - 奥杜尔秘符（专家）"},
    {"id":"永久","realm":"poe2","text":"《流放之路：降临》 - 永久"},
    {"id":"永久（专家）","realm":"poe2","text":"《流放之路：降临》 - 永久（专家）"}
  ],
  "league": "奥杜尔秘符",
  "basePath": "/trade2",
  "state": { ... }
};
```

### 5.3 模块结构

通过 require.js 加载模块：
- `baseUrl`: `https://poecdn.game.qq.com/dist/legacy`
- 主入口：`main` → `trade`
- 多语言翻译：`translate.zh_CN.js`
- 登录：`ptlogin_v1.js`

### 5.4 页面模板

页面使用 Vue.js 组件模板：
- `item-search-panel` — 搜索面板
- `filter-group` — 过滤条件组
- `stat-filter-group` — 属性过滤组
- `item-filter` — 单项过滤器
- `statusBar` — 状态栏（显示登录账号信息）

---

## 6. Cookie 清单

从 Chrome 开发者工具获取的完整 Cookie（2026-06-11 有效）：

```text
RK=ILZWx6WxVf
ptcz=dccbd1d7c891ccd6d333f13d65e1ff8c30a80adf7307316f138689442b418b25
pac_uid=0_rTcBpDsA0HQyB
omgid=0_rTcBpDsA0HQyB
_qimei_uuid42=1a41e1203031000970647d97da76a168a3ea16a557
_qimei_fingerprint=a3e0b4fc8a30cee90de446631074e5f6
eas_sid=81q757E989h324A1v5n7e8l0J5
pgv_info=ssid=s7665690821
pgv_pvid=2768476131
poeqqcomrouteLine=list
_qpsvr_localtk=0.3510030209695
POESESSID=f7da9f9e7223d5764aea4c4758642d06
POETOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9.eyJhdWQiOiJvYXV0aC9pbnRlcm5hbCIsImV4cCI6MTc4MTI1NDM5NiwiaWF0IjoxNzgxMTY3OTk2LCJpc3MiOiJ1cm46cGF0aG9mZXhpbGU6cG9lX3ByZCIsInJpZCI6ImRhMjZkNjVmYmM1N2Q5ODUzMDQ2ZjQzMjAwM2ZmZjIxIiwic2NvcGUiOiJpbnRlcm5hbCIsInN1YiI6IjllMzEyZGE0LWQzZjktNGJiOC1hNTcyLTBmYWQ1ZWMzZWZhMSIsInZlcnNpb24iOiI5OTFjNDg1YiIsImNsaWVudF9pZCI6ImludGVybmFsIiwicmVzcG9uc2VfdHlwZSI6ImludGVybmFsIn0.xj_AaRAXkxje-LhBUNH0diJn-Yk8WFFxmWX1oY3Rfo5VmaPXlC18ZpoEM3flz-NS_g5pMCyn67Nc8r1jliF2Yw
```

### 关键 Cookie

| Cookie 名 | 说明 | 有效期 |
|-----------|------|--------|
| `POESESSID` | 会话 ID（关键） | 随会话 |
| `POETOKEN` | JWT 认证 Token（关键） | 约 1 天 |
| `eas_sid` | 腾讯登录态 | 随会话 |
| `RK` | 腾讯登录态（refresh key） | 长期 |
| `ptcz` | 腾讯登录态 | 随会话 |

**注意：** `POETOKEN` 是 JWT 格式，过期时间约 1 天。每次成功请求后服务器会 `Set-Cookie` 新的 `POETOKEN`。

---

## 7. 注意事项

1. **Cookie 有时效性**，过期后会返回 401 错误
2. **禁止逆向工程** — GGG 服务条款明确禁止逆向 API 端点和内部接口
3. 国际服 API 文档参考：[https://www.pathofexile.com/developer/docs](https://www.pathofexile.com/developer/docs)
4. 第三方应用需包含声明：*"This product isn't affiliated with or endorsed by Grinding Gear Games in any way."*
5. 腾讯服与国际服的 API 可能不完全一致