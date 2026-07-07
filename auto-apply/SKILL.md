---
name: resume-pipeline
description: JD 驱动的求职投递流水线：岗位筛选 → 定制简历生成（事实核对防造假）→ 投递登记 → 状态追踪与看板。任何会话冷启动跑 status 即可接手全部进度。
version: 1.0.0
---

# Resume Pipeline — 会话契约

> 本文件是流水线的**会话契约**：任何 AI 会话按下面五条工作，即可稳健接手全部进度。
> 流程细节不在本文件——在命令的输出里（每条命令会打印下一步），以及 `jobs/_schema.md`（完整规范）。

## 五条契约

1. **开工先跑 `python3 auto-apply/build.py status`**，以它的输出为当前事实。不要信任何文档快照——快照可能过期，status 是从数据实时算的。
2. **一切状态变更走命令**（`prep` / `submit` / `close` / `fact` / `tracker`）。`applications.md` 的表格是生成物，**禁止手编辑**；简历版式由 `templates/` 唯一定义，**禁止为单份简历改模板**。
3. **履历事实只来自 SSOT**（`workspace.yaml` 的 `paths.ssot` 指向的文件）。改写 = 把 SSOT 已有事实换贴合 JD 的讲法，**绝不造 SSOT 没有的事实**；事实变更先改 SSOT + Change Log（`build.py fact` 留痕）。
4. **人只在两处介入**：① 事实核对的 NEEDS-USER 裁决（SSOT 查不到的内容是真是假，只有本人能拍板）；② 投不投的决定。其余按命令输出执行，不反复请示。
5. **每条命令打印的「下一步」就是下一步**。卡住时跑 `selftest` 查环境，怀疑漂移跑 `status` 看一致性自检。

## 命令地图

```
init         新工作区脚手架（建档一次，页数上限等配置问一次、之后不再确认）
selftest     环境+数据自检（渲染路径/依赖/schema/幂等/引擎lint）
check-update 检查引擎更新（引擎唯一联网命令，仅手动触发）
status       管道全景 + 今日行动 + 一致性自检 + 统计   ← 冷启动第一条
─────────────────────────────────────────────────
prep         抓 JD → 生成 APP yaml 草稿（JD 原文必须留档）
（阶段2）     会话读 yaml + SSOT，填 rewritten/cover_letter/provenance/locked_facts
prompt       渲染核对/质检 agent 派发 prompt（模板占位符 + workspace.yaml 红线注入，stdout 即完整 prompt）
（核对）      派独立核对 agent（prompt --type verifier 的输出）——与改写者隔离，防造假
factcheck-pass  锁定核对 PASS（--report 必传，报告+内容哈希入库，锁后改动会被 make/review 拦截）
make         渲染简历+CL PDF（页数硬闸：超页只减内容，不缩排版）
（质检）      派质量审核 agent（prompt --type qualreview 的输出）→ qualreview-pass 记 4 级评级
review       投递前总闸：factcheck/版式/qualreview/JD留档 四项全绿才可投
─────────────────────────────────────────────────
submit       登记投递（默认过 review 闸；--external 登记流水线外投递如内推）
close        关闭（no-response/rejected/withdrawn/skipped/expired）
fact         SSOT Change Log 机械追加（配合会话手改 SSOT 正文）
tracker      从 yaml 重新生成 applications.md 表格
dashboard    生成单文件本地看板 dashboard.html（零外部请求，数据不出本机）
```

## 设计要点（为什么这样）

- **单一状态源**：`jobs/APP-###.yaml` 存每个投递的全部状态；表格/看板/README 快照都是派生视图，不存在"同步"，只有"重新生成"。
- **防造假三层**：改写者与核对者隔离 → 核对报告 + 内容哈希入 yaml（锁后篡改被拦） → review 总闸。
- **超页只减内容**：排版压缩手段已从引擎物理删除；页数上限在 `workspace.yaml`（学术 CV 可配多页）。
- **隐私**：一切数据在本地文件 + 本地生成的看板；外部镜像（如 Notion）是可选的、由命令打印 payload 人工确认。`check-update` 是唯一主动联网的命令且仅手动触发——`status`/`selftest` 的「>30 天未检查更新」提醒是纯本地时间戳判断，不发任何请求。看到该提醒时，会话应转告用户并询问是否要跑 check-update，不要自行联网。
