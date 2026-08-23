# BD 探索文档：Rampage 触发 COC（萨满 / 0.5 Runes of Aldur）

> 角色：91 级萨满（Shaman）
> 核心思路：**Rampage 作为移动 + 触发源**，触发 **Cast on Critical（COC）** 自动释放法术。
> COC 提供主要伤害；Rampage 本身不追求伤害，只追求**触发频率**。
> 性质：**实验性 / 未经验证的探索 BD**，非主流成型套路。

---

## 1. 构建目标与定位

| 维度 | 目标 |
|---|---|
| 主伤害来源 | COC 被触发的法术 |
| 触发源 / 移动 | Rampage（边跑边砸地 → 暴击 → 给 COC 充能） |
| 定位 | 高速移动的"跑图施法"玩法，清图为主 |
| 已知风险 | Rampage 是慢速旅行技能，触发频率天然偏低（详见 §2.3） |

---

## 2. 核心机制原理

### 2.1 COC（Cast on Critical）能量机制

COC 是**精魂 Meta 宝石**（Persistent / Trigger / Meta），**占用 100 点精神**，要求智力。

- **充能**：暴击命中敌人时获得能量，能量达到上限自动触发所有镶嵌法术，并清空能量。
- **能量获取公式**（核心）：
  > 基础能量(1) × **怪物威力值** × **(暴击伤害 ÷ 怪物异常状态阈值)** × (全局能量提高% + 100%)
  - 能量会**向下取整**；若结果 < 1 则获得 **0** 能量。
  - 怪物威力值：弱怪 0.5 → 传奇 BOSS 20。**暴击 BOSS 能量收益高**。
  - 但 BOSS 高阈值/高血量导致"伤害÷阈值"占比低 → 实际能量往往低于小怪。
- **最大能量**：`每 0.1 秒基础施法时间 = 10 点最大能量`（由被触发的法术基础施法时间决定）。
- **惩罚**：镶嵌技能造成 **20% LESS 伤害**。
- **宝石等级**提供"获得能量提高 (0–57)%"。
- **品质**：额外的精神保留效率 + 暴击率加成 Buff。
- **致命 Bug**：`Missing Socketed Skill` 在 0.5.3 仍存在，会废掉主 COC 构建（需备好复制宝石/多存档）。

**关键结论**：要让 COC 高频触发，需要① 暴击率拉满（实战 100%）；② 足够的命中频率；③ 最大化"获得能量提高"和降低怪物异常阈值。

### 2.2 Rampage 触发技能本质

Rampage 是**熊形态攻击技能**（Attack / Shapeshift / Bear / AoE / Melee / Slam / Sustained / Channelling / Travel），需魔符（Talisman）。

- **攻击速度：基础 70%**（偏低）。
- **非站立时基础攻击时间 +0.5 秒**（Rampage 核心玩法就是奔跑状态 → 攻击间隔被进一步拉长）。
- 奔跑速度受**移动速度**词缀而非攻击速度词缀影响。
- **使用期间无法获得怒意**。
- 消耗：魔力 + 每秒 5 怒意（前 2.5 秒免怒）。
- 冲击范围 2.2 米。
- **0.5 改进**：不再卡进怪物碰撞体积，可边撞边跑不掉速（利好本玩法）。

### 2.3 核心矛盾：慢速旅行技能 vs 高频触发 ⚠️

这是本 BD 的**最大风险与设计难点**：

- COC 要求**高频命中 + 高暴击**来快速充能。
- Rampage 是**旅行/移动技能**：基础攻速仅 70%，且**奔跑时攻击时间再 +0.5 秒**，导致命中频率极低。
- 命中少 → 暴击少 → COC 能量积累慢 → 触发频率低 → 被触发的法术即使伤害高，实际 DPS 也受限。

**应对思路**：既然 Rampage 命中慢是不可回避的，就要**把每一次触发都做"重"**——选单个触发就够疼的法术，并把暴击率/能量获取堆满，让"稀少的触发"打出可观伤害。这是本 BD 能否成立的关键判断点。

---

## 3. 资料要点汇总

### 3.1 已核实的机制数据（来源：poe2db / game8 / COC 机制解析）

1. **COC 能量公式**中"伤害÷异常阈值"比例决定能量，**降低怪物异常阈值**（如"压迫气场"类手段）可显著提升 BOSS 能量获取。
2. **最大能量随被触发法术的基础施法时间增长**：想触发更频繁 → 用**基础施法时间短**的法术（最大能量低，容易充满）；Rampage 命中慢，更要压低最大能量。
3. **暴击率必须拉满（实战 100%）**：条件性暴击（如"对满血敌人"）不入面板，需自行计算。
4. **获得能量提高**（天赋/辅助`无边能量`/装备/COC 等级）直接放大每次暴击的能量增量。
5. 0.3 起**同一技能宝石不能重复装备** → 每套 COC 只有一个，别指望多套叠加。

### 3.2 0.5 版本相关改动（Return of the Ancients / Runes of Aldur）

- **COC 整体受压**：0.5 主打"战术化、有意义的战斗"，社区大量"退休 COC"呼声；COC 存在长期 `Missing Socketed Skill` Bug（0.5.3 仍复现）。
- **Rampage 加强**：不再卡进怪物碰撞体积（0.5 关键改进）。
- **熊萨满（Bear Shaman）整体强势**：0.5 未受 ES 大削波及，速度清图玩法依然 S 级（参考 Ronarray `RAMPAGE SPEED BEAR`）。
- **Bhatair's Vengeance 被削弱**（冻结流冰伤加成约减半）——若走"冻结+冰伤"连招需更多冰冷/物伤投入，但本 BD 走 COC，不依赖此件。

### 3.3 参考：Rampage 的常规（主流）用法 vs 本 BD

现实中 **Rampage 的主流用法是"速度清图"，不是 COC 触发源**（此前抓取的 5 名上榜萨满 + mobalytics/Odealo 攻略均如此）：

| 用法 | 定位 | 说明 |
|---|---|---|
| 主流 | **移动/清图** | Rampage 提供 120%+ 移速边跑边砸，配 Walking Calamity + 冰霜光环爆炸清屏 |
| 本 BD | **COC 触发源** | 用 Rampage 的暴击给 COC 充能，靠自动法术输出（实验性） |

> 此前分析 5 名玩家时，**没有任何人**用 Rampage 触发 COC，说明这是**冷门/未验证方向**，需自行打通机制。

---

## 4. 构建建议

### 4.1 触发频率优化方向（Rampage 作为触发源）

1. **暴击率拉满（核心）**：目标实战 100% 暴击。莎满/熊形态暴击节点、`Prism of Belief`、装备暴击词缀、COC 品质 Buff 都要堆。
2. **压低被触发法术的最大能量**：选**基础施法时间短**的法术 → 最大能量低 → Rampage 几次暴击就能充满、触发更频繁。
3. **堆"获得能量提高"**：COC 等级 + `无边能量`辅助 + 相关被动。
4. **降低怪物异常阈值**：提升 BOSS 战能量，保证对高血量目标也能稳定触发。
5. **攻击速度词缀照堆**：虽然移动速度看移速，但**砸地攻击本身仍受攻击速度影响**，攻速能提升每次 Rampage 跑动的命中次数。

### 4.2 被触发法术的选择

- **原则**：因为 Rampage 触发频率低，选"单发够重"或"一发清屏"的法术，避免依赖高频叠层的法术。
- **避坑**：`Comet` 等基础施法时间很长的法术 → 最大能量极高 → 触发极慢，不适配慢触发源。
- 可考虑：高伤范围法术 / 可自动索敌法术；具体需在游戏内实测充能速度后定夺。

### 4.3 升华（Ascendancy）建议

- **Bringer of the Apocalypse**：提供 `Apocalypse` 自动触发技，可作**补充伤害**，与 COC 并行。
- **Sacred Flow**（每空槽 +40 精神）：缓解 COC 100 精神 + 光环的精神压力。
- **Turning of the Seasons**：自带 Exposure 与随机元素附加，提升法术伤害。
- 若偏暴击/充能，可点**暴击相关**节点或用 `Prism of Belief` 珠宝补暴击。

### 4.4 装备与词缀

- **魔符（Talisman）必带**：Rampage 依赖魔符。
- 优先：**暴击率、攻击速度、+法术等级、+精神、移动速度**。
- 命中/精准：近战需堆 Accuracy（戒指/头盔）。
- 防御：熊形态靠 Armour + Life；0.5 下 Armour 可转元素减伤（Reactive Growth），目标 1.8w+ 护甲。

### 4.5 精神 / 资源管理

- COC 占用 **100 精神**，需预留足够精神给：COC + 光环（如 Herald）+ 可选 Walking Calamity。
- 莎满 `Sacred Flow`、装备 `精神力`、`精神保留效率` 都要考虑。
- Rampage 消耗怒意且**无法在冲刺中回怒**：若副点怒意相关增伤（如 Druidic Champion），需外部手段补怒，否则冲突。

---

## 5. 风险与待验证事项

| 风险 / 待验证 | 说明 |
|---|---|
| ⚠️ **触发频率天花板低** | Rampage 奔跑时攻击间隔 +0.5s，命中频率天然低，COC 充能慢，需实测 DPS 是否可接受 |
| ⚠️ **COC `Missing Socketed Skill` Bug** | 0.5.3 仍存在，可能废掉主 COC 构建，备好替代宝石 |
| 法术-能量匹配 | 具体法术的充能速度需进游戏实测后才能定 |
| BOSS 能量不足 | BOSS 高阈值导致能量低，需"降低异常阈值"手段 |
| 精神预算 | COC 100 精神 + 光环，需确认够用 |
| 怒意冲突 | 若要怒意增伤（Druidic Champion），Rampage 无法自回忝是关键矛盾 |

---

## 6. 结论与下一步

- **可行性判断**：本 BD **机制上可行但很强求**——Rampage 是移动/清图技能，天然不适合做高频 COC 触发源。它的价值在于"边高速移动边自动施法"的玩法乐趣，而非极致 DPS。
- **建议先小规模验证**（而非直接成型）：
  1. 先把**暴击率拉满**，确认 Rampage 每次跑动能稳定出暴击充能；
  2. 选一个**基础施法时间短**的法术塞 COC，实测触发频率与单发伤害；
  3. 确认精神够用、无 Bug 卡死；
  4. 若触发频率实在过低，可降级定位为"移动 + 补充触发"（主伤害交给 Walking Calamity / Apocalypse 等萨满常规输出），而非纯 COC 主伤。

---

## 参考来源

- poe2db.tw — [Cast on Critical](https://poe2db.tw/Cast_on_Critical) / [Rampage](https://poe2db.tw/Rampage)
- game8 — [Cast on Critical Gem Effects](https://game8.co/games/Path-of-Exile-2/archives/491236) / [Rampage Gem Effects](https://game8.co/games/Path-of-Exile-2/archives/571286)
- 大神 COC 机制解析（能量公式、暴击拉满、降阈值）— [什么值得买转载](https://post.m.smzdm.com/p/ad734z7d/)
- Odealo — [Bear Form Shaman](https://www.static.odealo.com/articles/bear-form-shaman-poe2-build) / [CoC Detonate Dead Abyssal Lich](https://static.odealo.com/articles/detonate-dead-abyssal-lich-poe-2-build)
- Mobalytics — [0.5 Shaman Bear Druid（RAMPAGE SPEED BEAR）](https://mobalytics.gg/poe-2/builds/bear-druid-build-league-starter-to-endgame)
- Boostmatch — [PoE2 Druid Best Build Guide](https://boostmatch.gg/blog/poe-2/articles/poe2-druid-best-build-guide-0-5)
- 官方论坛 — [COC Missing Socketed Skill Bug（0.5.3）](https://www.pathofexile.com/forum/view-thread/3971178/page/1)