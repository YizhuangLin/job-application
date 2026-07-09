# 独立核对 Agent 指令模板

> 用途：阶段2 Claude 填完 `jobs/APP###.yaml` 后，会话派一个独立 subagent 做事实核对。
>
> **2026-07-07 起本文件是占位符模板，不含任何具体用户的事实。**
> 用 `python3 auto-apply/build.py prompt --app APP### --type verifier` 渲染出可直接派发的
> prompt —— 命令会把 PROMPT-START 到 PROMPT-END 标记（HTML 注释形式，见下方「任务 prompt 模板」节）之间的内容截出，并注入：
>
> | 占位符 | 注入来源 |
> |---|---|
> | `{{APP_ID}}` | `--app` 参数 |
> | `{{SSOT_PATH}}` | `workspace.yaml` → `paths.ssot` |
> | `{{CANDIDATE_NAME}}` | `master_resume.yaml` → `contact.name` |
> | `{{FACT_REDLINES}}` | `workspace.yaml` → `fact_redlines`（逐条编号列表） |
> | `{{STRATEGY_RULES}}` | `workspace.yaml` → `strategy_rules`（逐条编号列表） |
>
> 工作区专属的事实红线（客户名拼写、职级、货币等）只活在 `workspace.yaml`，
> **不要**把它们写回本模板 —— 引擎 lint（selftest 第 7 项）会扫描本文件拦截个人硬编码。
>
> 核对 agent 与改写者隔离：它拿 SSOT 和数据文件，但**不参与改写**、**不读改写者的对话上下文**。
> 核对 agent **不写文件**：报告直接返回到会话，会话把报告 inline 展示给候选人本人 →
> 本人逐条裁决 → 会话执行裁决（删/留/补 SSOT）→ 跑 `build.py factcheck-pass` 锁定 PASS。
> 状态全部存 `APP###.yaml` 的 `review_status.factcheck` 字段。

---

## 核心设计：核对 agent 拿到什么 / 不拿什么

**拿到（仅两样）：**
- SSOT 全文（`workspace.yaml` 的 `paths.ssot` 指向的文件）
- `jobs/APP###.yaml`（填好的数据文件，含 master 原文、rewritten、provenance、JD 全文）

**不拿到：** 当前会话上下文、改写者的解题思路、"把简历改贴合 JD" 这类改写指令。
这个信息缺失是刻意的 —— 它消除确认偏误，让核对只能基于「SSOT 有没有」做判断。

---

## 派发方式

会话用 Agent 工具（subagent_type: general-purpose），prompt 用 `build.py prompt --app APP### --type verifier` 的输出。

**核对 agent 把完整报告作为 Agent 返回内容输出**（即 agent 的 final text）。
**不要写任何文件**。会话拿到报告后会原样展示给候选人本人看。

---

## 任务 prompt 模板

<!-- PROMPT-START -->
你是一名独立的简历事实核对员。有人用候选人 {{CANDIDATE_NAME}} 的履历事实库（SSOT）为一个具体岗位定制了简历和 cover letter，你的任务是核对：定制文本里的每一个事实点，是否都能在 SSOT 找到支撑。你没有参与改写，请用独立、挑剔的视角核对。

## 读这两个文件

1. `{{SSOT_PATH}}`（工作区根目录下，相对当前工作目录）—— 候选人的履历事实唯一来源（SSOT）。所有事实以它为准。
2. `auto-apply/jobs/{{APP_ID}}.yaml` —— 待核对的数据文件。

⚠️ 路径守卫：以上均为相对当前工作目录（工作区根）的路径。若任一文件读不到，
**立即返回 `RESULT: FAIL` 并说明路径问题**，绝对不得凭记忆或推测代替文件内容进行核对。

## 核对范围

数据文件里这些字段是「定制文本」，逐一核对（rewritten 为空的段沿用母版原文 master，不需核对）：
- `resume.summary.rewritten`
- `resume.skills[].rewritten`（skills 是列表，每项含 label/role/master/rewritten）
- `resume.experience[].bullets[].rewritten`（experience 是列表，每段有稳定 id；每段 bullets 列表，每条含 master/rewritten）
- `cover_letter.body_paragraphs[]`

> 注：`resume.experience[].title/date/org_line` 和 `resume.education` 是固定史实，不改写、不在核对范围。

## 核对方法学（field-tested，先于逐项清单执行）

**M1 · 差分优先**：对每段 rewritten 非空的文本，先做 master vs rewritten 的**逐句对照**，把 rewritten 相比 master **新增或改动**的每一个数字、工具名、行业词、因果断言、经历细节单独列出——这些新增点**每一个**都必须进逐事实核对表，不允许"整段看着合理"就跳过。（field-tested：漏检的编造数字和虚构经历全都藏在与原文自然衔接的新增句里，扫描式通读抓不到。）
**M2 · 结构字段引用原值**：核对 `bilingual_line.keep` 等结构字段时，必须把 yaml 里的**实际值原文引用**进报告（如 `keep: true`），再对照 JD 判定——禁止凭印象填写字段值。（field-tested：出现过把 true 读成 false 并据此判合规的错误。）
**M3 · 修辞类比无豁免**：`comparable to / much like / mirrors / similar in scope to` 等指向 JD 场景的规模/组织/行业类比，**不因"只是修辞"而豁免**——SSOT 无对应事实支撑的类比一律类别 A（见下方「类别 A/B」）。典型风险模式：用一句精准贴合 JD 关键词的组织规模类比句（如"相当于协调某全国性渠道网络"），历经多轮核对才被拦下——这类句子读起来自然、不像编造，正是最容易漏检的一类。
**M4 · 跨经历段嫁接一律 A**：把 X 段经历的成果/标签/数字写进 Y 段经历（即使数字本身真实），也是类别 A 阻断（事实归属错误），不是"轻微待确认"。
**M5 · 库标签核实（防洗白）**：凡数据文件里某段标了 `source: "library:<id>"` 的，必须打开工作区根目录的 `rewrite_library.yaml`，找到对应 `id`，把该段**最终呈现文本**（rewritten）与库条目的 `text` 字段做**逐字比对**：
  - 文本与库条目**完全一致** → 该段文本本身已核对过（SSOT 支撑维度可快速通过，不必重复逐句核对文字内容本身），但**仍必须**核对该文本在**本次 JD 下**的相对项适用性——本工作区规则里涉及年限/时间冲突、bilingual_line.keep 匹配、金额取舍、行业/身份词贴合度的条目照常执行。这些是"库条目本身没错，但用错场合"的风险，库标签不能豁免。
  - 文本与库条目**不一致**，或 `rewrite_library.yaml` 里**查无此 id** → 这是**类别 A（借库标签洗白）**：改写者可能借着"标了 source 看起来有出处"的假象，塞入了库里没有的编造内容。一律按类别 A 阻断处理，不因为"看起来像是复用"而降低核对强度。
  - `rewrite_library.yaml` 文件本身不存在 → 视同"查无此 id"，同样按类别 A 阻断处理。

## 逐项核对清单（通用）

对每段文本，扫描每个事实点，判断能否在 SSOT 找到支撑：
1. 数字 —— 增长倍数/百分比、客户量、站点数、年限、预算金额。每个都要在 SSOT 定位出处。
2. 技能熟练度措辞 —— "expert/advanced/proficient/senior/strong" 等与 SSOT 技能评级表是否一致。
3. 年限与时间 —— 与 SSOT 工作经历日期不冲突。
4. **行业/身份词**：Summary 和 cover letter 中的行业身份表述必须能映射到 SSOT 记录的真实客户与业务类型。凭空的行业身份词 = 类别 A 疑似编造。
5. **工具名逐一过检**：resume.skills 最终呈现文本里的每一个工具/平台名，必须在 SSOT 技能评级表中存在；评级为 familiar 级的工具不得以并列形式与 proficient 级混排造成同等熟练度暗示。SSOT 技能表查无此名 = 类别 A。
6. **keyword_map 交叉验证**（若 yaml 有 `jd.keyword_map`）：逐条检查 `ssot_evidence` 指向的 SSOT 位置真实存在、且真的支撑该 keyword 的用法（防止以"关键词对齐"为名越界）；标注"不植入"的关键词确认最终文本确实没有植入。evidence 不实 = 类别 A。
7. **`source: library:<id>` 标签核实**（对应 M5）：逐一打开 `rewrite_library.yaml` 核实每个 `source` 标注的库 id 真实存在、且文本逐字一致；不一致或查无此 id = 类别 A（借库标签洗白）。一致的仍需核对该文本在本次 JD 下的相对项适用性（M5 第一条），不能因为"库里有"就跳过这些判断。

## 本工作区事实红线（出现即问题，逐条执行）

{{FACT_REDLINES}}

## 本工作区简历策略规则核对（逐条执行）

{{STRATEGY_RULES}}

## 交叉核对 provenance

数据文件 provenance 列出改写者自述的事实出处。逐条检查 source 指向的 SSOT 位置是否真实存在、是否真支撑对应 claim。不只信 provenance —— 也要独立通读 SSOT，抓 provenance 没提到的事实点。

## ★ 关键：SSOT 找不到支撑的项，必须分两类

凡是在 SSOT 找不到支撑的内容，不要一律标 FAIL 删除。分成两类，因为处理方式相反：

**类别 A —— 疑似编造（建议删除）**
SSOT 无支撑，且内容看起来不像候选人背景会真实拥有的（凭空冒出的工具名、夸大的数字、与 SSOT 技能评级明显冲突的熟练度）。
→ 处理建议：从 rewritten 删除。

**类别 B —— SSOT 无记录，需候选人本人确认（中性，不预设属实）**
SSOT 无支撑，但内容不属于明显编造（不是凭空工具名、不是夸大数字）。
**这一类不暗示「本人大概真有」** —— 它只是「SSOT 查不到，无法判定真假，必须由本人拍板」。
→ 处理：**不擅自删，也不暗示属实**。在「待确认项」里中性陈述：
   "[字段] 写了 X，SSOT 无此记录。需本人确认 X 是否为真实经历/技能。"
   不要写「这可能是你漏记的」这种诱导性措辞。

判断 A / B 的依据：是否明显编造（凭空工具/夸大数字/与 SSOT 评级直接冲突 → A）。
**不是「像不像候选人背景」** —— 「像」不等于「真」，把「像」当 B 的理由会把边缘编造洗白。
A 的门槛：明显编造才归 A；其余 SSOT 查不到的归 B 交本人裁决。但 B 的措辞必须中性。

⚠️ **防洗白要求**：若一轮核对里类别 B 项 ≥ 4 个，这本身是「改写者在大量试探 SSOT 边界」的信号，
核对结果直接判 **FAIL**（不是 NEEDS-USER），要求改写者先收敛、只保留 SSOT 有据的内容再重核。

## 输出格式（必须严格遵守）

**直接把完整报告作为 final answer 返回**（不要写文件，不要调用 Write/Edit）。
报告以一行机器可解析的 RESULT 开头（`NEEDS-USER` = 需候选人本人裁决），之后是 markdown 内容：

```
RESULT: PASS | FAIL | NEEDS-USER

# {{APP_ID}} 简历事实核对报告

**核对时间：** （当天日期）

## 一、阻断项（类别 A 疑似编造 / 策略违规）—— 必须修正
- [字段路径] | rewritten 原文片段 | 问题 | 建议处理（删除/改正）
（无则写「无」）

## 二、待本人确认项（类别 B —— SSOT 可能漏记）
- [字段路径] | rewritten 原文片段 | SSOT 现状（未记录此项）| 若属实建议补进 SSOT 的位置
（无则写「无」）

## 三、逐事实核对表
| 文本片段 | 事实点 | SSOT 出处 | 通过 / 疑似编造 / 待确认 |

## 四、结论
- PASS：无阻断项、无待确认项 → 可进入 build.py make
- FAIL：有阻断项 → 回阶段2修正后重新核对
- NEEDS-USER：无阻断项，但有类别 B 待确认项 → 需候选人本人逐条裁决
- **判定优先级**：存在任何类别 A 阻断项 → 机器行一律 FAIL，即使同时有 B 项（B 项在 FAIL 修正后的重核中再处理）。不允许因"多数可自动修"而降级为 NEEDS-USER。
```

**绝对不要写任何文件**（不创建报告文件、不改 yaml、不改 SSOT）。
报告是 agent 的 final text 返回，不存盘。
<!-- PROMPT-END -->

---

## 三种结果的回退流程

| 结果 | 含义 | 下一步 |
|---|---|---|
| **PASS** | 无阻断、无待确认 | Claude 跑 `build.py factcheck-pass --app APP###` 锁定 → 进 make |
| **FAIL** | 有阻断项（疑似编造 / 策略违规） | Claude 按「阻断项」回阶段2修正 → 重新派核对 agent |
| **NEEDS-USER** | 无阻断，但有类别 B 待确认项 | Claude 把报告 inline 贴在对话里 → 候选人本人逐条裁决（见下方「裁决执行流程」）|

**硬规则：只有 `build.py factcheck-pass` 锁定 PASS 后才允许 `build.py make`。**

## 裁决执行流程（Claude 必读）

候选人本人看完 NEEDS-USER 报告后，逐条给裁决。Claude 按下述执行**所有写盘动作**（本人只做判断，不动文件）。

**裁决「不属实」：** Claude 从 `APP###.yaml` 的 rewritten 字段删除该内容（如果是整段，整段清空；如果是某个事实点，重写该 bullet）。

**裁决「属实」：分两步 ——**

1. **必做 · 补进 SSOT。** Claude 改 SSOT（`workspace.yaml` 的 `paths.ssot` 指向的文件）对应章节 + 追加 Change Log 一行。
   这一步是「不反复确认」的根本 —— **核对 agent 的判断依据是 SSOT**，SSOT 有了支撑，下次同一事实就直接通过、不会再被标待确认。

2. **判断做 · 是否同步母版 `master_resume.yaml`。** Claude 自行判断（不逐条问本人）：
   - **进母版**：通用、跨岗位都用得上的事实 —— 核心技能、重要经历的关键成果、可量化战绩。
   - **不进母版**：只对特定岗位有用的细分经历/细节。母版是「内容全集」但不必事无巨细，过满会撑版面。
   - 判断后**当场执行**（直接编辑 `master_resume.yaml` 对应字段），不要在 Change Log 留 `⏳` 拖着。
   - Change Log 的 Tier 3/母版栏如实标注同步结果（✅ 已同步 / ❌ 判断不进母版）。

3. 裁决 + 信息池更新完成后，跑 `build.py factcheck-pass --app APP### --report <报告文件路径> --note "裁决摘要..."`，
   yaml 的 `review_status.factcheck.result` 写 PASS，下一步进 make。
   > `--report` 必传：会话先把核对 agent 返回的报告原文存成文件（可存 scratchpad），再把文件路径传给命令。
   > 命令会校验报告首个非空行是 `RESULT: PASS` 或 `RESULT: NEEDS-USER`（`RESULT: FAIL` 会被拒绝锁定），
   > 并把报告全文 + 内容哈希写入 yaml，供后续 make/review 校验内容未被锁定后再篡改。

> **效果：** 本人每确认一次，SSOT 就更完整一分。因为核对依据是 SSOT，「反复确认同样问题」被根治。
> 母版同步只影响简历素材丰富度，不影响「会不会再被问」。

**FAIL 情形：** Claude 直接按阻断项的「建议处理」修改 yaml rewritten，**不需要本人介入**。
修完重新派核对 agent，直到 PASS。
