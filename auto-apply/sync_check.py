#!/usr/bin/env python3
"""
sync_check.py — 投递文档一致性体检
================================================
用途：扫描 applications/ 目录的简历文件 ↔ applications.md 的表格行 ↔ README.md 的状态快照，
      报告漏登记 / 不一致 / 过期的项，防止派生文档漂移。

何时跑：
  - 怀疑文档漂移时
  - 每次批量投递后做收尾体检
  - 新会话开始想确认当前状态是否可信时

运行：  python auto-apply/sync_check.py
        （在 Resume/ 目录下运行；脚本会自动定位仓库根）

退出码： 0 = 全部一致 · 1 = 发现问题
"""
import os
import re
import sys
import datetime

# ---- 定位仓库根（脚本在 Resume/auto-apply/ 下）----
# 2026-07-07：支持 RESUME_WORKSPACE 环境变量覆盖（与 build.py find_repo_root 一致），
# 否则 build.py selftest 在可复制工作区（drill/新工作区）里调本脚本时，会静默检查
# 脚本物理位置所在仓库而不是目标工作区——同一进程内两套"仓库根"语义不一致。
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.environ["RESUME_WORKSPACE"]) if os.environ.get("RESUME_WORKSPACE") \
             else os.path.dirname(SCRIPT_DIR)                  # Resume/（或 RESUME_WORKSPACE 指向的根）
APP_DIR    = os.path.join(REPO_ROOT, "auto-apply", "applications")
APPS_MD    = os.path.join(REPO_ROOT, "applications.md")
README_MD  = os.path.join(REPO_ROOT, "README.md")

problems = []   # 阻断级
warnings = []   # 提醒级


def app_ids_from_filenames():
    """从 applications/ 目录的简历文件名提取 APP 编号集合（只看简历正文 docx，跳过 cover letter / 面试文档）。"""
    ids = set()
    detail = {}
    if not os.path.isdir(APP_DIR):
        problems.append(f"applications/ 目录不存在：{APP_DIR}")
        return ids, detail
    for fn in os.listdir(APP_DIR):
        m = re.match(r"APP(\d{3})_", fn)
        if not m:
            continue
        num = int(m.group(1))
        ids.add(num)
        detail.setdefault(num, []).append(fn)
    return ids, detail


def app_ids_from_applications_md():
    """从 applications.md 的表格行提取 APP 编号集合。"""
    ids = set()
    if not os.path.isfile(APPS_MD):
        problems.append(f"applications.md 不存在：{APPS_MD}")
        return ids
    text = open(APPS_MD, encoding="utf-8").read()
    for m in re.finditer(r"^\|\s*APP-(\d+)", text, re.MULTILINE):
        ids.add(int(m.group(1)))
    return ids


def readme_dates():
    """提取 README 第三节快照日期 + 末尾最后更新日期。"""
    snap, last = None, None
    if not os.path.isfile(README_MD):
        problems.append(f"README.md 不存在：{README_MD}")
        return snap, last
    text = open(README_MD, encoding="utf-8").read()
    m = re.search(r"当前状态快照（([0-9]{4}-[0-9]{2}-[0-9]{2})）", text)
    if m:
        snap = m.group(1)
    m = re.search(r"最后更新：([0-9]{4}-[0-9]{2}-[0-9]{2})", text)
    if m:
        last = m.group(1)
    return snap, last


def applications_md_mtime_date():
    """applications.md 最后修改日期（用于和 README 快照日期对比）。"""
    if not os.path.isfile(APPS_MD):
        return None
    ts = os.path.getmtime(APPS_MD)
    return datetime.date.fromtimestamp(ts).isoformat()


def main():
    print("=" * 60)
    print("  投递文档一致性体检 · sync_check.py")
    print("=" * 60)

    file_ids, file_detail = app_ids_from_filenames()
    md_ids = app_ids_from_applications_md()
    snap_date, last_date = readme_dates()
    apps_mtime = applications_md_mtime_date()

    # ---- 检查 1：简历文件 vs applications.md ----
    print(f"\n[1] 简历文件 ↔ applications.md")
    print(f"    applications/ 目录中检出 {len(file_ids)} 个 APP 编号")
    print(f"    applications.md 中检出 {len(md_ids)} 个 APP 行")

    missing_in_md = sorted(file_ids - md_ids)
    if missing_in_md:
        for n in missing_in_md:
            problems.append(
                f"APP-{n:03d} 有简历文件但 applications.md 无对应行 "
                f"（文件：{', '.join(file_detail.get(n, []))}）"
            )
    missing_files = sorted(md_ids - file_ids)
    if missing_files:
        # md 有行但无文件 —— 可能是 Skipped/Closed 未生成简历，属正常，仅提醒
        for n in missing_files:
            warnings.append(
                f"APP-{n:03d} 在 applications.md 有行但 applications/ 无简历文件 "
                f"（若为 Skipped/Closed 未生成简历则正常）"
            )

    # ---- 检查 2：README 日期新鲜度 ----
    print(f"\n[2] README 日期新鲜度")
    print(f"    第三节快照日期：{snap_date or '未找到'}")
    print(f"    末尾最后更新：  {last_date or '未找到'}")
    print(f"    applications.md 磁盘修改日：{apps_mtime or '未知'}")

    if snap_date and apps_mtime and snap_date < apps_mtime:
        # mtime 对任何编辑都敏感（含纯格式调整），故仅作提醒，不阻断
        warnings.append(
            f"README 第三节快照日期（{snap_date}）早于 applications.md 磁盘修改日"
            f"（{apps_mtime}）—— 若 applications.md 近期有内容变更，请确认第三节快照已同步刷新"
        )
    if snap_date and last_date and snap_date != last_date:
        warnings.append(
            f"README 第三节快照日期（{snap_date}）与末尾最后更新（{last_date}）不一致"
        )

    # ---- 检查 3：README 文件结构图是否覆盖最新 APP ----
    print(f"\n[3] README 文件结构图覆盖度")
    if os.path.isfile(README_MD) and file_ids:
        readme_text = open(README_MD, encoding="utf-8").read()
        max_app = max(file_ids)
        if f"APP{max_app:03d}" in readme_text or f"APP-{max_app:03d}" in readme_text:
            print(f"    最新 APP-{max_app:03d} 已在 README 中提及 ✓")
        else:
            warnings.append(
                f"最新简历 APP-{max_app:03d} 未在 README 文件结构图中出现 —— 建议补充"
            )

    # ---- 汇总 ----
    print("\n" + "=" * 60)
    if not problems and not warnings:
        print("  ✅ 全部一致，无漂移")
        print("=" * 60)
        return 0

    if problems:
        print(f"  ❌ 阻断级问题 {len(problems)} 项：")
        for p in problems:
            print(f"     - {p}")
    if warnings:
        print(f"  ⚠️  提醒级 {len(warnings)} 项：")
        for w in warnings:
            print(f"     - {w}")
    print("=" * 60)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
