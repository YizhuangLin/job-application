# per-APP 数据文件 Schema 说明 — `jobs/APP###.yaml`

> 本文件供**人**阅读（不是脚本读）。它说明 `build.py` 三阶段工作流中，per-APP 数据文件每个字段的含义、谁负责填、填写规则。
> 配套：`build.py`（生成脚本）· `_verifier_prompt.md`（独立核对 agent 指令）。

---

## 一、完整工作流（prep → 阶段2 → 核对 → make → 质量审核 → review 投递闸）

> **2026-05-26 重构：** factcheck / qualreview 不再写独立 `.md` 文件。
> 报告 inline 显示给候选人本人，状态全部存 `APP###.yaml` 的 `review_status` 字段
> + `applications.md` Match 列。
> 新增两个 build.py 子命令：`factcheck-pass` 和 `qualreview-pass`。

```
build.py prep ──► jobs/APP###.yaml 草稿 ──► 阶段2 Claude 填改写
                                                  │
                          ┌── build.py verify ────┤  检查阶段2 完整性
                          │   派独立核对 agent ────┘  agent 返回报告 inline
                          │        │
            FAIL ─────────┤        ├──── NEEDS-USER ──► 本人逐条裁决
            Claude 按报告  │        │                    Claude 执行（删/留/补 SSOT）
            自动修阶段2    │      PASS
                          │        │
                          │  build.py factcheck-pass  ──► yaml review_status.factcheck = PASS
                          │        │
                          └─► build.py make ──► 简历 + CL 的 PDF（调 Reactive Resume API，内置版式检查）
                                   │
                                   ▼
                          派质量审核 agent ──► 返回报告 inline（含 RATING + EXPECTATION）
                                   │
                                   ▼
                       build.py qualreview-pass  ──► yaml review_status.qualreview 写入
                                   │              ──► applications.md Match 列同步
                                   ▼
                          build.py review ◄─── 投递前总闸（3 检查全绿才放行）
                                   │            ① factcheck PASS ② 版式 ③ qualreview 4 级评级 + 期待句
                          全绿 ──► 可投递（手动）
```

| 阶段 | 执行者 | 动作 |
|---|---|---|
| prep | `build.py prep` | 抓 JD、从 `master_resume.yaml` 载入各段、分配 APP 编号、写 applications.md 占位行、生成 YAML 草稿 |
| 阶段2 | Claude 会话 | 读 YAML + SSOT，填 `rewritten` / `cover_letter` / `provenance` / `locked_facts` / `bilingual_line.keep` |
| verify | `build.py verify` | 检查阶段2 是否填全；读 yaml `review_status.factcheck.result` 判定状态 |
| 核对 | 独立 agent | 拿 SSOT + 填好的 YAML（不参与改写、不读改写者上下文），逐条核对事实，**返回报告 inline** |
| 裁决执行 | Claude 会话 | NEEDS-USER：把报告贴对话里 → 本人裁决 → Claude 执行（删 rewritten / 补 SSOT + Change Log / 判断同步 master_resume.yaml） |
| factcheck-pass | `build.py factcheck-pass` | 裁决全部执行完后 Claude 跑此命令 → yaml `review_status.factcheck` 写 PASS + 时间戳 + note。**需传 `--report`**（agent 报告存盘后传入，命令校验首行 `RESULT: PASS\|NEEDS-USER` 并把报告全文 + content_hash 写入 yaml） |
| make | `build.py make` | 核对门禁（factcheck PASS 才放行）→ 替换/删段/压 1 页/打包简历+CL → 写 applications.md Resume File →**内置版式检查** |
| 质量审核 | 独立 agent | 拿 JD + 成品 PDF，审 JD 匹配度+说服力+ATS 友好性，**返回报告 inline**（含 RATING / EXPECTATION 机器行）|
| qualreview-pass | `build.py qualreview-pass` | 把 4 级评级 + 期待句写进 yaml `review_status.qualreview` + applications.md Match 列 |
| review | `build.py review` | **投递前总闸** —— 3 检查（factcheck/版式/qualreview）全绿才打印「可投递」 |

**硬规则 1：`build.py make` 内置核对门禁 —— `review_status.factcheck.result` 为 PASS 才放行。**
（测试可加 `--skip-verify` 跳过，正式投递勿用。）

**硬规则 2：投递前必须跑 `build.py review`，四项全绿才可投递：**
- factcheck PASS（即 `review_status.factcheck.result == "PASS"`，且 content_hash 与当前内容一致——不一致说明锁定后内容被改过，需重新核对；旧版无 content_hash 的记录只警告不阻断）
- 版式检查通过（页数/字符/CL 1页 等）
- qualreview 已做（`review_status.qualreview.rating ∈ {High, Medium-High, Medium, Low}` + `expectation` 非空 + applications.md Match 列与 yaml 一致）
- JD 留档完整（`jd.raw_text` 去空白后 ≥ 200 字符 + `jd.source` 非空）

### 核对的三种结果

| Agent 返回 | 含义 | 下一步 |
|---|---|---|
| **RESULT: PASS** | 无阻断、无待确认 | Claude 跑 `build.py factcheck-pass` → 进 make |
| **RESULT: FAIL** | 有阻断项（疑似编造 / 策略违规） | Claude **自动**按阻断项的「建议处理」改 yaml rewritten → 重新派核对 agent |
| **RESULT: NEEDS-USER** | 无阻断，但有「SSOT 可能漏记」的待确认项 | Claude 把报告 inline 贴在对话里 → 本人逐条裁决 |

**NEEDS-USER 的裁决：** factcheck「待本人确认项」列出的是 SSOT 没记录、但可能是候选人真实经历/技能的内容。本人判断每条，Claude 执行：
- **属实** → ① 必做：先改 SSOT（`workspace.yaml` 的 `paths.ssot` 指向的文件）+ 追加 Change Log，再保留该 rewritten；
  ② 判断做：Claude 自行决定是否同步母版 `master_resume.yaml`（通用技能/重要成果→进母版；细分经历→只进 SSOT），当场执行不留 `⏳`。
- **不属实** → 从 rewritten 删除。
- 裁决全部执行完后跑 `build.py factcheck-pass --app APP### --note "..."`。

> 核对 agent 把「SSOT 找不到支撑」分两类是关键：**疑似编造**该删，**SSOT 漏记**该补。这个区分只有候选人本人能做。
> 补进 SSOT 是「不反复确认同一问题」的根本 —— 核对依据是 SSOT，SSOT 有支撑后下次同一事实直接通过。
> **不再写 `_factcheck.md` 文件** —— Change Log 已经记录所有信息池更新，factcheck 报告本身是临时审查产物，
> 看完决策完就消化掉。yaml `review_status.factcheck.passed_at` + `note` 保留决策时间和摘要。

---

## 二、字段总览

> **schema v2（2026-05-22 起）**：母版 YAML 化重构后的结构。母版是 `master_resume.yaml`；
> APP###.yaml 的 `resume` 段从「三个写死的公司字段」改为 `experience` 列表 + `skills` 列表。

```yaml
schema_version: 2            # 必填。make 校验，不匹配则报错（旧 v1 文件需重新 prep）。

app_id: "APP-037"            # prep 写入。本地 applications.md 是编号 SSOT。
company: "seoplus+"          # prep 写入（来自 CLI 参数）。
role: "SEO Specialist"       # prep 写入。
created: "2026-05-22"        # prep 写入。
stage: "Drafting"            # prep 写 Drafting；make 成功后由 Claude 收尾时改 Ready。

jd:
  source: "<url>|pasted"     # prep：JD 来源
  raw_text: |                # prep：JD 全文原样留底
    ...
  salary: ""                 # prep：正则轻量抽取，抽不到留空
  location: ""               # prep：同上
  contract_type: ""          # prep：permanent|contract|part-time，抽不到留空
  jd_summary: ""             # 阶段2 Claude 填：3-5 句 JD 重点

resume:
  summary:
    master: "<母版 summary 原文>"   # prep 从 master_resume.yaml 载入
    rewritten: ""            # 阶段2 Claude 填。空 = 沿用 master
  experience:                # 列表，每段一个公司（顺序 = 简历呈现顺序）
    - id: "ore"              # 稳定 key（ore / target_social / kinking）—— 不要改
      title: "..."           # prep 载入，固定史实，不改写
      date: "..."            # prep 载入，固定史实
      org_line: "..."        # prep 载入，固定史实
      bullets:               # 列表，每条 {master, rewritten}
        - { master: "...", rewritten: "" }   # rewritten 空 = 沿用 master
    # target_social / kinking 同结构
  education:                 # prep 载入，原样用，不改写（学位/日期/机构）
    - { degree: "...", date: "...", org_line: "..." }
  skills:                    # 列表，每行一项 {label, role, master, rewritten}
    - label: "Development:"  # prep 载入。label 固定，不改
      role: ""               # 语义标记，仅 Languages 行为 "languages"
      master: "<母版技能行>"  # prep 载入
      rewritten: ""          # 阶段2 Claude 填。空 = 沿用 master
    # SEO & Marketing: / Tools: / Languages: 同结构
  bilingual_line:
    present_in_master: true  # prep 写入（master 是否有 meta.bilingual_sentence）
    keep: true               # 阶段2 Claude 按 JD 判定。false → make 删 Summary 双语句 + Languages 行

cover_letter:
  date: "May 22, 2026"               # prep 预填（当天）
  recipient_company: "seoplus+"      # prep 预填
  re_line: "SEO Specialist"          # prep 预填
  salutation: "Dear Hiring Team,"    # prep 预填
  body_paragraphs:                   # 阶段2 Claude 填，3-4 段
    - ""
  closing: "Sincerely,"              # prep 预填
  signature: "Jane Doe"              # prep 预填（示例名；实际从 master_resume.yaml contact 取）

page_compression:                    # 超页时的内容缩减优先级（Claude 回阶段2时参考执行）
  # ⚠ 2026-07-07 政策：页数上限见 workspace.yaml resume_layout.max_pages（默认 1，
  #   学术/科研岗可配多页；init 建档时问一次，之后不再重复确认）。
  #   超页只允许**缩减内容**，禁止缩小字号/行距/边距 —— 排版类 step 已废除。
  steplist:                          # 按 order 升序，从低价值内容删起
    - { id: "drop_oldest_bullet", order: 1 }       # 删最后一段经历的最后一条 bullet
    - { id: "languages_line",  order: 2 }          # 删 Languages 行
    - { id: "bilingual_line",  order: 99 }         # 末位手段：删 Bilingual 句 + Languages 行

provenance:                          # 阶段2 Claude 填：每个改写事实点的 SSOT 出处
  - { claim: "5× organic traffic growth", source: "SSOT 三节 ORE 行" }

locked_facts:                        # 阶段2 Claude 填：make 数字归一化粗筛用
  numeric: ["5", "150", "20"]        # 纯数值（去单位/符号）

review_status:                       # 2026-05-26 新增。审核状态全部存这里（不再写独立 .md 文件）
  factcheck:                         # build.py factcheck-pass 写入
    result: "PASS"                   # 锁定后才有此字段；PASS = 所有本人裁决已执行完
    passed_at: "2026-05-26T10:00:00" # ISO 时间戳
    note: "本人裁决：A1 删 / B2 SSOT 漏记已补..."   # 裁决摘要（可选 --note）
    content_hash: "a1b2c3d4e5f6a7b8"  # 2026-07-07 新增：resume+cover_letter 内容 sha256 前16位，防锁定后被改动
    report: |                        # 2026-07-07 新增：核对 agent 报告全文（--report 文件内容原样存入）
      RESULT: PASS
      ...
  qualreview:                        # build.py qualreview-pass 写入
    rating: "Medium"                 # 4 级：High | Medium-High | Medium | Low
    expectation: "够格但非强匹配，可投别抱高预期"   # ≤ 30 字
    passed_at: "2026-05-26T10:30:00"
    report: |                        # 2026-07-07 新增：qualreview agent 报告全文（可选 --report 传入）
      RATING: Medium
      ...

tracking:                            # 2026-07-07 新增。投递状态唯一源——applications.md
                                      # 两张表是从全部 APP###.yaml 的 tracking 子树 + 顶层
                                      # company/role/stage **生成**的产物，不再手编辑。
  category: "Marketing"              # md Active 表 Category 列
  location: "Ottawa (hybrid)"        # md Active 表 Location 列
  applied: "2026-04-14"              # 或 null（未投）；md Applied 列
  outcome: "Pending"                 # Pending|—|Rejected 等；md Outcome 列
  match: "High"                      # md Match 列（镜像 review_status.qualreview.rating 的显示值）
  follow_up_by: "2026-04-23"         # 或 null；submit 时自动 = applied + 7 天；md Follow-up by 列
  resume_file: "APP002_..."          # 不含扩展名；md Resume File 列
  notes: "Indeed"                    # md Notes 列全文
  closed:                            # 未关闭为 null；关闭后由 build.py close 写入
    date: "2026-07-07"
    reason: "No response · 投递后 84 天无回应 (Applied 2026-04-14)"
```

**tracking 子树不进 `content_hash` 计算范围**（`content_hash()` 只序列化 `resume` + `cover_letter` 两个子树）——改 `tracking`（投递状态变更）不会使已锁定的 `factcheck` 哈希失效，不需要重新核对。

**旧系统 legacy stub：** `build.py tracker --migrate` 对 applications.md 里存在、但没有对应 `jobs/APP###.yaml`（旧系统 APP-001~037 遗留）的行，会创建一个精简 stub：

```yaml
schema_version: 2
app_id: "APP-003"
company: "TRADER Corporation"
role: "Web Designer"
created: null
stage: "Closed"
legacy: true                         # 标记：无 resume 段，不支持简历生成/核对流程
tracking: { ... }
```

`legacy: true` 或缺 `resume` 段的 yaml，`verify` / `make` / `factcheck-pass` 会直接报错拒绝（`_legacy_or_missing_resume_guard`）——这些岗位只用于 tracking 展示，不是活跃的简历生成流程。

---

## 三、阶段2 填写规则（Claude 必读）

### 3.1 `rewritten` 怎么填

- **留空 = 沿用 `master` 原文。** 未针对本 JD 调整的段，不必复制粘贴，留空即可。
- **填了 = 用你写的文本替换。** 改写 = 把 SSOT 已有事实换一个贴合本 JD 的讲法/侧重，**不是**造 JD 想要但 SSOT 没有的事实。
- JD 想要、但 SSOT 找不到支撑的内容 → **留空保留原文**，不要编。

### 3.2 简历策略规则（判据在 workspace.yaml `strategy_rules`）

跨岗位统一的取舍口径**不写死在本文件**：规则原文维护在 SSOT 的「简历生成策略」
小节，核对判据镜像在 `workspace.yaml` 的 `strategy_rules`（`build.py prompt` 渲染时
注入核对/质检 agent）。阶段2 填写时逐条遵守该列表；新增规则 = 改 SSOT + 同步一条进
`strategy_rules`，不改本文件。

与 schema 字段直接相关的两条通用机制：

1. **`bilingual_line.keep` 按 JD 判定。** JD 明确要求/偏好目标语言/双语 → `keep: true`；JD 未提及 → `keep: false`。
   - `keep: false` → make **无条件**删 Summary 的双语句 + Languages 行（精确句存 `meta.bilingual_sentence`）。
   - `keep: true` → 默认保留；但若简历超页、且内容缩减 step 全部用尽仍超页，双语句是**末位缩减手段**（steplist 里 order=99）。宁可先删低价值内容，语言能力是 JD 匹配卖点，最后才牺牲。**任何情况下不用缩排版换页数。**
2. **母版 vs 定制的分层。** 母版是内容全集。事实/风险层规则（如货币换算）母版本身已遵守；针对性减法规则（如按 JD 删语言句/删大额金额）母版保留、定制时按 JD 删。不要为执行减法规则去改母版。

### 3.3 `provenance` 怎么填

- 每一条非空的 `rewritten` 和每段 `cover_letter.body_paragraphs`，其中的事实点（数字、技能熟练度、客户名、年限）都要在 `provenance` 列出 `{claim, source}`。
- `source` 指向 SSOT 的具体位置（章节名 / 表格行 / 原句）。
- provenance 不是"自证清白"——它是给核对 agent 的对照面。核对 agent 仍会独立通读 SSOT 验证。

### 3.4 `locked_facts.numeric` 怎么填

- 列出改写文本里出现的关键数值，**去掉单位和符号**（`5×` → `"5"`，`150%` → `"150"`，`$60-70k` 不算改写内容不用列）。
- 用途：make 阶段做数字归一化粗筛（最后一道兜底，非主防线）。

---

## 四、固定史实约束（Target Social / Kin-king）

`experience` 列表里 `id` 为 `target_social` 和 `kinking` 的两段是历史事实段。
改写**只能调叙述角度/动词/侧重**（仅动各 bullet 的 `rewritten`），不能改动事实元素，
`title` / `date` / `org_line` 一律不改：

- 职级：Target Social 是 **Senior** Digital Marketing Manager（SSOT 第二节，不可降写）
- 客户名：GAC Honda Odyssey（Target Social）、GAC Trumpchi + A2 milk powder（Kin-king）—— 注意 SSOT 明确标过 "GAC Toyota" 是错的，不可出现
- 预算/数字：母版已是 CAD（11M+ CAD / 1.9M+ CAD），保持

核对 agent 会逐条核对这些事实元素是否被改动。

---

## 五、make 阶段的自动化边界

`build.py make` **只自动写** `applications.md` 的 Active 表对应行（填 Resume File 文件名、确认占位行存在）。

以下仍由 Claude 会话按 `CLAUDE.md` 的「同步检查清单」收尾，make 不碰：
Notion 同步 · README 第三节快照 · README 文件结构图 · README 末尾日期 · applications.md 拒信挪 Closed 表 · Response Rate Log · SSOT Change Log · Stage 语义推进（Drafting→Ready→Applied）。

`build.py make` 运行结束会打印同步清单待办提醒。

## 六、版式唯一来源（2026-07 重构）

简历 / cover letter 的版式（HTML 渲染路径）**唯一来源**是 `auto-apply/templates/` 目录：

- `templates/_header.html.j2` —— 共享页头宏 `header(contact, divider=false)`。
  resume 和 CL 都调用这一个宏生成 name + contact 行 HTML，两个文档的页头因此
  **强制同源**（改一处、两处一起变，不可能出现结构漂移）。CL 比 resume 多一条
  contact 行下分隔线，用 `divider=true` 参数显式表达，不是隐藏差异。
- `templates/_theme.css.j2` —— 共享设计 token（CSS 自定义属性）：字体、颜色
  （ink / name / muted / dim）、分隔线粗细、name/contact 字号等。两个文档模板
  的 `<style>` 里 `{% include '_theme.css.j2' %}` 引入这些 token，文档级的差异
  （body 字号行高、`@page` margin）留在各自模板里，但差异化覆盖也必须引用
  `var(--...)` token，不得重新写死颜色/字体值。
- `templates/resume.html.j2` / `templates/cl.html.j2` —— 两个文档模板本身，
  分别持有各自专属的排版规则（section 间距、job/edu 排版等）。

**约束（铁律）：**
- **任何会话不得为单份简历 / 单份 CL 修改上述模板文件**（不允许"这次投递字号临时调小一点"这种改法）。
- 版式调整 = 改 `_theme.css.j2`（token）或 `_header.html.j2`（页头结构）或两个文档模板的专属规则段，
  **必须 git commit 留痕**，且要过一遍视觉回归检查（pdftotext -layout diff + pdfinfo 页数一致）。
- 简历与 CL 的页头由共享宏保证同源；如果发现两者页头看起来不一致，说明有人绕过了
  `_header.html.j2` 直接改了某个文档模板 —— 应视为 bug 修复，改回引用共享宏。

## 七、状态变更命令（2026-07-07 新增）

> **⚠️ applications.md 两张表（Active Applications / Closed / Skipped）现在是生成物。**
> 区间由 `<!-- AUTO-GENERATED: build.py tracker（勿手编辑，改 yaml 后重跑）-->` 标记，
> **不要手编辑标记区间内的表格行**——改了也会在下次 `build.py tracker` 时被覆盖。
> 要变更投递状态，改对应 `jobs/APP###.yaml` 的 `tracking` 子树，或用下面的子命令
> （子命令写完 yaml 后会自动重跑 `tracker` 重新生成表格）。区间外内容（文件头 /
> Stage Definitions / Response Rate Log）不受影响，**Response Rate Log 仍需手动追加**。

### `build.py tracker [--migrate]`

- `--migrate`：**一次性**命令。解析 applications.md 现有 Active + Closed/Skipped 表，
  把每行内容写入对应 APP 的 `tracking` 子树（已有 `jobs/APP###.yaml` 的只更新
  `tracking` + 顶层 `stage`/`company`/`role`，不碰 `resume`/`cover_letter`/`review_status`；
  没有 yaml 的旧系统 APP 创建 `legacy: true` stub）。跑完自动生成一次表格，
  之后可用对比脚本核对迁移前后语义一致。**只应该跑一次**，重复跑是幂等的但没有意义
  （表格内容此后应该只由 yaml 变化驱动，不该反向从 md 再读一遍）。
- 不带参数：从全部 `jobs/APP-*.yaml` 的当前状态重新生成两张表，替换标记区间内容。
  Active 表 = `stage` 不是 `Closed` 的 APP（按编号升序）；Closed 表 = `stage == Closed`
  的 APP。**任何 yaml 变更后想让 applications.md 反映出来，跑这个命令**（`submit`/`close`
  已经自动跑过，手改 yaml 后需要自己跑一次）。

### `build.py submit --app APP-### [--date YYYY-MM-DD] [--external]`

登记投递。默认先跑投递闸（`cmd_review` 同款四项检查抽出的 `_review_gate()`），
有 blocker 就拒绝登记并列出待办。`--external` 跳过闸——用于登记在流水线外完成的投递
（内推 / 猎头渠道直接投的，没走 build.py make/review 全流程），这种情况建议在
`tracking.notes` 里注明来源渠道。

过闸后写入：`tracking.applied` = 指定日期（默认今天）、`tracking.outcome` = `"Pending"`、
`tracking.follow_up_by` = `applied + 7 天`、顶层 `stage` = `"Applied"`。然后自动重新生成
表格，并打印人读的 Notion 同步 payload（`Status: Applied` + Apply Date）供会话照着调
`notion-update-page`。**投递本身仍是手动动作**——这个命令只负责登记，不会真的帮你提交申请。

### `build.py close --app APP-### --reason <no-response|rejected|withdrawn|skipped|expired> [--note "..."] [--date YYYY-MM-DD]`

关闭一条投递。写入 `tracking.closed = {date, reason}`（`reason` 是拼好的中文描述，
`no-response` 会自动算「投递后 N 天无回应」，`--note` 追加到描述末尾）、顶层 `stage` =
`"Closed"`。自动重新生成表格，并打印 Notion payload（`--reason` 映射到 Notion Status：
`rejected→Rejected`、`no-response→No Response`、`withdrawn→Withdrawn`、
`skipped/expired→Skipped`）。

### `build.py fact --topic "..." --content "..." [--cause "..."] [--files "..."] [--tier3 "..."]`

SSOT（`workspace.yaml` 的 `paths.ssot` 指向的文件）Change Log 表的机械追加命令。**用途：** Claude 先手动
编辑 SSOT 对应章节正文（事实变更本身仍需要人读判断落在哪一节、怎么措辞），改完之后跑
这个命令，只负责在 Change Log 表最后一行之后追加一行留痕 + 刷新文件末尾「最后更新」
日期——不负责判断事实变更本身是否合理。定位方式：找最后一个 `| 2026-...` 开头的表格行。

### `build.py dashboard [--out 路径]`

生成单文件、自包含、零外部请求的只读投递看板 HTML（默认 `REPO_ROOT/dashboard.html`）。
数据全部内嵌（JSON script 标签 + 直接渲染的表格/卡片），不引任何 CDN/外链字体/外链脚本。
内容从 `_collect_pipeline_data()`（`cmd_status` 同款数据组装，两者共用同一份逻辑）派生：
顶部统计卡、今日行动告警区、Drafting/Ready/Applied/Closed 四列看板（Closed 折叠）、
可排序全量表格、按月投递/回应趋势条。**纯只读** —— 不提供任何写入功能，页面上注明
生成时间 + 重新生成命令；写入仍走 `submit`/`close`/`tracker`。`dashboard.html` 已加入
`.gitignore`（可随时重建的派生物，不入库）。

### `build.py selftest`

环境 + 数据自检，退出码 `0`=全过 / `1`=有 FAIL。按序检查：① 系统依赖（pdfinfo/pdftotext）
② 渲染路径真实可用（Playwright 尝试启动 Chromium；WeasyPrint 不可用只标 ⚠，除非
Playwright 也不可用则 FAIL）③ 端到端渲染（用 `master_resume.yaml` 组装 content，
`html_render.render_resume` 到临时文件，跑 `layout_check_resume` 全过）④ 数据完整性
（`workspace.yaml`/`master_resume.yaml`/全部 `jobs/APP-*.yaml` 可解析 + schema 校验）
⑤ tracker 幂等（`regenerate_tracker_tables()` 连跑两次比对 `applications.md` 内容不变）
⑥ 文档一致（调 `sync_check.py`，非 0 退出码只标 ⚠ 不 FAIL）
⑦ 引擎 lint（`engine_lint()` 扫描 `auto-apply/*.py` + `auto-apply/templates/*` +
`jobs/` 下两个 prompt 模板里的个人硬编码字符串——扫描模式来自 `workspace.yaml`
`lint_patterns` + 母版 `contact.name` 派生，命中即 FAIL；模式为空时跳过并提示）。

---

## 八、新工作区 init 与可复制性（2026-07-07 起）

> **目标：** 这套引擎（`build.py` + `templates/` + `html_render.py`/`docx_render.py`）
> 本身不属于任何具体的人——个人事实（姓名/联系方式/履历）全部活在
> `master_resume.yaml` + SSOT（`workspace.yaml` 的 `paths.ssot` 指向的文件）里，
> 引擎代码不写死任何人的姓名/邮箱/电话。新用户可以复用同一份引擎、给自己建一个
> 独立工作区。

### 路径配置化

`find_repo_root()` 定位仓库根的优先级：
1. 环境变量 `RESUME_WORKSPACE`（若设置，直接用它，跳过目录探测）。
2. 逐级向上找 `workspace.yaml`（新版工作区标志文件，找到即视为仓库根）。
3. 回退：旧双文件判据（`applications.md` + legacy SSOT 文件名同时存在）——
   兼容尚未加 `workspace.yaml` 的旧工作区。

`workspace.yaml` 新增 `paths` 段（缺省即用默认值，不会因为字段缺失而报错）：

```yaml
paths:
  ssot: "Context_Master.md"      # 履历事实 SSOT 文件名（相对仓库根），引擎默认值
  applications: "applications.md"  # 投递追踪表
```

引擎的模块级默认值是通用文件名 `Context_Master.md`；沿用历史文件名的旧工作区在
`workspace.yaml` 里显式覆盖即可，这样默认值调整不影响既有工作区——
`workspace.yaml` 里的显式值优先。

### `build.py init [--dir 目标目录]`

在目标目录生成一套空白工作区脚手架（默认当前目录；目录须为空或不含
`workspace.yaml`，已有则拒绝覆盖）：

- `workspace.yaml`（配置层：`resume_layout.max_pages` 默认 1 页 + 注释说明学术/
  科研岗可改多页 · `paths` 段）
- `Context_Master.md`（SSOT 模板：个人档案/工作经历/核心项目/教育/技能评级表/
  简历生成策略规则区/变更日志表头，每节内嵌 HTML 注释填写指引）
- `master_resume.yaml`（`schema_version: 2` 骨架：contact/summary/experience 一段
  示例/education/skills 四行/`meta.bilingual_sentence`）
- `applications.md`（空表骨架：Active/Closed 表头 + AUTO-GENERATED 标记 +
  Stage Definitions + Response Rate Log 表头）
- `auto-apply/jobs/` · `auto-apply/applications/` 目录
- `.gitignore`（`__pycache__/` / `dashboard.html` / `.DS_Store`）

**`init` 不生成 `build.py` 本体**——目标目录复用某处已有的引擎代码，通过
`RESUME_WORKSPACE` 环境变量指向目标目录来运行（例如
`RESUME_WORKSPACE=/path/to/new-workspace python3 /path/to/build.py selftest`）。
`init` 生成的模板骨架不含任何具体个人信息。

### 引擎 lint（selftest ⑦）

`engine_lint()` 扫描 `auto-apply/*.py`（含子目录 `templates/*` 一层）**以及
`jobs/_verifier_prompt.md` / `_quality_review_prompt.md`（2026-07-07 发布阶段起）**里是否含
个人标识字面量（扫描模式 = `workspace.yaml` `lint_patterns` + 母版 `contact.name` 派生的
token，引擎代码不内置任何具体用户的模式列表）。命中即 selftest FAIL，
逼迫任何新加的个人硬编码在合入前被发现。prompt 模板已改为占位符模板：工作区专属的
事实红线/策略规则只活在 `workspace.yaml`（`fact_redlines` / `strategy_rules` 段），
由 `build.py prompt --app APP### --type verifier|qualreview` 渲染时注入
`{{FACT_REDLINES}}` / `{{STRATEGY_RULES}}` 等占位符——派发 agent 时直接用该命令的
stdout，不再手动替换 `{{APP_ID}}`。

代码里极少数无法避免的字面量（如向后兼容旧工作区文件名的 fallback 常量）用行内
`# engine-lint-allow: ...` 注释显式标记豁免那一行，其余任何新硬编码都会被 lint 抓到。
