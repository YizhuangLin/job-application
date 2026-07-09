#!/usr/bin/env python3
"""
build.py — JD 驱动的简历 + Cover Letter 生成系统
================================================================
母版 YAML 化架构（2026-05-22）：
  母版 = master_resume.yaml（结构化内容）
  排版 = resume_render.py（代码生成 docx）
  不再解包 docx、不再做 XML 字符串替换。

子命令：
  prep             读 JD + master_resume.yaml → 生成 jobs/APP###.yaml 草稿 + applications.md 占位行
  verify           检查阶段2 完整性 + 核对状态
  factcheck-pass   用户完成 factcheck 裁决后，锁定 APP###.yaml 的 review_status.factcheck = PASS
  qualreview-pass  qualreview agent 跑完后，把 4 级评级 + 期待句写进 yaml + applications.md
  make             读填好的 jobs/APP###.yaml → 代码生成简历+CL 的 docx/pdf（默认只留 PDF）
  review           投递前总闸：核对/版式/质量 三检查

2026-05-26 改造：factcheck / qualreview 不再写独立 .md 文件，状态全部存 yaml + applications.md
              ↳ factcheck 报告 inline 显示给用户裁决 → Claude 执行裁决 → factcheck-pass 锁定
              ↳ qualreview agent 返回 4 级评级 + 期待句 → qualreview-pass 写两处
详见 auto-apply/jobs/_schema.md。
"""
import os
import re
import sys
import glob
import html
import shutil
import hashlib
import argparse
import subprocess
import tempfile
import datetime

try:
    import yaml
except ImportError:
    sys.exit("缺少 pyyaml，请先 pip install pyyaml --break-system-packages")

SCHEMA_VERSION = 2   # v2：母版 YAML 化，experience 列表结构

# 引擎版本。发版流程：与发布仓 SKILL.md frontmatter version + CHANGELOG 同步 bump。
# check-update 用它与上游最新版本对比。
ENGINE_VERSION = "1.1.0"


# ============================================================
# 路径定位 —— 全部动态，无会话 ID 硬编码
# ============================================================

def find_repo_root():
    """定位工作区根目录。

    2026-07-07 起支持可复制工作区：
      1. 若设了环境变量 RESUME_WORKSPACE，直接用它（跳过目录探测）——
         用于 build.py 本体和目标工作区不在同一仓库的场景（如某个新工作区没有
         自己的 build.py，复用本仓库的引擎但指向别处的根）。
      2. 逐级向上找 workspace.yaml —— 这是工作区配置层的标志文件，
         找到即视为仓库根（不要求 workspace.yaml 内容非空）。
    （2026-07-07 发布阶段删除了「applications.md + 历史 SSOT 文件名」的双文件回退判据 ——
    所有工作区已有 workspace.yaml，回退路径是死代码且含维护者个人文件名。）
    """
    env_root = os.environ.get("RESUME_WORKSPACE")
    if env_root:
        env_root = os.path.abspath(env_root)
        if not os.path.isdir(env_root):
            sys.exit(f"RESUME_WORKSPACE 指向的目录不存在：{env_root}")
        return env_root

    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isfile(os.path.join(d, "workspace.yaml")):
            return d
        d = os.path.dirname(d)
    sys.exit("无法定位仓库根（需在工作区根放 workspace.yaml —— 新工作区跑 build.py init 生成；"
             "也可设 RESUME_WORKSPACE 环境变量显式指定）")


def check_deps():
    """2026-05-26 起 make 不再依赖 docx skill（soffice）—— 由 RR API 渲染 PDF。
    仍需 pdfinfo + pdftotext（poppler-utils）做版式检查（页数/字符/正文提取）。
    2026-07-07 补：layout_check_* 裸调 pdftotext，缺失会直接崩，故补进必需依赖检查。"""
    missing = [t for t in ("pdfinfo", "pdftotext") if shutil.which(t) is None]
    if missing:
        sys.exit(f"缺少系统依赖：{', '.join(missing)}")


def _load_paths_config(repo_root):
    """读 workspace.yaml 的 paths 段（模块加载时解析一次）。
    文件不存在/无 paths 段/解析失败 —— 一律回退通用默认值（Context_Master.md /
    applications.md）。任何在 workspace.yaml 里显式配置了 paths.ssot 的旧工作区
    （如维护者本人工作区，指向历史文件名）不受此默认值改动影响——
    workspace.yaml 里的显式值优先于此处默认值。"""
    defaults = {"ssot": "Context_Master.md", "applications": "applications.md"}
    path = os.path.join(repo_root, "workspace.yaml")
    if not os.path.isfile(path):
        return defaults
    try:
        cfg = yaml.safe_load(open(path, encoding="utf-8")) or {}
    except Exception:
        return defaults
    return {**defaults, **(cfg.get("paths") or {})}


REPO_ROOT     = find_repo_root()
_PATHS_CFG    = _load_paths_config(REPO_ROOT)
MASTER_YAML   = os.path.join(REPO_ROOT, "master_resume.yaml")
APPS_MD       = os.path.join(REPO_ROOT, _PATHS_CFG["applications"])
SSOT          = os.path.join(REPO_ROOT, _PATHS_CFG["ssot"])
JOBS_DIR      = os.path.join(REPO_ROOT, "auto-apply", "jobs")
OUT_DIR       = os.path.join(REPO_ROOT, "auto-apply", "applications")

# 2026-05-27：渲染层从 Reactive Resume API 切到本地 HTML + Playwright（方案 2）。
# 顶部不再 import 渲染层 —— cmd_make 在调用前动态 import html_render / docx_render，
# 避免任一渲染层依赖缺失时 build.py 启动崩溃（如 playwright 未装时 verify / review 仍可跑）。
# RR 路径见 _archive/2026-05-27_rr_attempt/（Step 7.1 归档）；旧 docx 路径见 _archive/2026-05-26_pre_rr_render/。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ============================================================
# 公共工具
# ============================================================

def load_workspace_config():
    """读工作区配置 workspace.yaml（2026-07-07 起的配置层）。
    文件不存在或字段缺失时用默认值 —— 引擎必须在裸工作区也能跑。
    fact_redlines / strategy_rules 是核对/质检 prompt 的工作区专属注入段
    （build.py prompt 渲染时替换 {{FACT_REDLINES}} / {{STRATEGY_RULES}} 占位符），
    缺失时为空列表 —— 渲染层负责给出「未配置」的提示文案。

    2026-07-08 新增 paths.rewrite_library：已核对片段库文件路径（相对仓库根），
    默认值 "rewrite_library.yaml"（工作区根，与 master_resume.yaml 同级）。"""
    defaults = {"resume_layout": {"max_pages": 1, "overflow_strategy": "cut_content"},
                "fact_redlines": [], "strategy_rules": [], "lint_patterns": [],
                "paths": {"rewrite_library": "rewrite_library.yaml"}}
    path = os.path.join(REPO_ROOT, "workspace.yaml")
    if not os.path.isfile(path):
        return defaults
    try:
        cfg = yaml.safe_load(open(path, encoding="utf-8")) or {}
    except Exception:
        return defaults
    rl = {**defaults["resume_layout"], **(cfg.get("resume_layout") or {})}
    paths = {**defaults["paths"], **(cfg.get("paths") or {})}
    return {"resume_layout": rl,
            "fact_redlines": [str(s) for s in (cfg.get("fact_redlines") or [])],
            "strategy_rules": [str(s) for s in (cfg.get("strategy_rules") or [])],
            "lint_patterns": [str(s) for s in (cfg.get("lint_patterns") or [])],
            "paths": paths}


def rewrite_library_path():
    """已核对片段库文件的绝对路径，从 workspace.yaml paths.rewrite_library 派生。"""
    rel = load_workspace_config()["paths"]["rewrite_library"]
    return os.path.join(REPO_ROOT, rel)


def pdf_pages(pdf_path):
    if not os.path.isfile(pdf_path):
        return None
    info = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True).stdout
    m = re.search(r'Pages:\s+(\d+)', info)
    return int(m.group(1)) if m else None


def render_docx(*args, **kwargs):
    """已退役。原实现：从嵌入骨架打包 docx → LibreOffice 转 PDF。
    2026-05-26 起渲染走 Reactive Resume API（rr_render.py），此函数仅作为占位保留签名。
    原实现见 _archive/2026-05-26_pre_rr_render/resume_render.py + docx_skeleton_embedded.py。
    """
    raise NotImplementedError(
        "render_docx 已退役 —— 2026-05-26 起渲染走 Reactive Resume API。"
        "如需复用旧路径，从 _archive/2026-05-26_pre_rr_render/ 恢复"
    )


# ============================================================
# applications.md 编号 + 占位行
# ============================================================

def existing_app_numbers():
    if not os.path.isfile(APPS_MD):
        return set()
    text = open(APPS_MD, encoding="utf-8").read()
    return {int(m) for m in re.findall(r'\bAPP-(\d{1,4})\b', text)}


def next_app_id():
    nums = existing_app_numbers()
    return f"APP-{(max(nums) + 1) if nums else 1:03d}"


def _table_columns(text):
    """解析 applications.md Active 表头，返回列名→cell索引 映射（含首尾空串列）。"""
    for ln in text.split('\n'):
        if ln.lstrip().startswith("| APP ") or ln.lstrip().startswith("| APP|"):
            cells = ln.split('|')
            return {c.strip(): i for i, c in enumerate(cells)}
    return None


def add_placeholder_row(app_id, company, role):
    """在 applications.md Active 表末尾追加占位行。返回是否新增。
    按表头列名动态填值，不硬编码列数（适应表结构变化）。"""
    text = open(APPS_MD, encoding="utf-8").read()
    if re.search(rf'\|\s*{re.escape(app_id)}\s*\|', text):
        return False
    cols = _table_columns(text)
    if cols:
        # cols: {列名: cell索引}，含首尾空串。按索引顺序填。
        n_cells = max(cols.values()) + 1
        cells = [""] * n_cells
        preset = {"APP": app_id, "Company": company, "Role": role,
                  "Stage": "Drafting", "Notes": "build.py prep 占位行，待 make 生成简历"}
        for name, idx in cols.items():
            if 0 < idx < n_cells - 1:   # 跳过首尾空串列
                cells[idx] = f" {preset.get(name, '—')} "
        row = "|".join(cells)
    else:
        # 兜底：表头解析失败用旧的 13 段固定格式
        row = (f"| {app_id} | {company} | {role} | — | — | — | Drafting | — | — | — | — "
               f"| build.py prep 占位行，待 make 生成简历 |")
    lines = text.split('\n')
    closed_ln = next((i for i, ln in enumerate(lines)
                      if ln.startswith("## Closed / Skipped")), None)
    if closed_ln is None:
        sys.exit("applications.md 找不到 '## Closed / Skipped'，结构异常")
    last_active = None
    for i in range(closed_ln):
        if lines[i].lstrip().startswith("| APP-"):
            last_active = i
    if last_active is None:
        # 空表兜底（全新工作区第一次 prep）：Active 表还没有任何数据行，
        # 插在表头分隔行（"|---|---|..."）之后而不是报错——新工作区第一次
        # 调 prep 是正常场景，不应因为"表是空的"就拒绝写入。
        header_ln = next((i for i, ln in enumerate(lines[:closed_ln])
                          if ln.lstrip().startswith("| APP")), None)
        if header_ln is None or header_ln + 1 >= closed_ln:
            sys.exit("applications.md Active 表结构异常（找不到表头或分隔行）")
        last_active = header_ln + 1   # 表头下一行是分隔行，插在它之后
    lines.insert(last_active + 1, row)
    with open(APPS_MD, "w", encoding="utf-8") as f:
        f.write('\n'.join(lines))
    return True


def fill_resume_file(app_id, resume_filename):
    """make 成功后把占位行的 Resume File 列填上文件名。按列名定位（修复⑥）。"""
    text = open(APPS_MD, encoding="utf-8").read()
    cols = _table_columns(text)
    lines = text.split('\n')
    for i, ln in enumerate(lines):
        if re.match(rf'\|\s*{re.escape(app_id)}\s*\|', ln):
            cells = ln.split('|')
            idx = cols.get("Resume File") if cols else None
            if idx is None or idx >= len(cells):
                idx = 11  # 兜底：旧硬编码索引
            if idx < len(cells):
                cells[idx] = f" {resume_filename} "
                lines[i] = '|'.join(cells)
                with open(APPS_MD, "w", encoding="utf-8") as f:
                    f.write('\n'.join(lines))
                return True
    return False


# ============================================================
# JD 抓取 + 轻量抽取
# ============================================================

def fetch_jd(jd_url, jd_file):
    if jd_file:
        if not os.path.isfile(jd_file):
            sys.exit(f"JD 文件不存在：{jd_file}")
        return "pasted", open(jd_file, encoding="utf-8").read()
    if jd_url:
        try:
            import urllib.request
            req = urllib.request.Request(jd_url, headers={"User-Agent": "Mozilla/5.0"})
            html_raw = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
            text = re.sub(r'<script.*?</script>', ' ', html_raw, flags=re.S)
            text = re.sub(r'<style.*?</style>', ' ', text, flags=re.S)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) < 400:
                print("⚠️  JD URL 抓取内容过短（可能是 JS 渲染站）。建议改用 --jd-file 粘贴。")
            return jd_url, text
        except Exception as e:
            print(f"⚠️  JD URL 抓取失败：{e} —— 建议改用 --jd-file 粘贴 JD 全文。")
            return jd_url, ""
    return "pasted", ""


def light_extract(jd_text):
    """正则轻量抽取薪资/地点/合同性质。抽不到留空。"""
    salary = ""
    for pat in (r'\$\s?\d{1,3}(?:,\d{3})+\s?[-–]\s?\$?\s?\d{1,3}(?:,\d{3})+',
                r'\$?\s?\d{2,3}\s?[kK]\s?[-–]\s?\$?\s?\d{2,3}\s?[kK]',
                r'\$\s?\d{1,3}(?:,\d{3})+'):
        m = re.search(pat, jd_text)
        if m:
            salary = m.group(0).strip()
            break
    location = ""
    for kw in ("Remote", "remote", "Hybrid", "hybrid", "Ottawa", "Toronto",
               "Mississauga", "in-person", "on-site", "onsite"):
        if kw in jd_text:
            location = kw
            break
    contract = ""
    low = jd_text.lower()
    if "part-time" in low or "part time" in low:
        contract = "part-time"
    elif re.search(r'\b\d+[\s-]?(month|year)', low) or "contract" in low or "fixed-term" in low:
        contract = "contract"
    elif "permanent" in low or "full-time" in low or "full time" in low:
        contract = "permanent"
    return salary, location, contract


# ============================================================
# 子命令：prep
# ============================================================

def load_master():
    """读 master_resume.yaml，校验 schema_version + 结构断言。
    母版被误改/缺字段时立即报错，不让残缺数据流进下游。"""
    if not os.path.isfile(MASTER_YAML):
        sys.exit(f"母版不存在：{MASTER_YAML}")
    m = yaml.safe_load(open(MASTER_YAML, encoding="utf-8"))
    if m.get("schema_version") != SCHEMA_VERSION:
        sys.exit(f"master_resume.yaml schema_version={m.get('schema_version')}，"
                 f"当前 build.py 支持 {SCHEMA_VERSION}")
    # 结构断言
    errs = []
    if not (m.get("contact", {}).get("name") and m.get("contact", {}).get("line")):
        errs.append("contact 段缺 name/line")
    if not (m.get("summary") or "").strip():
        errs.append("summary 段为空")
    exps = m.get("experience") or []
    if not exps:
        errs.append("experience 段为空")
    for i, e in enumerate(exps):
        miss = [k for k in ("id", "title", "date", "org_line", "bullets") if not e.get(k)]
        if miss:
            errs.append(f"experience[{i}] 缺字段 {miss}")
    if not (m.get("education") or []):
        errs.append("education 段为空")
    sk = m.get("skills") or []
    if not sk:
        errs.append("skills 段为空")
    for i, s in enumerate(sk):
        if not (s.get("label") and s.get("body")):
            errs.append(f"skills[{i}] 缺 label/body")
    if errs:
        msg = "\n".join(f"  ✗ {e}" for e in errs)
        sys.exit(f"[FAIL] master_resume.yaml 结构断言未通过 —— 母版可能被误改：\n{msg}")
    return m


def cmd_prep(args):
    check_deps()
    os.makedirs(JOBS_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    reuse = getattr(args, "reuse", False)
    if args.app:
        app_id = normalize_app_id(args.app)
        exists = int(re.search(r'\d+', app_id).group()) in existing_app_numbers()
        if exists and not reuse:
            sys.exit(f"{app_id} 已存在于 applications.md。"
                     f"\n  · 已有岗位重新生成 → 加 --reuse"
                     f"\n  · 新岗位 → 换编号或不传 --app（自动 max+1）")
    else:
        app_id = next_app_id()

    source, jd_text = fetch_jd(args.jd_url, args.jd_file)
    salary, location, contract = light_extract(jd_text)

    master = load_master()
    today = datetime.date.today().isoformat()
    cl_date = datetime.date.today().strftime("%B ") + str(datetime.date.today().day) \
              + datetime.date.today().strftime(", %Y")

    # APP###.yaml v2 结构：experience 列表，每段 id + bullets[{master,rewritten}]
    data = {
        "schema_version": SCHEMA_VERSION,
        "app_id": app_id,
        "company": args.company,
        "role": args.role,
        "created": today,
        "stage": "Drafting",
        "jd": {"source": source, "raw_text": jd_text, "salary": salary,
               "location": location, "contract_type": contract, "jd_summary": ""},
        "resume": {
            "summary": {"master": master["summary"], "rewritten": ""},
            "experience": [
                {"id": e["id"], "title": e["title"], "date": e["date"],
                 "org_line": e["org_line"],
                 "bullets": [{"master": b, "rewritten": ""} for b in e["bullets"]]}
                for e in master["experience"]
            ],
            "education": master["education"],   # 教育不改写，原样带（生成时直接用）
            "skills": [
                {"label": s["label"], "role": s.get("role", ""),
                 "master": s["body"], "rewritten": ""}
                for s in master["skills"]
            ],
            "bilingual_line": {
                "present_in_master": bool(master.get("meta", {}).get("bilingual_sentence")),
                "keep": True,
            },
        },
        "cover_letter": {
            "date": cl_date, "recipient_company": args.company, "re_line": args.role,
            "salutation": "Dear Hiring Team,", "body_paragraphs": [""],
            "closing": "Sincerely,",
            "signature": display_name_from_contact(master.get("contact")) or master.get("contact", {}).get("name", ""),
        },
        # 压页 steplist = 超页时的内容缩减优先级（供 Claude 阶段2/回炉时参考执行）。
        # 2026-07-07 起只含内容手段 —— 排版类 step（缩标题间距/行距）已废除：
        # 超页只减内容，不缩排版（见 workspace.yaml resume_layout.overflow_strategy）。
        "page_compression": {
            "steplist": [
                {"id": "drop_oldest_bullet", "order": 1},
                {"id": "languages_line", "order": 2},
                {"id": "bilingual_line", "order": 99},
            ],
        },
        "provenance": [],
        "locked_facts": {"numeric": []},
    }

    yaml_path = os.path.join(JOBS_DIR, f"{app_id}.yaml")

    # 防覆盖保护
    if os.path.isfile(yaml_path) and not getattr(args, "force", False):
        try:
            existing = yaml.safe_load(open(yaml_path, encoding="utf-8"))
        except Exception:
            existing = None
        if existing:
            er = existing.get("resume", {})
            filled = (
                (er.get("summary", {}).get("rewritten") or "").strip()
                or any((s.get("rewritten") or "").strip() for s in er.get("skills", []))
                or any((b.get("rewritten") or "").strip()
                       for e in er.get("experience", []) for b in e.get("bullets", []))
                or any(p and p.strip()
                       for p in existing.get("cover_letter", {}).get("body_paragraphs", []))
            )
            if filled:
                sys.exit(f"[BLOCKED] {yaml_path} 已存在且阶段2 已填写内容。"
                         f"\n  prep 默认拒绝覆盖。确实要重来 → 加 --force（丢失已填内容）")

    ssot_name = os.path.basename(SSOT)
    header = (
        "# ============================================================\n"
        f"# {app_id} 数据文件 · 阶段2 由 Claude 填写\n"
        f"# 简历策略强制规则（SSOT {ssot_name} 第二节）：\n"
        "#   1. resume.summary 不写年限数字，成果/角色导向开头\n"
        "#   2. 货币一律 CAD，金额不进 summary\n"
        "#   3. bilingual_line.keep: JD 要求/偏好中文→true；未提及→false\n"
        "#   4. JD 薪资<$60K 或小雇主 → Target Social bullet 删 11M+ CAD 金额（保留超越 Sienna 叙事）\n"
        "#   rewritten 留空 = 沿用 master 原文。详见 jobs/_schema.md\n"
        "# ============================================================\n"
    )
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(header)
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=100)

    row_added = add_placeholder_row(app_id, args.company, args.role)

    nb = [len(e["bullets"]) for e in master["experience"]]
    print(f"[OK] prep 完成")
    print(f"  数据文件：auto-apply/jobs/{app_id}.yaml")
    print(f"  applications.md：{'已加 ' + app_id + ' 占位行' if row_added else app_id + ' 行已存在（--reuse）'}")
    print(f"  母版载入：summary + {len(master['skills'])} 技能行 + experience {len(master['experience'])} 段 bullets{nb}")
    print(f"  JD 抽取：salary={salary or '—'} location={location or '—'} contract={contract or '—'}")
    print(f"\n  下一步：阶段2 Claude 读 {app_id}.yaml + SSOT，填 rewritten / cover_letter / provenance / locked_facts")


# ============================================================
# 内容组装：APP###.yaml → resume_render 用的 content dict
# ============================================================

def assemble_content(data, drop_bullets=None, drop_languages=False, drop_bilingual=False):
    """从 APP###.yaml 的 resume 段组装 content dict（每段取 rewritten or master）。
    drop_bullets: {exp_id: 要删的 bullet 数（从尾部）} —— 压页用
    drop_languages: 剔除 skills 里 role=languages 的行
    drop_bilingual: 从 summary 移除 bilingual 句
    """
    r = data["resume"]
    master = load_master()
    bilingual_sentence = master.get("meta", {}).get("bilingual_sentence", "")

    summary = (r["summary"].get("rewritten") or "").strip() or r["summary"]["master"]
    if drop_bilingual and bilingual_sentence and bilingual_sentence in summary:
        summary = summary.replace(bilingual_sentence, "").strip()
        summary = re.sub(r'\s{2,}', ' ', summary)

    experience = []
    for e in r["experience"]:
        bullets = [(b.get("rewritten") or "").strip() or b["master"] for b in e["bullets"]]
        nd = (drop_bullets or {}).get(e["id"], 0)
        if nd > 0:
            bullets = bullets[:len(bullets) - nd] if nd < len(bullets) else []
        experience.append({"title": e["title"], "date": e["date"],
                            "org_line": e["org_line"], "bullets": bullets})

    skills = []
    for s in r["skills"]:
        if drop_languages and s.get("role") == "languages":
            continue
        body = (s.get("rewritten") or "").strip() or s["master"]
        skills.append({"label": s["label"], "body": body})

    return {
        "contact": master["contact"],   # 联系信息固定取母版（含地址；地址定制见 schema）
        "summary": summary,
        "experience": experience,
        "education": r["education"],
        "skills": skills,
    }


# ============================================================
# 子命令：make
# ============================================================

def slugify(s):
    return re.sub(r'[^A-Za-z0-9]+', '', s.title())


def display_name_from_contact(contact):
    """从 master contact.name 派生一个人类惯用的签名/展示姓名。
    contact.name 常用于简历头部，可能全大写或含括号昵称（如 "FIRSTNAME (NICK) LASTNAME"）——
    cover letter 签名等场合需要更自然的形式（如 "Nick Lastname"）。
    规则：括号内容优先作为名字（视为昵称/惯用名），其余词 Title Case。
    取不到 contact/name 时返回空串，调用方应自行兜底。"""
    name = (contact or {}).get("name") or ""
    if not name:
        return ""
    m = re.search(r'\(([^)]+)\)', name)
    nickname = m.group(1).strip() if m else None
    rest = re.sub(r'\([^)]*\)', ' ', name)
    words = [w for w in rest.split() if w]
    if nickname and words:
        # 用昵称替换紧邻括号前的那个词（通常是全名的对应部分），其余词保留顺序
        # 简化处理：昵称作名，最后一个词作姓（常见英文姓名序）
        surname = words[-1].title() if len(words) > 1 else ""
        return f"{nickname.title()} {surname}".strip()
    return " ".join(w.title() for w in words)


def normalize_app_id(s):
    return s if s.startswith("APP-") else f"APP-{int(s.replace('APP','').strip('-')):03d}"


def factcheck_result(app_id):
    """读 APP###.yaml 的 review_status.factcheck 字段，返回核对状态。
    2026-05-26 改造：状态从独立 .md 文件改成 yaml 字段。

    实际只有两态：
      "PASS"   —— factcheck-pass 已锁定，所有裁决执行完，可进 make
      None     —— 未锁定 PASS（factcheck 还没跑 / 跑了但 Claude/用户还没完成裁决执行）

    Note: 当前 build.py 只有 factcheck-pass 一个写入 result 字段的入口，且只写 PASS。
    "未锁定" 状态没有专用值 —— yaml 里要么没 review_status.factcheck 子树，要么有但 result != "PASS"。
    两种都映射成 None（语义：还没锁定 PASS）。
    如果未来加更细的中间态（FAIL/NEEDS-USER），可扩展此函数。
    """
    yp = os.path.join(JOBS_DIR, f"{app_id}.yaml")
    if not os.path.isfile(yp):
        return None
    try:
        data = yaml.safe_load(open(yp, encoding="utf-8")) or {}
    except Exception:
        return None
    rs = (data.get("review_status") or {}).get("factcheck") or {}
    if rs.get("result") == "PASS":
        return "PASS"
    return None


def factcheck_hash_check(data):
    """校验 factcheck PASS 时锁定的 content_hash 是否与当前内容一致（防止 PASS 后又被改动）。
    返回 (status, message)：
      status = "ok"       —— 哈希一致 / 或无哈希可比（旧版锁定，视为不阻断，仅提示）
      status = "mismatch" —— 哈希不一致，内容在锁定后被修改
      status = "no_hash"  —— 旧版 PASS 记录，没有 content_hash 字段（向后兼容，只警告不阻断）
    """
    rs = (data.get("review_status") or {}).get("factcheck") or {}
    if rs.get("result") != "PASS":
        return "not_passed", None
    locked_hash = rs.get("content_hash")
    if not locked_hash:
        return "no_hash", "旧版锁定，无内容哈希，建议投递前重跑核对"
    cur_hash = content_hash(data)
    if cur_hash != locked_hash:
        return "mismatch", "内容在核对锁定后被修改，需重新核对"
    return "ok", None


def cmd_verify(args):
    app_id = normalize_app_id(args.app)
    yaml_path = os.path.join(JOBS_DIR, f"{app_id}.yaml")
    if not os.path.isfile(yaml_path):
        sys.exit(f"数据文件不存在：{yaml_path}")
    data = yaml.safe_load(open(yaml_path, encoding="utf-8"))
    _legacy_or_missing_resume_guard(app_id, data, "verify")

    print(f"== verify {app_id} ==")
    # 阶段2 完整性
    r = data["resume"]
    issues = []
    has_rw = ((r["summary"].get("rewritten") or "").strip()
              or any((s.get("rewritten") or "").strip() for s in r["skills"])
              or any((b.get("rewritten") or "").strip()
                     for e in r["experience"] for b in e["bullets"]))
    if not has_rw:
        issues.append("所有 rewritten 为空 —— 阶段2 未填，简历会原样用母版")
    if not data["jd"].get("jd_summary", "").strip():
        issues.append("jd.jd_summary 为空")
    if not [p for p in data["cover_letter"].get("body_paragraphs", []) if p and p.strip()]:
        issues.append("cover_letter.body_paragraphs 为空 —— CL 不会生成")
    if has_rw and not data.get("provenance"):
        issues.append("有 rewritten 但 provenance 为空 —— 核对 agent 需要对照面")
    if issues:
        print("  阶段2 检查：")
        for i in issues:
            print(f"     ⚠ {i}")
    else:
        print("  阶段2 检查：均已填 ✓")

    result = factcheck_result(app_id)
    print()
    if result == "PASS":
        print(f"  核对状态：PASS ✓ —— 下一步 build.py make --app {app_id}")
        sys.exit(0)
    else:  # None —— 未锁定 PASS
        print(f"  核对状态：未锁定 PASS")
        print(f"    → 派核对 agent（按 jobs/_verifier_prompt.md），agent 返回报告 inline")
        print(f"    → Claude 把报告贴给用户看，用户逐条裁决（仅 NEEDS-USER 时）")
        print(f"    → Claude 执行裁决（删/留/补 SSOT）")
        print(f"    → Claude 跑 build.py factcheck-pass --app {app_id} 锁定 PASS")
        sys.exit(2)


def cmd_make(args):
    """2026-05-27 起渲染层切到本地 HTML + Playwright（Step 5a 整体重写中）。
    旧 RR API 路径已废弃；旧 docx 路径见 _archive/2026-05-26_pre_rr_render/。

    流程（Step 5a 实现后）：
      1. 校验 schema + factcheck PASS
      2. assemble_content() → content dict
      3. html_render.render_resume(content) + html_render.render_cl(content, cl)
      4. docx_render.render_resume(content)
      5. 写 applications.md Resume File 字段
      6. 版式检查 + locked_facts 粗筛
      7. 报告 + 投递前必做提示
    """
    # 2026-07-06：Step 5a 收尾 —— cmd_make 接到本地 html_render（Playwright→WeasyPrint 回退）
    # + docx_render（--docx）。旧 rr_render 路径已退役。
    check_deps()
    app_id = normalize_app_id(args.app)
    yaml_path = os.path.join(JOBS_DIR, f"{app_id}.yaml")
    if not os.path.isfile(yaml_path):
        sys.exit(f"数据文件不存在：{yaml_path}（先跑 build.py prep）")

    data = yaml.safe_load(open(yaml_path, encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        sys.exit(f"schema_version={data.get('schema_version')}，当前支持 {SCHEMA_VERSION}，"
                 f"旧版数据文件需重新 prep")
    _legacy_or_missing_resume_guard(app_id, data, "make")

    skip_verify = getattr(args, "skip_verify", False)
    if not skip_verify:
        fc = factcheck_result(app_id)
        if fc != "PASS":
            sys.exit(f"[BLOCKED] factcheck 未锁定 PASS — 不允许 make。"
                     f"\n  → 先 build.py verify --app {app_id} 并派核对 agent，"
                     f"\n    完成裁决执行后 build.py factcheck-pass --app {app_id}"
                     f"\n  （测试可加 --skip-verify，但正式投递前必须 PASS）")
        hash_status, hash_msg = factcheck_hash_check(data)
        if hash_status == "mismatch":
            sys.exit(f"[BLOCKED] factcheck content_hash 不一致 —— {hash_msg}"
                     f"\n  → 重新派核对 agent，跑 build.py factcheck-pass --app {app_id} 重新锁定")
        elif hash_status == "no_hash":
            print(f"  ⚠ {hash_msg}")

    # 读 master_resume.yaml（rr_render 用它构造 patch ops + 删 bilingual 句）
    if not os.path.isfile(MASTER_YAML):
        sys.exit(f"母版 yaml 不存在：{MASTER_YAML}")
    master_yaml = yaml.safe_load(open(MASTER_YAML, encoding="utf-8")) or {}

    company_slug = slugify(data["company"])
    role_slug    = slugify(data["role"])
    date_str     = datetime.date.today().isoformat()
    label        = f"{app_id.replace('-', '')}_{company_slug}_{role_slug}_{date_str}"
    cl_label     = f"{app_id.replace('-', '')}_{company_slug}_CoverLetter_{date_str}"
    unverified   = "_UNVERIFIED" if skip_verify else ""   # 修复⑤：skip 产物打污点

    bl = data["resume"]["bilingual_line"]
    keep_bilingual = bl.get("keep", True)

    # ---- dry-run：报告 yaml 内容统计，不调 RR ----
    if getattr(args, "dry_run", False):
        print(f"== make --dry-run {app_id} ==")
        r = data["resume"]
        n_rw = sum(1 for s in [r["summary"]] if (s.get("rewritten") or "").strip())
        n_rw += sum(1 for s in r["skills"] if (s.get("rewritten") or "").strip())
        n_rw += sum(1 for e in r["experience"] for b in e["bullets"]
                    if (b.get("rewritten") or "").strip())
        cl_n = len([p for p in data["cover_letter"]["body_paragraphs"] if p and p.strip()])
        print(f"  改写段数：{n_rw}（summary/skills/bullets 中已填 rewritten 的）")
        print(f"  cover letter 正文段：{cl_n}")
        print(f"  bilingual keep：{keep_bilingual}")
        print(f"  渲染器：本地 html_render（Playwright→WeasyPrint 回退）+ docx_render（--docx）")
        print("  数据校验通过 ✓ —— 可正式 make。")
        sys.exit(0)

    # ---- 1. 本地渲染：assemble_content → html_render（PDF）+ 可选 docx_render ----
    import html_render
    pdf_path    = os.path.join(OUT_DIR, f"{label}{unverified}.pdf")
    cl_pdf_path = os.path.join(OUT_DIR, f"{cl_label}{unverified}.pdf")

    print(f"== make {app_id} —— 本地 HTML 渲染（Playwright→WeasyPrint 回退）==")
    print(f"  bilingual keep：{keep_bilingual}")
    if not keep_bilingual:
        print(f"  ✓ bilingual=false：summary 删 bilingual 句 + languages section 隐藏")

    content = assemble_content(
        data,
        drop_bilingual=(not keep_bilingual),
        drop_languages=(not keep_bilingual),
    )
    cl_data = data["cover_letter"]

    try:
        html_render.render_resume(content, pdf_path)
        html_render.render_cl(content, cl_data, cl_pdf_path)
    except Exception as e:
        sys.exit(f"[FAIL] HTML/PDF 渲染异常：{type(e).__name__}: {e}")

    if getattr(args, "docx", False):
        import docx_render
        docx_path    = os.path.join(OUT_DIR, f"{label}{unverified}.docx")
        cl_docx_path = os.path.join(OUT_DIR, f"{cl_label}{unverified}.docx")
        try:
            docx_render.render_resume(content, docx_path)
            docx_render.render_cl(content, cl_data, cl_docx_path)
            print(f"  ✓ docx 同时生成：{label}{unverified}.docx + CL")
        except Exception as e:
            print(f"  ⚠ docx 渲染失败（PDF 已出）：{type(e).__name__}: {e}")

    pages    = pdf_pages(pdf_path)
    cl_pages = pdf_pages(cl_pdf_path)

    # ---- 2. 页数硬约束（上限来自 workspace.yaml，默认 1 页；严格按 PDF 实际页数，不忽略空白页） ----
    # 视觉上多一页就是多一页 —— HR 打开 PDF 看到 2 页就是 2 页（即使第 2 页空白）。
    # 超页处理策略 = cut_content：只允许缩减内容（按 page_compression.steplist 优先级
    # 从低价值内容删起：最早经历的末位 bullet → Languages 行 → 末位 bilingual 句）。
    # ⛔ 禁止缩小字号/行距/边距换页数 —— 排版换来的一页比删一条弱 bullet 更伤简历。
    max_pages = load_workspace_config()["resume_layout"]["max_pages"]
    if pages and pages > max_pages:
        print(f"[FAIL] 简历 {pages} 页（上限 {max_pages} 页，workspace.yaml resume_layout.max_pages）")
        print(f"  → 超页只允许缩减内容：回阶段2 精简 rewritten / 按 steplist 删低价值 bullet 后重 make。")
        print(f"  ⛔ 不要用缩小字号、行距、边距等排版手段压页。")
        sys.exit(1)
    if cl_pages and cl_pages > 1:
        print(f"  ⚠ Cover letter {cl_pages} 页 —— 建议精简 cover_letter.body_paragraphs 或调 Master margin")

    # ---- 3. locked_facts 数字粗筛（用 PDF 文本兜底） ----
    precheck_warns = locked_facts_precheck_from_pdf(data, pdf_path)

    # ---- 4. 写 applications.md ----
    fill_resume_file(app_id, label + unverified)

    # ---- 5. 版式检查（内置） ----
    lp_r, li_r = layout_check_resume(pdf_path)
    lp_c, li_c = layout_check_cl(cl_pdf_path)
    layout_problems = lp_r + lp_c

    # ---- 6. 报告 ----
    print(f"\n[OK] make 完成 — {app_id}{'  [⚠ UNVERIFIED 跳过核对]' if skip_verify else ''}")
    print(f"  简历 PDF：auto-apply/applications/{label}{unverified}.pdf（{pages} 页）")
    print(f"  Cover letter PDF：auto-apply/applications/{cl_label}{unverified}.pdf（{cl_pages} 页）")
    print(f"  applications.md：{app_id} 行 Resume File 已填")
    print()
    print("  [版式检查]")
    for i in li_r + li_c:
        print(f"     · {i}")
    for p in layout_problems:
        print(f"     ✗ {p}")
    if not layout_problems:
        print("     版式检查通过 ✓")
    if precheck_warns:
        print()
        print("  [locked_facts 数字粗筛（兜底）]")
        for w in precheck_warns:
            print(f"     · {w}")
    print()
    # 检查 qualreview 当前状态
    try:
        cur = yaml.safe_load(open(yaml_path, encoding="utf-8")) or {}
        qr = (cur.get("review_status") or {}).get("qualreview") or {}
        qr_rating = qr.get("rating")
        qr_expectation = (qr.get("expectation") or "").strip()
    except Exception:
        qr_rating = None
        qr_expectation = ""

    print("  " + "=" * 56)
    print("  ⚠️  投递前必做（未完成不得投递）：")
    print(f"     1. 派质量审核 agent（jobs/_quality_review_prompt.md，APP_ID={app_id}）")
    if qr_rating and qr_expectation:
        print(f"        当前 review_status.qualreview = {qr_rating} · {qr_expectation}（已完整审核）")
    elif qr_rating and not qr_expectation:
        print(f"        ⚠ 当前 rating={qr_rating} 但 expectation 为空 —— 重跑 qualreview-pass 补齐")
    else:
        print(f"        当前 review_status.qualreview 未填 —— agent 跑完后 Claude 跑：")
        print(f"        build.py qualreview-pass --app {app_id} --rating <4级> --expectation \"<期待句>\"")
    print(f"     2. 跑 build.py review --app {app_id}（投递前总检查，四项全绿才可投）")
    print("  " + "=" * 56)
    if layout_problems:
        print(f"  ❗ 版式 {len(layout_problems)} 项问题，需先修正")
    print()
    print("  会话另需按 CLAUDE.md「同步检查清单」收尾：Notion · README · Stage 推进")


# _apply_compression_step() 已删除（2026-07-07）：自动压页从未接线（无调用方），
# 且其中的排版压缩手段（缩标题间距/行距）已被政策废除 —— 超页只减内容不缩排版。
# 超页时由 Claude 按 APP yaml 的 page_compression.steplist（纯内容手段）回阶段2缩减后重 make。


# ============================================================
# locked_facts 数字归一化粗筛
# ============================================================

def normalize_numbers(text):
    nums = set()
    for m in re.finditer(r'\d[\d,]*\.?\d*', text):
        raw = m.group(0).replace(',', '').rstrip('.')
        if raw:
            nums.add(raw)
    return nums


def locked_facts_precheck(data, final_doc_xml):
    """旧版：从 docx XML 提文本。保留兼容（仍用于 archived path）。"""
    locked = data.get("locked_facts", {}).get("numeric", []) or []
    if not locked:
        return ["locked_facts.numeric 为空 — 阶段2 未填（建议补）"]
    body_text = ' '.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', final_doc_xml, re.S))
    doc_nums = normalize_numbers(html.unescape(body_text))
    warns = []
    for v in locked:
        if str(v).replace(',', '').strip() not in doc_nums:
            warns.append(f"locked_facts 数值 '{v}' 未在最终简历中找到 — 可能丢失或被改动")
    return warns


def locked_facts_precheck_from_pdf(data, pdf_path):
    """2026-05-26 新增：从 PDF 文本提取数字做粗筛。RR 渲染路线下用此版本。"""
    locked = data.get("locked_facts", {}).get("numeric", []) or []
    if not locked:
        return ["locked_facts.numeric 为空 — 阶段2 未填（建议补）"]
    if not os.path.isfile(pdf_path):
        return [f"PDF 不存在，跳过 locked_facts 粗筛：{pdf_path}"]
    # 用 pdftotext（poppler-utils）拿 PDF 全文。如果不可用，fallback 用 pdfinfo 跳过。
    try:
        r = subprocess.run(["pdftotext", "-layout", pdf_path, "-"],
                           capture_output=True, text=True, timeout=30)
        body_text = r.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ["pdftotext 不可用，跳过 locked_facts 粗筛（建议安装 poppler-utils）"]
    doc_nums = normalize_numbers(body_text)
    warns = []
    for v in locked:
        if str(v).replace(',', '').strip() not in doc_nums:
            warns.append(f"locked_facts 数值 '{v}' 未在最终简历 PDF 中找到 — 可能丢失或被改动")
    return warns


# ============================================================
# Cover letter 生成（已退役：2026-05-26 起切到 rr_render.py）
# ============================================================
# build_cover_letter() 旧实现已删除。新流程由 rr_render.render_resume_and_cl
# 一次性生成简历 + CL 两份 PDF（RR API 路径）。
# 旧实现归档位置：auto-apply/_archive/resume_render.py（build_cover_letter_xml）


# ============================================================
# 版式检查（确定性）
# ============================================================

def _load_master_contact_for_check():
    """给 layout_check_* 用的宽松读取：从 master_resume.yaml 取 contact.name / 邮箱。
    跟 load_master() 不同 —— 这里读失败/字段缺失只返回 None，不 sys.exit，
    调用方降级为跳过对应断言 + 打印警告，不让 review 因为母版读取问题而崩溃。
    返回 (name, email) —— 任一项拿不到就是 None。
    """
    try:
        m = yaml.safe_load(open(MASTER_YAML, encoding="utf-8")) or {}
    except Exception as e:
        print(f"  [WARN] layout_check 读 master_resume.yaml 失败（{e}），跳过姓名/邮箱断言")
        return None, None
    contact = m.get("contact") or {}
    name = contact.get("name")
    line = contact.get("line") or ""
    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', line)
    email = email_match.group(0) if email_match else None
    if not name:
        print("  [WARN] master_resume.yaml contact.name 缺失，跳过姓名断言")
    if not email:
        print("  [WARN] master_resume.yaml contact.line 里提取不到邮箱，跳过邮箱断言")
    return name, email


def layout_check_resume(pdf_path):
    problems, info = [], []
    if not os.path.isfile(pdf_path):
        problems.append(f"简历 PDF 不存在：{pdf_path}")
        return problems, info
    pages = pdf_pages(pdf_path)
    max_pages = load_workspace_config()["resume_layout"]["max_pages"]
    if pages is not None and pages <= max_pages:
        info.append(f"简历页数 = {pages}（上限 {max_pages}）✓")
    else:
        problems.append(f"简历页数 = {pages}（上限 {max_pages}，workspace.yaml 可配；超页只减内容不缩排版）")
    txt = subprocess.run(["pdftotext", "-layout", pdf_path, "-"],
                         capture_output=True, text=True).stdout
    # 2026-05-28: RR meowth 模板用 CSS text-transform uppercase 渲染 heading；
    # PDF 字符流是 title 原始大小写还是转换后取决于 React PDF 实现。为安全起见用 case-insensitive 匹配。
    # Master sections.*.title 现在是 "Summary" / "Experience" / "Education" / "Skills"（2026-05-28 patch）。
    txt_lower = txt.lower()
    for sec in ("Summary", "Experience", "Education", "Skills"):
        if sec.lower() not in txt_lower:
            problems.append(f"简历缺 section：{sec}")
    if all("section" not in p for p in problems):
        info.append("四大 section 齐全 ✓")
    _, email = _load_master_contact_for_check()
    if email and email not in txt:
        problems.append("简历联系行缺失或邮箱不对")
    if re.search(r'[一-鿿]', txt):
        problems.append("简历正文含中文字符")
    return problems, info


def layout_check_cl(pdf_path):
    problems, info = [], []
    if not os.path.isfile(pdf_path):
        info.append("cover letter PDF 不存在 —— 该岗位可能未生成 CL")
        return problems, info
    pages = pdf_pages(pdf_path)
    if pages == 1:
        info.append("CL 页数 = 1 ✓")
    else:
        problems.append(f"CL 页数 = {pages}（应为 1）")
    txt = subprocess.run(["pdftotext", "-layout", pdf_path, "-"],
                         capture_output=True, text=True).stdout
    name, email = _load_master_contact_for_check()
    checks = {"Re 行": "Re:" in txt, "称呼": "Dear" in txt,
              "落款": "Sincerely" in txt or "Best regards" in txt}
    signature = display_name_from_contact({"name": name}) if name else ""
    if signature:
        checks["署名"] = signature in txt
    else:
        print("  [WARN] 无法从 master contact.name 派生署名，跳过署名断言")
    if name:
        checks["header 姓名"] = name in txt
    if email:
        checks["联系行"] = email in txt
    for k, ok in checks.items():
        if not ok:
            problems.append(f"CL 缺要素：{k}")
    if all(checks.values()):
        info.append("CL 结构要素齐全 ✓")
    if re.search(r'[一-鿿]', txt):
        problems.append("CL 正文含中文字符")
    return problems, info


# ============================================================
# 子命令：review —— 投递前总闸
# ============================================================

def _load_yaml(app_id):
    yaml_path = os.path.join(JOBS_DIR, f"{app_id}.yaml")
    if not os.path.isfile(yaml_path):
        sys.exit(f"数据文件不存在：{yaml_path}")
    return yaml_path, yaml.safe_load(open(yaml_path, encoding="utf-8")) or {}


def _save_yaml(yaml_path, data):
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=10000)


def content_hash(data):
    """对 resume + cover_letter 两个子树做确定性序列化后取 sha256 前16位。
    2026-07-07 新增：防止 factcheck-pass 锁定 PASS 后，内容被再次修改而旧 PASS 仍放行 make/review。
    sort_keys=True 保证字段顺序变化不影响哈希（只关心内容，不关心 key 排列）。"""
    sub = {
        "resume": data.get("resume") or {},
        "cover_letter": data.get("cover_letter") or {},
    }
    dumped = yaml.safe_dump(sub, sort_keys=True, allow_unicode=True)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()[:16]


def _read_report_result(report_path, pattern, label):
    """读报告文件，找首个非空行，匹配 pattern（如 RESULT: PASS|NEEDS-USER）。
    返回匹配到的组1（去除首尾空白）。匹配不到 / FAIL / 文件不存在 → 报错退出。
    label 用于报错信息（"factcheck" / "qualreview"）。"""
    if not os.path.isfile(report_path):
        sys.exit(f"[BLOCKED] --report 文件不存在：{report_path}")
    text = open(report_path, encoding="utf-8").read()
    first_nonempty = None
    for ln in text.split("\n"):
        if ln.strip():
            first_nonempty = ln.strip()
            break
    if first_nonempty is None:
        sys.exit(f"[BLOCKED] --report 文件为空：{report_path}")
    m = re.match(pattern, first_nonempty)
    if not m:
        sys.exit(f"[BLOCKED] --report 首个非空行不符合预期格式：{first_nonempty!r}"
                 f"\n  → {label} 报告首行必须是可解析的 RESULT/RATING 机器行")
    return m.group(1), text


# 核对报告首行的合法 token。NEEDS-USER 是现行 token（= 需候选人本人裁决）；
# 旧模板产出的历史 token 同义接受，仅作向后兼容，模板/文档不再产出它。
_FACTCHECK_RESULT_RE = r'RESULT:\s*(PASS|NEEDS-USER|NEEDS-LEON|FAIL)\s*$'  # engine-lint-allow: 旧 token 向后兼容


# ============================================================
# 子命令：harvest —— 已核对片段库（rewrite_library.yaml）
# ============================================================
# 2026-07-08 新增。已 factcheck PASS 的 APP###.yaml 里，rewritten 段已经过独立核对
# agent 逐字核对过 —— 这些文本是"已验证素材"，值得沉淀成跨岗位可复用的片段库，
# 减少每次阶段2 从零改写、也减少重复核对同样的事实点。
#
# 库文件本身只是"素材来源"，不是"成品模板"——阶段2 取用库片段仍需判断是否贴合
# 当前 JD，改写后要不要保留 source 标注；keyword_map 纪律照常执行（见 jobs/_schema.md 3.1b）。

def _slot_slug(label):
    """skills label（如 "SEO & Marketing:"）→ slot 用的小写 slug（去冒号、空格转下划线）。"""
    s = label.strip().rstrip(":").strip()
    s = re.sub(r'[^A-Za-z0-9]+', '-', s).strip('-').lower()
    return s


def _snippet_id(slot, text):
    """slot + 文本哈希前4位，如 "ore.bullet-b2a7"。同 slot 多条时避免 id 冲突。"""
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:4]
    slot_part = re.sub(r'[^A-Za-z0-9.]+', '-', slot).strip('-')
    return f"{slot_part}-{h}"


def load_rewrite_library():
    """读 rewrite_library.yaml。文件不存在 → 返回空骨架（{schema_version:1, snippets:[]}）。"""
    path = rewrite_library_path()
    if not os.path.isfile(path):
        return {"schema_version": 1, "snippets": []}
    data = yaml.safe_load(open(path, encoding="utf-8")) or {}
    data.setdefault("schema_version", 1)
    data.setdefault("snippets", [])
    return data


def save_rewrite_library(data):
    path = rewrite_library_path()
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=100)


def _harvest_extract(data, tags):
    """从一份已核对 PASS 的 APP###.yaml 提取可入库片段，返回 [{id, slot, master_ref,
    angle, text, context, verified_at}, ...]（未去重，由调用方对照现有库去重）。"""
    app_id = data.get("app_id", "")
    company = data.get("company", "")
    role = data.get("role", "")
    context = f"{app_id} · {company} · {role}".strip(" ·")

    rs = (data.get("review_status") or {}).get("factcheck") or {}
    verified_at = (rs.get("passed_at") or "")[:10]  # ISO 时间戳取日期部分

    r = data.get("resume") or {}
    out = []

    # summary
    summary_rw = (r.get("summary", {}).get("rewritten") or "").strip()
    if summary_rw:
        out.append({
            "id": _snippet_id("summary", summary_rw),
            "slot": "summary",
            "master_ref": (r["summary"].get("master") or "")[:60],
            "angle": list(tags),
            "text": summary_rw,
            "context": context,
            "verified_at": verified_at,
        })

    # skills
    for s in r.get("skills") or []:
        rw = (s.get("rewritten") or "").strip()
        if not rw:
            continue
        slot = f"skills.{_slot_slug(s.get('label', ''))}"
        out.append({
            "id": _snippet_id(slot, rw),
            "slot": slot,
            "master_ref": (s.get("master") or "")[:60],
            "angle": list(tags),
            "text": rw,
            "context": context,
            "verified_at": verified_at,
        })

    # experience bullets
    for e in r.get("experience") or []:
        exp_id = e.get("id", "")
        for b in e.get("bullets") or []:
            rw = (b.get("rewritten") or "").strip()
            if not rw:
                continue
            slot = f"{exp_id}.bullet"
            out.append({
                "id": _snippet_id(slot, rw),
                "slot": slot,
                "master_ref": (b.get("master") or "")[:60],
                "angle": list(tags),
                "text": rw,
                "context": context,
                "verified_at": verified_at,
            })

    # cover letter body paragraphs
    for p in (data.get("cover_letter") or {}).get("body_paragraphs") or []:
        p = (p or "").strip()
        if not p:
            continue
        slot = "cl.paragraph"
        out.append({
            "id": _snippet_id(slot, p),
            "slot": slot,
            "master_ref": "",   # cover letter 没有 master 原文可对照，留空
            "angle": list(tags),
            "text": p,
            "context": context,
            "verified_at": verified_at,
        })

    return out


def cmd_harvest(args):
    """harvest --app APP-### [--tags a,b] [--allow-legacy]
    从已 factcheck PASS 的 APP###.yaml 提取 rewritten 全文入库 rewrite_library.yaml。

    前置：review_status.factcheck.result == "PASS"，且 content_hash 与当前内容一致；
    hash 缺失（旧版锁定）默认拒绝，--allow-legacy 放行并打警告。"""
    app_id = normalize_app_id(args.app)
    yaml_path, data = _load_yaml(app_id)
    _legacy_or_missing_resume_guard(app_id, data, "harvest")

    fc_result = ((data.get("review_status") or {}).get("factcheck") or {}).get("result")
    if fc_result != "PASS":
        sys.exit(f"[BLOCKED] {app_id}.yaml review_status.factcheck.result != PASS（当前 {fc_result!r}）"
                 f"\n  → harvest 只入库已核对通过的内容")

    hash_status, hash_msg = factcheck_hash_check(data)
    allow_legacy = getattr(args, "allow_legacy", False)
    if hash_status == "mismatch":
        sys.exit(f"[BLOCKED] factcheck content_hash 不一致 —— {hash_msg}"
                 f"\n  → 内容在核对锁定后被改过，重新核对锁定后再 harvest")
    if hash_status == "no_hash":
        if not allow_legacy:
            sys.exit(f"[BLOCKED] {app_id}.yaml 是旧版锁定（无 content_hash），harvest 默认拒绝。"
                     f"\n  → 确认内容自锁定后未被改动 → 加 --allow-legacy 放行")
        print(f"  ⚠ {hash_msg}（--allow-legacy 放行）")

    tags_raw = (getattr(args, "tags", None) or "").strip()
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

    candidates = _harvest_extract(data, tags)
    if not candidates:
        print(f"[OK] {app_id} 无可入库内容（所有 rewritten 均为空）")
        return

    lib = load_rewrite_library()
    existing_by_slot = {}
    for sn in lib["snippets"]:
        existing_by_slot.setdefault(sn.get("slot"), set()).add(sn.get("text"))

    n_added, n_skipped = 0, 0
    for c in candidates:
        seen = existing_by_slot.setdefault(c["slot"], set())
        if c["text"] in seen:
            n_skipped += 1
            continue
        lib["snippets"].append(c)
        seen.add(c["text"])
        n_added += 1

    save_rewrite_library(lib)
    print(f"[OK] harvest {app_id} 完成：入库 {n_added} 条 / 跳过重复 {n_skipped} 条")
    print(f"  库文件：{rewrite_library_path()}（共 {len(lib['snippets'])} 条）")


def cmd_factcheck_pass(args):
    """用户完成 factcheck 裁决（Claude 已执行删/留/补 SSOT）后跑此命令锁定 PASS。
    把 review_status.factcheck 写进 APP###.yaml，带时间戳和决策摘要。

    2026-07-07 改造：--report 必传（核对 agent 报告存盘后传入的文件路径）。
    命令读取该文件，首个非空行必须是 `RESULT: PASS` 或 `RESULT: NEEDS-USER`（FAIL 或格式不对 → 拒绝锁定；
    旧模板产出的历史 token 同义接受，见 _FACTCHECK_RESULT_RE）。
    报告全文存入 review_status.factcheck.report，并计算 content_hash 存档防过期。"""
    app_id = normalize_app_id(args.app)
    yaml_path, data = _load_yaml(app_id)
    _legacy_or_missing_resume_guard(app_id, data, "factcheck-pass")

    # 前置检查：必须有阶段2 内容（防止裸跑）
    r = data.get("resume") or {}
    has_rw = ((r.get("summary", {}).get("rewritten") or "").strip()
              or any((s.get("rewritten") or "").strip() for s in (r.get("skills") or []))
              or any((b.get("rewritten") or "").strip()
                     for e in (r.get("experience") or []) for b in (e.get("bullets") or [])))
    if not has_rw:
        sys.exit(f"[BLOCKED] {app_id}.yaml 没有任何 rewritten 内容 —— 阶段2 未填，不允许 factcheck-pass")

    result, report_text = _read_report_result(args.report, _FACTCHECK_RESULT_RE, "factcheck")
    if result == "FAIL":
        sys.exit(f"[BLOCKED] --report 首行是 RESULT: FAIL —— 核对未通过，不允许锁定 PASS。"
                 f"\n  → 按报告阻断项修阶段2 rewritten，重新派核对 agent")

    rs = data.setdefault("review_status", {})
    rs["factcheck"] = {
        "result": "PASS",
        "passed_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "note": (args.note or "").strip() or "用户已完成所有裁决执行（删/留/补 SSOT），factcheck 锁定 PASS",
        "report": report_text,
        "content_hash": content_hash(data),
    }
    _save_yaml(yaml_path, data)
    print(f"[OK] {app_id} factcheck 锁定 PASS（报告原文 {len(report_text)} 字符 + content_hash 已存档）")
    print(f"  下一步：build.py make --app {app_id}")


def cmd_qualreview_pass(args):
    """质量审核 agent 跑完后，把 4 级评级 + 期待管理句写进 yaml + applications.md。
    --rating: High / Medium-High / Medium / Low
    --expectation: 期待管理一句话

    前置检查：
    - APP###.yaml 必须存在
    - factcheck 必须 PASS（qualreview agent 审的是已 factcheck PASS 的成品）
    - 简历成品 PDF 必须存在（agent 是要读 PDF 才能审）
    """
    app_id = normalize_app_id(args.app)
    rating = args.rating
    expectation = (args.expectation or "").strip()
    if rating not in ("High", "Medium-High", "Medium", "Low"):
        sys.exit(f"--rating 必须是 High/Medium-High/Medium/Low，传入 {rating!r}")
    if not expectation:
        sys.exit(f"--expectation 期待管理一句话必传")

    yaml_path, data = _load_yaml(app_id)

    # 前置：factcheck 必须先 PASS（防止裸跑/未审就锁定 rating）
    fc_result = ((data.get("review_status") or {}).get("factcheck") or {}).get("result")
    if fc_result != "PASS":
        sys.exit(f"[BLOCKED] {app_id}.yaml 的 review_status.factcheck.result != PASS（当前 {fc_result!r}）"
                 f"\n  → 先完成 factcheck 流程并跑 build.py factcheck-pass --app {app_id}")

    # 前置：简历成品 PDF 必须存在（qualreview agent 是审成品的）
    company_slug = slugify(data.get("company", ""))
    role_slug    = slugify(data.get("role", ""))
    prefix = f"{app_id.replace('-', '')}_{company_slug}_{role_slug}_"
    pdfs = glob.glob(os.path.join(OUT_DIR, prefix + "*.pdf"))
    if not pdfs:
        sys.exit(f"[BLOCKED] 找不到简历成品 PDF（{prefix}*.pdf）"
                 f"\n  → 先跑 build.py make --app {app_id}，agent 审的是成品 PDF")

    qualreview_entry = {
        "rating": rating,
        "expectation": expectation,
        "passed_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }

    report_arg = getattr(args, "report", None)
    if report_arg:
        report_rating, report_text = _read_report_result(
            report_arg, r'RATING:\s*(High|Medium-High|Medium|Low)\s*$', "qualreview")
        if report_rating != rating:
            sys.exit(f"[BLOCKED] --report 首行 RATING: {report_rating} 与 --rating {rating} 不一致"
                     f"\n  → 传入的 --rating 必须与报告首行机器行一致")
        qualreview_entry["report"] = report_text
    else:
        print("  ⚠ 未传 --report —— 建议传 qualreview agent 报告文件留痕（--report <路径>）")

    rs = data.setdefault("review_status", {})
    rs["qualreview"] = qualreview_entry
    _save_yaml(yaml_path, data)
    print(f"[OK] {app_id}.yaml review_status.qualreview 已填：{rating}")

    # 同步 applications.md Match 列
    text = open(APPS_MD, encoding="utf-8").read()
    cols = _table_columns(text)
    if cols is None or "Match" not in cols:
        print(f"  ⚠ applications.md 无 Match 列，跳过表内同步（请手动检查列结构）")
    else:
        mi = cols["Match"]
        lines = text.split("\n")
        wrote = False
        for i, ln in enumerate(lines):
            if re.match(rf'\|\s*{re.escape(app_id)}\s*\|', ln):
                cells = ln.split("|")
                if mi < len(cells):
                    cells[mi] = f" {rating} "
                    lines[i] = "|".join(cells)
                    wrote = True
                break
        if wrote:
            with open(APPS_MD, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            print(f"  ✓ applications.md {app_id} Match = {rating}")
        else:
            print(f"  ⚠ applications.md 找不到 {app_id} 行，跳过")

    print(f"  ⚠ Notion 同步需手动：把 Match Level = {rating} 写进对应 page")
    print(f"  ⚠ Notes 期待句建议追加：「{expectation}」")
    print(f"  下一步：build.py review --app {app_id}")


# ============================================================
# 投递状态收编：tracking 子树 + tracker/submit/close/fact 子命令
# ============================================================
# 2026-07-07 新增。设计原则：
#   · jobs/APP###.yaml 的 tracking 子树是投递状态唯一源；applications.md 两张表
#     变成标记区间内的生成物（区间外内容——文件头/Stage Definitions/Response Rate
#     Log——原样保留，tracker 命令不碰）。
#   · tracking 字段不进 content_hash 计算范围（content_hash() 只序列化
#     resume+cover_letter 子树），改 tracking 不影响已锁定的 factcheck 哈希。

AUTO_GEN_MARK = "<!-- AUTO-GENERATED: build.py tracker（勿手编辑，改 yaml 后重跑）-->"

ACTIVE_COLS = ["APP", "Company", "Role", "Category", "Location", "Applied",
               "Stage", "Outcome", "Match", "Follow-up by", "Resume File", "Notes"]
CLOSED_COLS = ["APP", "Company", "Role", "Reason", "Date"]

CLOSE_REASON_LABELS = {
    "no-response": "No response",
    "rejected": "Rejected",
    "withdrawn": "Withdrawn",
    "skipped": "Skipped",
    "expired": "Skipped",
}
CLOSE_REASON_NOTION_STATUS = {
    "no-response": "No Response",
    "rejected": "Rejected",
    "withdrawn": "Withdrawn",
    "skipped": "Skipped",
    "expired": "Skipped",
}


def _all_app_yaml_paths():
    return sorted(glob.glob(os.path.join(JOBS_DIR, "APP-*.yaml")),
                  key=lambda p: os.path.basename(p))


def _load_yaml_soft(path):
    """宽松读取：解析失败返回 None，不崩溃（tracker 遍历全部 yaml 用）。"""
    try:
        return yaml.safe_load(open(path, encoding="utf-8")) or {}
    except Exception:
        return None


def _tracking_row_cells(app_id, data):
    """把一个 APP 的 yaml 数据组装成 Active 表一行的 {列名: 值}（未含首尾空串列）。"""
    t = data.get("tracking") or {}
    return {
        "APP": app_id,
        "Company": data.get("company", "") or "—",
        "Role": data.get("role", "") or "—",
        "Category": t.get("category") or "—",
        "Location": t.get("location") or "—",
        "Applied": t.get("applied") or "—",
        "Stage": data.get("stage") or "—",
        "Outcome": t.get("outcome") or "—",
        "Match": t.get("match") or "—",
        "Follow-up by": t.get("follow_up_by") or "—",
        "Resume File": t.get("resume_file") or "—",
        "Notes": t.get("notes") or "—",
    }


def _render_md_row(cells, col_order):
    return "| " + " | ".join(str(cells.get(c, "—") or "—") for c in col_order) + " |"


def _closed_reason_text(data):
    t = data.get("tracking") or {}
    closed = t.get("closed") or {}
    return closed.get("reason") or "—"


def _closed_date_text(data):
    t = data.get("tracking") or {}
    closed = t.get("closed") or {}
    return closed.get("date") or "—"


def _find_table_span(lines, header_prefix, next_header_prefixes):
    """定位一张表在 lines 里的范围：从表头行到最后一条数据行（'| APP-...'）之后。
    停止条件是遇到第一条不是数据行的行（通常是紧跟表格的空行），而不是找下一个 '## '
    标题——这样表格与下一个标题之间的空行/'---' 分隔符留在区间外，原样保留不被吞掉。
    返回 (header_idx, sep_idx, data_start_idx, data_end_idx_exclusive)，找不到返回 None。"""
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith(header_prefix):
            header_idx = i
            break
    if header_idx is None:
        return None
    sep_idx = header_idx + 1  # 分隔行 |---|---|...
    data_start = sep_idx + 1
    data_end = data_start
    for i in range(data_start, len(lines)):
        if lines[i].lstrip().startswith("| APP-"):
            data_end = i + 1
        else:
            break
    return header_idx, sep_idx, data_start, data_end


def _app_num(app_id):
    m = re.search(r'\d+', app_id)
    return int(m.group()) if m else 0


def regenerate_tracker_tables():
    """从全部 jobs/APP-*.yaml 的 tracking 子树重新生成 applications.md 两张表，
    替换 AUTO_GEN_MARK 标记区间内的内容。区间外一字不动。
    Active 表 = stage 不是 Closed 的；Closed 表 = stage 是 Closed 的（按 APP 编号升序）。
    """
    if not os.path.isfile(APPS_MD):
        sys.exit(f"applications.md 不存在：{APPS_MD}")
    text = open(APPS_MD, encoding="utf-8").read()
    lines = text.split("\n")

    all_data = {}
    for yp in _all_app_yaml_paths():
        app_id = os.path.splitext(os.path.basename(yp))[0]
        d = _load_yaml_soft(yp)
        if d is not None:
            all_data[app_id] = d

    active_ids = sorted(
        (aid for aid, d in all_data.items() if (d.get("stage") or "") != "Closed"),
        key=_app_num)
    closed_ids = sorted(
        (aid for aid, d in all_data.items() if (d.get("stage") or "") == "Closed"),
        key=_app_num)

    active_rows_md = [_render_md_row(_tracking_row_cells(aid, all_data[aid]), ACTIVE_COLS)
                       for aid in active_ids]
    closed_rows_md = [
        _render_md_row({
            "APP": aid,
            "Company": all_data[aid].get("company", "") or "—",
            "Role": all_data[aid].get("role", "") or "—",
            "Reason": _closed_reason_text(all_data[aid]),
            "Date": _closed_date_text(all_data[aid]),
        }, CLOSED_COLS)
        for aid in closed_ids
    ]

    active_span = _find_table_span(lines, "| APP ", ["## "])
    if active_span is None:
        # 兼容无空格变体
        active_span = _find_table_span(lines, "| APP|", ["## "])
    if active_span is None:
        sys.exit("applications.md 找不到 Active 表头行，结构异常")
    ah, asep, adata_start, adata_end = active_span
    # 重跑 tracker 时表头正上方可能已有上一次留下的 AUTO_GEN_MARK —— 一并纳入替换区间，
    # 避免标记行逐次重跑越堆越多。
    if ah > 0 and lines[ah - 1].strip() == AUTO_GEN_MARK:
        ah -= 1

    active_header = "| " + " | ".join(ACTIVE_COLS) + " |"
    active_sep = "|" + "|".join(["---"] * len(ACTIVE_COLS)) + "|"

    new_active_block = ([AUTO_GEN_MARK, active_header, active_sep] + active_rows_md)

    # 先替换 Active 表（表头+分隔+数据行），保留其后内容
    new_lines = lines[:ah] + new_active_block + lines[adata_end:]

    # 重新定位 Closed 表（因为上面替换可能改变了行号）。
    # Closed 表结构不同（5 列），要在 '## Closed' 标题之后找
    closed_header_idx = None
    for i, ln in enumerate(new_lines):
        if ln.startswith("## Closed"):
            closed_header_idx = i
            break
    if closed_header_idx is None:
        sys.exit("applications.md 找不到 '## Closed / Skipped'，结构异常")
    # 从标题往下找表头行 '| APP |'
    ch = None
    for i in range(closed_header_idx, len(new_lines)):
        if new_lines[i].lstrip().startswith("| APP "):
            ch = i
            break
    if ch is None:
        sys.exit("applications.md Closed 表头未找到，结构异常")
    # 同 Active 表：吞掉表头正上方已存在的 AUTO_GEN_MARK，避免重跑堆叠标记行。
    # 注意：吸收标记行只影响替换区间起点 block_start，表头/分隔/数据行的偏移
    # 必须基于真正的表头行 ch 计算（此前把两者混用导致重跑时旧数据行残留 → 表格重复）。
    block_start = ch
    if ch > 0 and new_lines[ch - 1].strip() == AUTO_GEN_MARK:
        block_start = ch - 1
    csep = ch + 1
    cdata_start = csep + 1
    cdata_end = cdata_start
    for i in range(cdata_start, len(new_lines)):
        if new_lines[i].lstrip().startswith("| APP-"):
            cdata_end = i + 1
        else:
            break

    closed_header = "| " + " | ".join(CLOSED_COLS) + " |"
    closed_sep = "|" + "|".join(["---"] * len(CLOSED_COLS)) + "|"
    new_closed_block = ([AUTO_GEN_MARK, closed_header, closed_sep] + closed_rows_md)

    final_lines = new_lines[:block_start] + new_closed_block + new_lines[cdata_end:]

    with open(APPS_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(final_lines))

    return len(active_rows_md), len(closed_rows_md)


def _print_notion_payload(app_id, fields):
    """人读的 Notion 同步字段清单，会话照着调 notion-update-page。"""
    print(f"\n  [Notion 同步 payload] {app_id}")
    for k, v in fields.items():
        print(f"     {k}: {v}")
    print(f"  → notion-search 查 {app_id} 对应 page id，再 notion-update-page(update_properties)")


def cmd_tracker(args):
    if getattr(args, "migrate", False):
        _tracker_migrate()
    else:
        n_active, n_closed = regenerate_tracker_tables()
        print(f"[OK] tracker 重新生成：Active {n_active} 行 · Closed {n_closed} 行")


def _tracker_migrate():
    """一次性迁移：解析 applications.md 现有两张表 → 写入/创建各 APP 的 tracking 子树。"""
    text = open(APPS_MD, encoding="utf-8").read()
    cols = _table_columns(text)
    if cols is None:
        sys.exit("applications.md Active 表头解析失败，结构异常")
    active_rows = _read_active_rows(text, cols)
    closed_ln_split = text.split("## Closed", 1)
    closed_body = closed_ln_split[1] if len(closed_ln_split) > 1 else ""

    n_stub = 0
    n_updated = 0

    # ---- Active 表行 ----
    for row in active_rows:
        app_id = row.get("APP", "").strip()
        if not app_id:
            continue
        yaml_path = os.path.join(JOBS_DIR, f"{app_id}.yaml")
        tracking = {
            "category": row.get("Category") or None,
            "location": row.get("Location") or None,
            "applied": row.get("Applied") or None,
            "outcome": row.get("Outcome") or None,
            "match": row.get("Match") or None,
            "follow_up_by": row.get("Follow-up by") or None,
            "resume_file": row.get("Resume File") or None,
            "notes": row.get("Notes") or None,
            "closed": None,
        }
        stage = row.get("Stage") or "Drafting"

        if os.path.isfile(yaml_path):
            data = yaml.safe_load(open(yaml_path, encoding="utf-8")) or {}
            data["tracking"] = tracking
            # 迁移语义：applications.md 当前显示的内容是迁移这一刻的 SSOT，无条件写入
            # yaml 顶层 stage/company/role，保证迁移前后表格语义一致（哪怕 yaml 内部这些
            # 字段此前已滞后于 md 的更新——那属于迁移前既有的漂移，migrate 不负责判断谁对，
            # 只负责把 md 当前状态如实收编进 yaml；resume/cover_letter/review_status 不碰）。
            data["stage"] = stage
            if row.get("Company"):
                data["company"] = row["Company"]
            if row.get("Role"):
                data["role"] = row["Role"]
            _save_yaml(yaml_path, data)
            n_updated += 1
        else:
            stub = {
                "schema_version": SCHEMA_VERSION,
                "app_id": app_id,
                "company": row.get("Company", "") or "",
                "role": row.get("Role", "") or "",
                "created": None,
                "stage": stage,
                "legacy": True,
                "tracking": tracking,
            }
            _save_yaml(yaml_path, stub)
            n_stub += 1

    # ---- Closed 表行 ----
    for ln in closed_body.split("\n"):
        m = re.match(r'\|\s*(APP-\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|', ln)
        if not m:
            continue
        app_id, company, role, reason, date = m.groups()
        yaml_path = os.path.join(JOBS_DIR, f"{app_id}.yaml")
        closed = {"date": date or None, "reason": reason or None}
        if os.path.isfile(yaml_path):
            data = yaml.safe_load(open(yaml_path, encoding="utf-8")) or {}
            t = data.setdefault("tracking", {})
            t.setdefault("category", None)
            t.setdefault("location", None)
            t.setdefault("applied", None)
            t.setdefault("outcome", None)
            t.setdefault("match", None)
            t.setdefault("follow_up_by", None)
            t.setdefault("resume_file", None)
            t.setdefault("notes", None)
            t["closed"] = closed
            data["stage"] = "Closed"
            # 同 Active 分支：company/role 以 md 当前显示为准同步进 yaml（迁移语义，见上）。
            if company:
                data["company"] = company
            if role:
                data["role"] = role
            _save_yaml(yaml_path, data)
            n_updated += 1
        else:
            stub = {
                "schema_version": SCHEMA_VERSION,
                "app_id": app_id,
                "company": company or "",
                "role": role or "",
                "created": None,
                "stage": "Closed",
                "legacy": True,
                "tracking": {
                    "category": None, "location": None, "applied": None,
                    "outcome": None, "match": None, "follow_up_by": None,
                    "resume_file": None, "notes": None, "closed": closed,
                },
            }
            _save_yaml(yaml_path, stub)
            n_stub += 1

    print(f"[OK] tracker --migrate 完成：更新已有 yaml {n_updated} 份 · 新建 legacy stub {n_stub} 份")

    n_active, n_closed = regenerate_tracker_tables()
    print(f"  已插入标记 + 重新生成表格：Active {n_active} 行 · Closed {n_closed} 行")
    print(f"  建议：对比迁移前后表格内容（每行每列值应一致，行序可能按 APP 编号规整）")


def _legacy_or_missing_resume_guard(app_id, data, cmd_name):
    """verify/make/factcheck-pass 等命令的共同防护：legacy stub（无 resume 段）不允许跑深层命令。"""
    if data.get("legacy"):
        sys.exit(f"[BLOCKED] {app_id}.yaml 是 tracker --migrate 生成的 legacy stub（无 resume 段），"
                 f"不支持 {cmd_name}。\n  → 该岗位是旧系统投递记录，仅用于 tracking 展示，"
                 f"不支持简历生成/核对流程。")
    if "resume" not in data:
        sys.exit(f"[BLOCKED] {app_id}.yaml 缺 resume 段，不支持 {cmd_name}。"
                 f"\n  → 检查是否为 legacy/旧版数据文件")


def cmd_submit(args):
    app_id = normalize_app_id(args.app)
    yaml_path, data = _load_yaml(app_id)
    _legacy_or_missing_resume_guard(app_id, data, "submit")

    date_str = args.date or datetime.date.today().isoformat()
    try:
        applied_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        sys.exit(f"--date 格式错误：{date_str!r}，需 YYYY-MM-DD")

    external = getattr(args, "external", False)
    if not external:
        print(f"== submit {app_id} · 投递闸检查 ==")
        blockers, resume_pdf, _ = _review_gate(app_id, data, verbose=True)
        if resume_pdf is None or blockers:
            print("\n" + "=" * 56)
            print(f"  ⛔ 投递闸未通过，{len(blockers)} 项待办，拒绝登记投递：")
            for b in blockers:
                print(f"     · {b}")
            print(f"  → 处理完后重跑 build.py submit --app {app_id}")
            print(f"  → 若此投递是在流水线外完成（内推/猎头渠道），加 --external 跳过闸")
            sys.exit(1)
        print("\n  ✅ 四项全绿 —— 登记投递")
    else:
        print(f"== submit {app_id} · --external 跳过投递闸 ==")

    follow_up = (applied_date + datetime.timedelta(days=7)).isoformat()
    t = data.setdefault("tracking", {})
    t["applied"] = applied_date.isoformat()
    t["outcome"] = "Pending"
    t["follow_up_by"] = follow_up
    data["stage"] = "Applied"
    _save_yaml(yaml_path, data)

    n_active, n_closed = regenerate_tracker_tables()
    print(f"\n[OK] {app_id} 已登记投递：applied={applied_date.isoformat()} · "
          f"follow_up_by={follow_up} · stage=Applied")
    print(f"  applications.md 已重新生成（Active {n_active} 行 · Closed {n_closed} 行）")

    _print_notion_payload(app_id, {
        "Status": "Applied",
        "Apply Date (date:start)": applied_date.isoformat(),
    })
    print(f"\n  ⚠ 提醒：Response Rate Log 需手动追加一行（applications.md 末尾表格，"
          f"不在 tracker 生成范围内）")


def cmd_close(args):
    app_id = normalize_app_id(args.app)
    yaml_path, data = _load_yaml(app_id)

    reason = args.reason
    if reason not in CLOSE_REASON_LABELS:
        sys.exit(f"--reason 必须是 {list(CLOSE_REASON_LABELS)} 之一，传入 {reason!r}")

    date_str = args.date or datetime.date.today().isoformat()
    try:
        close_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        sys.exit(f"--date 格式错误：{date_str!r}，需 YYYY-MM-DD")

    t = data.setdefault("tracking", {})
    label = CLOSE_REASON_LABELS[reason]
    desc = label
    if reason == "no-response":
        applied_str = t.get("applied")
        applied_date = _parse_date_safe(applied_str) if applied_str else None
        if applied_date:
            n_days = (close_date - applied_date).days
            desc = f"No response · 投递后 {n_days} 天无回应 (Applied {applied_date.isoformat()})"
        else:
            desc = "No response · 投递后无回应（Applied 日期未知）"
    note = (getattr(args, "note", None) or "").strip()
    if note:
        desc = f"{desc} · {note}"

    t["closed"] = {"date": close_date.isoformat(), "reason": desc}
    data["stage"] = "Closed"
    _save_yaml(yaml_path, data)

    n_active, n_closed = regenerate_tracker_tables()
    print(f"[OK] {app_id} 已关闭：stage=Closed · reason={desc}")
    print(f"  applications.md 已重新生成（Active {n_active} 行 · Closed {n_closed} 行）")

    notion_status = CLOSE_REASON_NOTION_STATUS[reason]
    _print_notion_payload(app_id, {
        "Status": notion_status,
        "Closed Date": close_date.isoformat(),
    })


def cmd_fact(args):
    """SSOT Change Log 机械追加：Claude 先手动编辑 SSOT（workspace.yaml paths.ssot 指向
    的文件）对应章节正文，再跑此命令在第十一节变更日志表最后一行后追加一行，并刷新文件
    末尾「最后更新：」日期。定位方式：找最后一个以 '| 2026-' 开头的表格行（与既有 Change
    Log 追加逻辑一致）。"""
    if not os.path.isfile(SSOT):
        sys.exit(f"SSOT 不存在：{SSOT}")
    text = open(SSOT, encoding="utf-8").read()
    lines = text.split("\n")

    last_row_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith("| 2026-") or re.match(r'^\|\s*\d{4}-\d{2}(-\d{2})?\s*\|', ln):
            last_row_idx = i
    if last_row_idx is None:
        sys.exit(f"SSOT（{os.path.basename(SSOT)}）找不到任何 Change Log 表格行"
                 "（'| 2026-...' 开头），结构异常")

    today = datetime.date.today().isoformat()
    topic = args.topic.strip()
    content = args.content.strip()
    cause = (args.cause or "").strip()
    files = (args.files or "").strip()
    tier3 = (args.tier3 or "").strip()

    # 现表是 5 列：日期 | 字段/变更项 | 旧值→新值 | Tier2已同步 | Tier3状态。
    # cause 融入第 3 列（沿用既有惯例：起因写在"旧值→新值"内容列前缀）。
    col3 = f"起因：{cause}。{content}" if cause else content
    new_row = f"| {today} | {topic} | {col3} | {files or '—'} | {tier3 or '—'} |"

    lines.insert(last_row_idx + 1, new_row)

    # 刷新文件末尾「最后更新：」日期
    updated_last_line = False
    for i in range(len(lines) - 1, -1, -1):
        if "最后更新" in lines[i]:
            lines[i] = re.sub(r'最后更新[：:]\s*\d{4}-\d{2}-\d{2}',
                              f"最后更新：{today}", lines[i])
            updated_last_line = True
            break

    with open(SSOT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[OK] SSOT（{os.path.basename(SSOT)}）Change Log 已追加一行（第十一节最后一行之后）：")
    print(f"  {new_row}")
    if updated_last_line:
        print(f"  文件末尾「最后更新」日期已刷新为 {today}")
    else:
        print(f"  ⚠ 未找到「最后更新」标记行，日期未刷新，请手动检查文件末尾")


# ============================================================
# 子命令：status —— 只读全景仪表盘（不写任何文件）
# ============================================================

def _parse_date_safe(s):
    """统一日期解析：失败一律返回 None（调用方降级显示「—」）。"""
    s = (s or "").strip()
    if not s or s == "—":
        return None
    # 只取字符串里第一个形如 YYYY-MM-DD 的片段，兼容 cell 里夹杂说明文字的情况
    m = re.search(r'\d{4}-\d{2}-\d{2}', s)
    if not m:
        return None
    try:
        return datetime.date.fromisoformat(m.group(0))
    except ValueError:
        return None


def _split_row_cells(line, cols):
    """按 _table_columns 的列名→索引映射，取一行的 {列名: 值}（已 strip，空/— 视为空串）。"""
    cells = line.split('|')
    out = {}
    for name, idx in cols.items():
        if name == "" or idx >= len(cells):
            continue
        v = cells[idx].strip()
        if v == "—":
            v = ""
        out[name] = v
    return out


def _read_active_rows(text, cols):
    """解析 Active 表所有数据行（跳过表头/分隔行），返回 dict 列表。"""
    rows = []
    in_active = False
    for ln in text.split('\n'):
        if ln.startswith("## Active Applications"):
            in_active = True
            continue
        if ln.startswith("## Closed"):
            break
        if not in_active:
            continue
        s = ln.lstrip()
        if not s.startswith("| APP-"):
            continue
        rows.append(_split_row_cells(ln, cols))
    return rows


def _read_closed_app_ids(text):
    """Closed/Skipped 表只需数量和编号，不逐条解析列结构（该表列结构与 Active 不同）。"""
    ids = []
    in_closed = False
    for ln in text.split('\n'):
        if ln.startswith("## Closed"):
            in_closed = True
            continue
        if not in_closed:
            continue
        m = re.match(r'\|\s*(APP-\d+)\s*\|', ln)
        if m:
            ids.append(m.group(1))
    return ids


def _resume_file_date(filename):
    """从 Resume File 文件名尾部抓 YYYY-MM-DD 日期。抓不到返回 None。"""
    m = re.search(r'(\d{4}-\d{2}-\d{2})', filename or "")
    if not m:
        return None
    return _parse_date_safe(m.group(1))


def _days_since(d):
    if d is None:
        return None
    return (datetime.date.today() - d).days


def _yaml_next_step(app_id, data):
    """在制品（stage=Drafting）推断下一步命令，原文打印。"""
    r = data.get("resume") or {}
    has_rw = ((r.get("summary", {}).get("rewritten") or "").strip()
              or any((s.get("rewritten") or "").strip() for s in (r.get("skills") or []))
              or any((b.get("rewritten") or "").strip()
                     for e in (r.get("experience") or []) for b in (e.get("bullets") or [])))
    if not has_rw:
        return f"待阶段2填写（读 APP###.yaml + SSOT {os.path.basename(SSOT)} 填 rewritten）"

    fc_result = ((data.get("review_status") or {}).get("factcheck") or {}).get("result")
    if fc_result != "PASS":
        return f"派核对 agent → build.py factcheck-pass --app {app_id} --report <路径>"

    company_slug = slugify(data.get("company", ""))
    role_slug = slugify(data.get("role", ""))
    prefix = f"{app_id.replace('-', '')}_{company_slug}_{role_slug}_"
    pdfs = glob.glob(os.path.join(OUT_DIR, prefix + "*.pdf"))
    if not pdfs:
        return f"build.py make --app {app_id}"

    qr = (data.get("review_status") or {}).get("qualreview") or {}
    if not (qr.get("rating") and (qr.get("expectation") or "").strip()):
        return "派质量审核 agent → build.py qualreview-pass --app " + app_id + " --rating <4级> --expectation \"...\""

    return f"build.py review --app {app_id}"


def _collect_pipeline_data():
    """管道数据统一组装 —— cmd_status 和 cmd_dashboard 共用。绝不写任何文件。

    返回 dict：
      text, cols, active_rows, closed_ids           —— applications.md 原始解析结果
      yaml_data, yaml_load_errs                      —— 全部 APP yaml（app_id → data / 解析错误）
      today, grouped, other_stage                    —— 按 stage 分组的 Active 行
      n_drafting/n_ready/n_applied/n_active/n_closed —— 计数
      actions                                         —— [(权重, 文本), ...] 今日行动（未排序）
      inconsistencies, md_only_count                  —— 一致性自检结果
      applied_total, rejected_count, interview_count, ready_backlog —— 统计
      apps                                            —— 全量 APP 派生记录列表（供 dashboard 用），每条：
        {app_id, company, role, stage, outcome, applied, days_in_state, follow_up_by,
         match, resume_file, notes, closed_reason, closed_date}
    """
    text = open(APPS_MD, encoding="utf-8").read()
    cols = _table_columns(text)
    if cols is None:
        sys.exit("applications.md Active 表头解析失败，结构异常")

    active_rows = _read_active_rows(text, cols)
    closed_ids = _read_closed_app_ids(text)

    # yaml 全量载入（app_id → data），载入失败的记下但不崩溃
    yaml_paths = sorted(glob.glob(os.path.join(JOBS_DIR, "APP-*.yaml")))
    yaml_data = {}
    yaml_load_errs = []
    for yp in yaml_paths:
        app_id = os.path.splitext(os.path.basename(yp))[0]
        try:
            yaml_data[app_id] = yaml.safe_load(open(yp, encoding="utf-8")) or {}
        except Exception as e:
            yaml_load_errs.append(f"{app_id}.yaml 解析失败：{e}")

    today = datetime.date.today()

    # ---------------- [1] 管道全景：分组 ----------------
    stage_order = ["Drafting", "Ready", "Applied"]
    grouped = {s: [] for s in stage_order}
    other_stage = []
    for row in active_rows:
        stage = row.get("Stage", "") or "—"
        if stage in grouped:
            grouped[stage].append(row)
        else:
            other_stage.append(row)

    def key_date_for_row(row):
        applied = _parse_date_safe(row.get("Applied", ""))
        if applied:
            return applied, "Applied " + applied.isoformat()
        rf = row.get("Resume File", "")
        d = _resume_file_date(rf)
        if d:
            return d, "Resume " + d.isoformat()
        return None, "—"

    n_drafting = len(grouped["Drafting"])
    n_ready = len(grouped["Ready"])
    n_applied = len(grouped["Applied"])
    n_active = len(active_rows)
    n_closed = len(closed_ids)

    # ---------------- [2] 今日行动 ----------------
    actions = []  # (紧急度权重, 文本) —— 权重越小越靠前

    # Ready 过期（>7 天）
    for row in grouped["Ready"]:
        app_id = row.get("APP", "—")
        rf = row.get("Resume File", "")
        d = _resume_file_date(rf)
        days = _days_since(d)
        if days is not None and days > 7:
            actions.append((0, f"⚠ {app_id} Ready 已 {days} 天未投——先核实岗位是否还开放，"
                                f"投递前建议重 make 刷日期"))

    # 跟进过期
    for row in active_rows:
        app_id = row.get("APP", "—")
        fu = row.get("Follow-up by", "")
        outcome = (row.get("Outcome", "") or "").strip()
        d = _parse_date_safe(fu)
        if d and d < today and outcome == "Pending":
            days = (today - d).days
            actions.append((1, f"⚠ {app_id} 跟进已过期 {days} 天"))

    # Applied 超期（>45 天，Outcome=Pending）
    for row in active_rows:
        app_id = row.get("APP", "—")
        applied_d = _parse_date_safe(row.get("Applied", ""))
        outcome = (row.get("Outcome", "") or "").strip()
        if applied_d and outcome == "Pending":
            days = (today - applied_d).days
            if days > 45:
                actions.append((2, f"建议关闭：{app_id} 已 {days} 天无回应 → Closed·No response"))

    # 在制品下一步（yaml stage=Drafting）
    for app_id, data in sorted(yaml_data.items()):
        if (data.get("stage") or "") != "Drafting":
            continue
        step = _yaml_next_step(app_id, data)
        actions.append((3, f"{app_id}：{step}"))

    # ---------------- [3] 一致性自检 ----------------
    md_by_app = {row.get("APP", ""): row for row in active_rows if row.get("APP")}
    inconsistencies = []

    # 2026-07-07：applications.md 现在是 build.py tracker 从 yaml 生成的产物（tracking 子树）。
    # stage=Closed 的 yaml 理应不在 Active 表里，不算漂移；只对非 Closed 的 yaml 检查
    # 是否出现在 Active 表，且 tracking 子树存在时顺带比对 applied/stage 与 md 行是否一致
    # （迁移后应零漂移——非零说明有人绕过 tracker 手改了 applications.md，或 yaml 改了没重新生成）。
    for app_id, data in sorted(yaml_data.items()):
        yaml_stage = data.get("stage") or "—"
        if yaml_stage == "Closed":
            continue
        if app_id in md_by_app:
            md_stage = md_by_app[app_id].get("Stage", "") or "—"
            if yaml_stage != md_stage:
                inconsistencies.append(f"{app_id}：yaml stage={yaml_stage!r} 但 applications.md Stage={md_stage!r}")
            tracking = data.get("tracking")
            if tracking:
                yaml_applied = tracking.get("applied") or ""
                md_applied = md_by_app[app_id].get("Applied", "") or ""
                if (yaml_applied or "") != (md_applied or ""):
                    inconsistencies.append(
                        f"{app_id}：yaml tracking.applied={yaml_applied!r} 但 "
                        f"applications.md Applied={md_applied!r}（改 yaml 后忘记重跑 build.py tracker？）")
        else:
            inconsistencies.append(f"{app_id}：yaml 存在但 applications.md 无对应 Active 行")

    for app_id, row in md_by_app.items():
        rf = row.get("Resume File", "")
        if rf:
            # Resume File 列本身就是确切文件名（无扩展名）—— 优先按它精确匹配；
            # 匹配不到再退化为 slug 前缀模糊匹配（旧手工命名可能与 slugify 结果不一致，如 APP-035）
            pdfs = glob.glob(os.path.join(OUT_DIR, rf + "*"))
            if not pdfs:
                data = yaml_data.get(app_id)
                if data:
                    company_slug = slugify(row.get("Company", ""))
                    role_slug = slugify(data.get("role", ""))
                    prefix = f"{app_id.replace('-', '')}_{company_slug}_{role_slug}_"
                    pdfs = glob.glob(os.path.join(OUT_DIR, prefix + "*.pdf"))
            if not pdfs:
                inconsistencies.append(f"{app_id}：applications.md Resume File={rf!r} 但 "
                                        f"auto-apply/applications/ 下找不到对应 PDF")

    md_only_count = sum(1 for app_id in md_by_app if app_id not in yaml_data)

    # ---------------- [4] 统计 ----------------
    applied_total = 0
    for row in active_rows:
        if _parse_date_safe(row.get("Applied", "")):
            applied_total += 1
    closed_ln = text.split("## Closed", 1)
    closed_body = closed_ln[1] if len(closed_ln) > 1 else ""
    for ln in closed_body.split('\n'):
        if re.match(r'\|\s*APP-\d+\s*\|', ln) and re.search(r'Applied\s+\d{4}-\d{2}-\d{2}', ln):
            applied_total += 1

    rejected_count = closed_body.count("Rejected")
    # 面试识别很粗糙：只能按行扫描关键字，"未进入面试" 这类否定表述会被误记为正例。
    # 只逐行统计一次（同一行出现多个关键字不重复计数），并如实标注局限性。
    interview_count = 0
    for ln in closed_body.split('\n'):
        if re.match(r'\|\s*APP-\d+\s*\|', ln) and re.search(r'面试|Interview|HR\s*面', ln):
            interview_count += 1

    ready_backlog = n_ready

    # ---------------- apps：全量派生记录（供 dashboard 用） ----------------
    apps = []
    all_app_ids = sorted(set(md_by_app) | set(yaml_data), key=_app_num)
    for app_id in all_app_ids:
        row = md_by_app.get(app_id, {})
        data = yaml_data.get(app_id, {})
        stage = (data.get("stage") if data else None) or row.get("Stage", "") or "—"
        company = data.get("company") or row.get("Company", "") or "—"
        role = data.get("role") or row.get("Role", "") or "—"
        outcome = row.get("Outcome", "") or (data.get("tracking") or {}).get("outcome") or "—"
        applied = row.get("Applied", "") or (data.get("tracking") or {}).get("applied") or ""
        follow_up_by = row.get("Follow-up by", "") or (data.get("tracking") or {}).get("follow_up_by") or ""
        match = row.get("Match", "") or (data.get("tracking") or {}).get("match") \
            or ((data.get("review_status") or {}).get("qualreview") or {}).get("rating") or ""
        resume_file = row.get("Resume File", "") or (data.get("tracking") or {}).get("resume_file") or ""
        notes = row.get("Notes", "") or (data.get("tracking") or {}).get("notes") or ""
        closed_reason = _closed_reason_text(data) if data else "—"
        closed_date = _closed_date_text(data) if data else "—"

        d, _label = key_date_for_row(row) if row else (None, "—")
        if d is None and stage == "Closed":
            d = _parse_date_safe(closed_date)
        days_in_state = _days_since(d)

        apps.append({
            "app_id": app_id, "company": company, "role": role, "stage": stage,
            "outcome": outcome, "applied": applied, "days_in_state": days_in_state,
            "follow_up_by": follow_up_by, "match": match, "resume_file": resume_file,
            "notes": notes, "closed_reason": closed_reason, "closed_date": closed_date,
        })

    return {
        "text": text, "cols": cols, "active_rows": active_rows, "closed_ids": closed_ids,
        "yaml_data": yaml_data, "yaml_load_errs": yaml_load_errs,
        "today": today, "grouped": grouped, "other_stage": other_stage,
        "n_drafting": n_drafting, "n_ready": n_ready, "n_applied": n_applied,
        "n_active": n_active, "n_closed": n_closed,
        "actions": actions,
        "inconsistencies": inconsistencies, "md_only_count": md_only_count,
        "applied_total": applied_total, "rejected_count": rejected_count,
        "interview_count": interview_count, "ready_backlog": ready_backlog,
        "apps": apps,
    }


def cmd_status(args):
    """只读全景仪表盘：管道全景 + 今日行动 + 一致性自检 + 统计。绝不写任何文件。"""
    pd = _collect_pipeline_data()
    active_rows = pd["active_rows"]
    yaml_data = pd["yaml_data"]
    grouped = pd["grouped"]
    other_stage = pd["other_stage"]

    def key_date_for_row(row):
        applied = _parse_date_safe(row.get("Applied", ""))
        if applied:
            return applied, "Applied " + applied.isoformat()
        rf = row.get("Resume File", "")
        d = _resume_file_date(rf)
        if d:
            return d, "Resume " + d.isoformat()
        return None, "—"

    # ---------------- [1] 管道全景 ----------------
    print("=" * 60)
    print("[1] 管道全景")
    print("=" * 60)

    stage_order = ["Drafting", "Ready", "Applied"]
    for stage in stage_order + (["其他"] if other_stage else []):
        rows = grouped.get(stage, other_stage if stage == "其他" else [])
        if not rows:
            continue
        print(f"\n-- {stage}（{len(rows)} 条）--")
        for row in rows:
            app_id = row.get("APP", "—")
            company = row.get("Company", "—") or "—"
            outcome = row.get("Outcome", "") or "—"
            d, date_label = key_date_for_row(row)
            days = _days_since(d)
            days_label = f"{days} 天" if days is not None else "—"
            print(f"  {app_id} · {company} · {stage}/{outcome} · {date_label} · 已 {days_label}")

    print(f"\n汇总：Active {pd['n_active']} 条（Drafting {pd['n_drafting']} / Ready {pd['n_ready']} / "
          f"Applied {pd['n_applied']}）· Closed {pd['n_closed']} 条")

    # ---------------- [2] 今日行动 ----------------
    print("\n" + "=" * 60)
    print("[2] 今日行动")
    print("=" * 60)

    if not pd["actions"]:
        print("今日无待办 ✓")
    else:
        for _, text_line in sorted(pd["actions"], key=lambda x: x[0]):
            print(f"  {text_line}")

    # ---------------- [3] 一致性自检 ----------------
    print("\n" + "=" * 60)
    print("[3] 一致性自检")
    print("=" * 60)

    if pd["inconsistencies"]:
        for i in pd["inconsistencies"]:
            print(f"  ✗ {i}")
    else:
        print("  未发现 yaml/md 漂移 ✓")

    print(f"\n  md 有行但无 yaml：{pd['md_only_count']} 条（旧系统产物，属正常，不逐条列出）")

    if pd["yaml_load_errs"]:
        print("\n  yaml 解析异常：")
        for e in pd["yaml_load_errs"]:
            print(f"     · {e}")

    # ---------------- [4] 统计 ----------------
    print("\n" + "=" * 60)
    print("[4] 统计")
    print("=" * 60)

    print(f"  已投总数：{pd['applied_total']}（Active Applied 日期非空 + Closed 表含 Applied 字样的行）")
    print(f"  拒信数：{pd['rejected_count']}（从 Closed 表 Reason 文本识别 'Rejected' 关键字）")
    print(f"  面试数：{pd['interview_count']}（Closed 表中含 面试/Interview/HR 面 关键字的行数，"
          f"关键字识别粗糙，'未进入面试' 等否定表述也会被计入，仅供参考，不可作为准确值）")
    print(f"  回应数：无法从现有字段推断（需人工核对 Response Rate Log 或 Notion）")
    print(f"  Ready 积压数：{pd['ready_backlog']}")

    nag = update_check_nag()   # 纯本地时间戳判断，不联网
    if nag:
        print(f"\n  ⚠ {nag}")


def _review_gate(app_id, data, verbose=True):
    """投递前总闸的四项检查（供 cmd_review 和 cmd_submit 共用抽出）。
    verbose=True 时打印每项检查过程（cmd_review 的原行为）；
    verbose=False 只跑检查、收集 blockers，不打印过程（cmd_submit --external 之外的默认路径要看结果时用）。
    返回 (blockers: list[str], resume_pdf: str|None, cl_pdf: str|None)。
    resume_pdf 为 None 表示找不到成品 PDF（此时其余检查仍会跑，但版式检查会失败）。
    """
    def p(s):
        if verbose:
            print(s)

    company_slug = slugify(data["company"])
    role_slug    = slugify(data["role"])
    prefix    = f"{app_id.replace('-', '')}_{company_slug}_{role_slug}_"
    cl_prefix = f"{app_id.replace('-', '')}_{company_slug}_CoverLetter_"
    resume_pdfs = sorted(glob.glob(os.path.join(OUT_DIR, prefix + "*.pdf")))
    cl_pdfs     = sorted(glob.glob(os.path.join(OUT_DIR, cl_prefix + "*.pdf")))

    blockers = []

    if not resume_pdfs:
        p(f"  ✗ 找不到简历成品 PDF（{prefix}*.pdf）— 先跑 build.py make")
        blockers.append("简历成品 PDF 不存在")
        resume_pdf = None
    else:
        resume_pdf = resume_pdfs[-1]
    cl_pdf = cl_pdfs[-1] if cl_pdfs else os.path.join(OUT_DIR, "___none___")

    p("\n[1/4 核对 · 防造假]")
    fc = factcheck_result(app_id)
    if fc == "PASS":
        p("  ✓ review_status.factcheck.result = PASS")
        hash_status, hash_msg = factcheck_hash_check(data)
        if hash_status == "mismatch":
            p(f"  ✗ {hash_msg}")
            blockers.append("factcheck content_hash 不一致（锁定后内容被修改）")
        elif hash_status == "no_hash":
            p(f"  ⚠ {hash_msg}")
        else:
            p("  ✓ content_hash 一致（锁定后未被修改）")
    else:  # None
        p("  ✗ factcheck 未锁定 PASS（review_status.factcheck.result != \"PASS\"）")
        blockers.append("事实核对未锁定 PASS")

    p("\n[2/4 版式检查]")
    if resume_pdf is None:
        layout_problems = []
        rp, ri = layout_check_resume(os.path.join(OUT_DIR, "___none___"))
        cp, ci = layout_check_cl(cl_pdf)
        for i in ri + ci:
            p(f"  · {i}")
        layout_problems = rp + cp
        for pr in layout_problems:
            p(f"  ✗ {pr}")
        blockers.append(f"版式 {len(layout_problems)} 项问题")
    else:
        rp, ri = layout_check_resume(resume_pdf)
        cp, ci = layout_check_cl(cl_pdf)
        for i in ri + ci:
            p(f"  · {i}")
        layout_problems = rp + cp
        for pr in layout_problems:
            p(f"  ✗ {pr}")
        if not layout_problems:
            p("  ✓ 版式检查通过")
        else:
            blockers.append(f"版式 {len(layout_problems)} 项问题")

    p("\n[3/4 质量审核 · JD 匹配度]")
    qr_rs = (data.get("review_status") or {}).get("qualreview") or {}
    rating = qr_rs.get("rating")
    expectation = (qr_rs.get("expectation") or "").strip()
    if not rating:
        p(f"  ✗ review_status.qualreview.rating 未填")
        blockers.append("质量审核未做")
    elif rating not in ("High", "Medium-High", "Medium", "Low"):
        p(f"  ✗ rating = {rating!r} 不是合法 4 级评级")
        blockers.append(f"qualreview rating 非法（{rating}）")
    elif not expectation:
        p(f"  ✗ rating={rating} 但 expectation 期待管理一句话为空")
        blockers.append("qualreview 缺期待管理句")
    else:
        p(f"  ✓ 已审核，匹配度：{rating} · 期待管理：{expectation}")
        # 顺便检查 applications.md Match 列
        try:
            txt = open(APPS_MD, encoding="utf-8").read()
            cols = _table_columns(txt)
            mi = cols.get("Match") if cols else None
            md_rating = None
            if mi is not None:
                for ln in txt.split("\n"):
                    if re.match(rf'\|\s*{re.escape(app_id)}\s*\|', ln):
                        cells = ln.split("|")
                        if mi < len(cells):
                            md_rating = cells[mi].strip()
                        break
            if md_rating and md_rating != rating:
                p(f"  ⚠ applications.md Match 列 = {md_rating!r}，与 yaml rating={rating!r} 不一致")
                blockers.append(f"applications.md Match 漂移（{md_rating} vs {rating}）")
        except Exception as e:
            p(f"  ⚠ 无法校验 applications.md Match 列：{e}")

    p("\n[4/4 JD 留档]")
    jd = data.get("jd") or {}
    jd_raw = (jd.get("raw_text") or "").strip()
    jd_source = (jd.get("source") or "").strip()
    if len(jd_raw) >= 200 and jd_source:
        p(f"  ✓ jd.raw_text {len(jd_raw)} 字符 · source={jd_source}")
    else:
        p(f"  ✗ JD 留档不完整（raw_text {len(jd_raw)} 字符 · source={jd_source or '（空）'}）")
        blockers.append("JD 留档不完整（raw_text 过短或缺 source）")

    return blockers, resume_pdf, cl_pdf


def cmd_review(args):
    app_id = normalize_app_id(args.app)
    yaml_path = os.path.join(JOBS_DIR, f"{app_id}.yaml")
    if not os.path.isfile(yaml_path):
        sys.exit(f"数据文件不存在：{yaml_path}")
    data = yaml.safe_load(open(yaml_path, encoding="utf-8"))

    print(f"== review {app_id} · 投递前总检查 ==")
    blockers, resume_pdf, _ = _review_gate(app_id, data, verbose=True)
    if resume_pdf is None:
        # 保持旧行为：找不到成品 PDF 直接退出，不继续跑版式/质量审核噪音输出
        sys.exit(f"找不到简历成品 PDF — 先跑 build.py make --app {app_id}")

    print("\n" + "=" * 56)
    if not blockers:
        print("  ✅ 四项全绿 —— 可以投递（投递为手动动作）")
        sys.exit(0)
    else:
        print(f"  ⛔ 未通过投递前检查，{len(blockers)} 项待办：")
        for b in blockers:
            print(f"     · {b}")
        print("  → 处理完后重新跑 build.py review。")
        sys.exit(1)


# ============================================================
# 子命令：dashboard —— 单文件只读投递看板
# ============================================================

def _dashboard_json_escape(obj):
    """把 dict/list 安全序列化进 <script> 标签 —— 转义 </script> 防止提前闭合标签。"""
    import json
    return json.dumps(obj, ensure_ascii=False, default=str).replace("</", "<\\/")


def _dashboard_owner_label():
    """看板标题里的「XXX Job Search」姓名，从 master_resume.yaml contact.name 派生。
    读不到就退化为通用文案，不留硬编码人名。"""
    try:
        m = yaml.safe_load(open(MASTER_YAML, encoding="utf-8")) or {}
    except Exception:
        return "Job Search"
    name = display_name_from_contact(m.get("contact"))
    return f"{name} Job Search" if name else "Job Search"


def _dashboard_html(pd, generated_at):
    """从 _collect_pipeline_data() 的结果组装单文件 HTML。纯内联 CSS/JS，零外部请求。"""
    apps = pd["apps"]
    owner_label = _dashboard_owner_label()

    # 告警区：复用 status 的今日行动列表（actions 已含权重+文本）
    actions_sorted = [t for _, t in sorted(pd["actions"], key=lambda x: x[0])]

    # 统计卡
    stats = {
        "applied_total": pd["applied_total"],
        "rejected_count": pd["rejected_count"],
        "interview_count": pd["interview_count"],
        "ready_backlog": pd["ready_backlog"],
        "n_active": pd["n_active"],
        "n_closed": pd["n_closed"],
        "n_alerts": len(actions_sorted),
    }

    # 看板列分组（按 stage；Closed 单独一列）
    kanban_cols = ["Drafting", "Ready", "Applied", "Closed"]
    kanban = {c: [] for c in kanban_cols}
    for a in apps:
        stage = a["stage"] if a["stage"] in kanban_cols else "Drafting"
        kanban[stage].append(a)

    # 趋势：按 Applied 月份 / Closed(Rejected) 月份统计条数
    from collections import Counter
    applied_by_month = Counter()
    rejected_by_month = Counter()
    for a in apps:
        d = _parse_date_safe(a.get("applied") or "")
        if d:
            applied_by_month[d.strftime("%Y-%m")] += 1
        if (a.get("stage") == "Closed" and "rejected" in (a.get("closed_reason") or "").lower()
                or "Rejected" in (a.get("closed_reason") or "")):
            cd = _parse_date_safe(a.get("closed_date") or "")
            if cd:
                rejected_by_month[cd.strftime("%Y-%m")] += 1
    months = sorted(set(applied_by_month) | set(rejected_by_month))
    trend = [{"month": m, "applied": applied_by_month.get(m, 0),
              "rejected": rejected_by_month.get(m, 0)} for m in months]

    data_json = _dashboard_json_escape({
        "generated_at": generated_at,
        "stats": stats,
        "alerts": actions_sorted,
        "apps": apps,
        "kanban_counts": {k: len(v) for k, v in kanban.items()},
        "trend": trend,
    })

    def esc(s):
        return html.escape(str(s if s is not None else "—"))

    def alert_class(text):
        return "alert-red" if text.strip().startswith("⚠") else "alert-yellow"

    alerts_html = "".join(
        f'<div class="alert {alert_class(a)}">{esc(a)}</div>' for a in actions_sorted
    ) or '<div class="alert alert-ok">今日无待办 ✓</div>'

    def kanban_card(a):
        badge = f'<span class="badge">{esc(a["match"])}</span>' if a.get("match") and a["match"] != "—" else ""
        return (
            f'<div class="card">'
            f'<div class="card-top"><strong>{esc(a["app_id"])}</strong>{badge}</div>'
            f'<div class="card-company">{esc(a["company"])}</div>'
            f'<div class="card-role">{esc(a["role"])}</div>'
            f'<div class="card-meta">{esc(a["outcome"])} · '
            f'{(str(a["days_in_state"]) + " 天") if a["days_in_state"] is not None else "—"}</div>'
            f'</div>'
        )

    def kanban_column(name):
        items = kanban[name]
        if name == "Closed":
            visible = ""
            return (
                f'<div class="kcol"><div class="kcol-head">{name}'
                f'<span class="kcol-count">{len(items)}</span></div>'
                f'<button class="expand-btn" onclick="this.nextElementSibling.style.display='
                f"='block';this.style.display='none'\">展开 {len(items)} 条</button>"
                f'<div class="kcol-body" style="display:none">'
                + "".join(kanban_card(a) for a in items) + '</div></div>'
            )
        return (
            f'<div class="kcol"><div class="kcol-head">{name}'
            f'<span class="kcol-count">{len(items)}</span></div>'
            f'<div class="kcol-body">' + "".join(kanban_card(a) for a in items) + '</div></div>'
        )

    kanban_html = "".join(kanban_column(c) for c in kanban_cols)

    def table_row(a):
        cls = "row-closed" if a["stage"] == "Closed" else ""
        days = str(a["days_in_state"]) if a["days_in_state"] is not None else "—"
        return (
            f'<tr class="{cls}">'
            f'<td>{esc(a["app_id"])}</td><td>{esc(a["company"])}</td><td>{esc(a["role"])}</td>'
            f'<td>{esc(a["stage"])}</td><td>{esc(a["outcome"])}</td><td>{esc(a["applied"])}</td>'
            f'<td>{days}</td><td>{esc(a["follow_up_by"])}</td><td>{esc(a["match"])}</td>'
            f'<td>{esc(a["resume_file"])}</td><td>{esc(a["notes"])}</td>'
            f'<td>{esc(a["closed_reason"])}</td><td>{esc(a["closed_date"])}</td>'
            f'</tr>'
        )

    table_headers = ["APP", "Company", "Role", "Stage", "Outcome", "Applied", "天数",
                      "Follow-up", "Match", "Resume File", "Notes", "Closed Reason", "Closed Date"]
    table_head_html = "".join(f'<th onclick="sortTable({i})">{h} ⇅</th>' for i, h in enumerate(table_headers))
    table_body_html = "".join(table_row(a) for a in apps)

    max_month_count = max([1] + [max(t["applied"], t["rejected"]) for t in trend]) if trend else 1

    def trend_bar(t):
        w_applied = round(t["applied"] / max_month_count * 100, 1)
        w_rejected = round(t["rejected"] / max_month_count * 100, 1)
        return (
            f'<div class="trend-row"><div class="trend-month">{esc(t["month"])}</div>'
            f'<div class="trend-bars">'
            f'<div class="trend-bar trend-applied" style="width:{w_applied}%" '
            f'title="投递 {t["applied"]}">{t["applied"] or ""}</div>'
            f'<div class="trend-bar trend-rejected" style="width:{w_rejected}%" '
            f'title="拒信 {t["rejected"]}">{t["rejected"] or ""}</div>'
            f'</div></div>'
        )

    trend_html = "".join(trend_bar(t) for t in trend) or '<div class="muted">暂无按月数据</div>'

    return f"""<title>投递看板 · {esc(owner_label)}</title>
<style>
  :root {{
    --bg: #f7f7f8; --card-bg: #ffffff; --border: #e2e2e6; --text: #1f2328;
    --muted: #6b7280; --red: #dc2626; --red-bg: #fef2f2; --yellow: #b45309;
    --yellow-bg: #fffbeb; --green: #16a34a; --accent: #2563eb;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", Helvetica, Arial, sans-serif;
    background: var(--bg); color: var(--text); margin: 0; padding: 24px; font-size: 14px;
  }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  .subtitle {{ color: var(--muted); font-size: 12px; margin-bottom: 20px; }}
  .stats-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
  .stat-card {{
    background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px;
    padding: 12px 16px; min-width: 130px; flex: 1;
  }}
  .stat-card .num {{ font-size: 22px; font-weight: 700; }}
  .stat-card .label {{ color: var(--muted); font-size: 12px; margin-top: 2px; }}
  section {{
    background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px;
    padding: 16px; margin-bottom: 20px;
  }}
  section h2 {{ font-size: 15px; margin: 0 0 12px; }}
  .alert {{ padding: 8px 10px; border-radius: 6px; margin-bottom: 6px; font-size: 13px; }}
  .alert-red {{ background: var(--red-bg); color: var(--red); }}
  .alert-yellow {{ background: var(--yellow-bg); color: var(--yellow); }}
  .alert-ok {{ background: #f0fdf4; color: var(--green); }}
  .kanban {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
  .kcol {{ background: #fafafa; border: 1px solid var(--border); border-radius: 8px; padding: 10px; min-height: 60px; }}
  .kcol-head {{ font-weight: 600; margin-bottom: 8px; display: flex; justify-content: space-between; }}
  .kcol-count {{ color: var(--muted); font-weight: 400; }}
  .card {{
    background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px;
    padding: 8px 10px; margin-bottom: 8px; font-size: 12.5px;
  }}
  .card-top {{ display: flex; justify-content: space-between; align-items: center; }}
  .badge {{ background: var(--accent); color: #fff; font-size: 10px; padding: 1px 6px; border-radius: 4px; }}
  .card-company {{ font-weight: 600; margin-top: 2px; }}
  .card-role {{ color: var(--muted); }}
  .card-meta {{ color: var(--muted); font-size: 11px; margin-top: 4px; }}
  .expand-btn {{
    width: 100%; padding: 6px; background: #eee; border: 1px solid var(--border);
    border-radius: 6px; cursor: pointer; font-size: 12px; color: var(--text);
  }}
  table {{ border-collapse: collapse; width: 100%; font-size: 12.5px; }}
  th, td {{ border-bottom: 1px solid var(--border); padding: 6px 8px; text-align: left; white-space: nowrap; }}
  th {{ cursor: pointer; user-select: none; color: var(--muted); font-weight: 600; position: sticky; top: 0; background: var(--card-bg); }}
  .table-wrap {{ overflow-x: auto; max-height: 480px; overflow-y: auto; }}
  tr.row-closed {{ color: #9ca3af; }}
  .trend-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }}
  .trend-month {{ width: 64px; font-size: 12px; color: var(--muted); flex-shrink: 0; }}
  .trend-bars {{ flex: 1; display: flex; flex-direction: column; gap: 2px; }}
  .trend-bar {{ height: 14px; border-radius: 3px; font-size: 10px; color: #fff; padding-left: 4px; min-width: 2px; }}
  .trend-applied {{ background: var(--accent); }}
  .trend-rejected {{ background: var(--red); }}
  .muted {{ color: var(--muted); }}
  footer {{ color: var(--muted); font-size: 11px; margin-top: 16px; }}
  code {{ background: #eee; padding: 1px 4px; border-radius: 3px; }}
</style>

<h1>投递看板</h1>
<div class="subtitle">
  只读视图，从 auto-apply/jobs/*.yaml 派生 —— 不提供任何写入功能（登记投递 / 关闭请用
  <code>build.py submit</code> / <code>build.py close</code>）。
  生成时间：{esc(generated_at)} · 重新生成：<code>python3 auto-apply/build.py dashboard</code>
</div>

<div class="stats-row">
  <div class="stat-card"><div class="num">{stats['applied_total']}</div><div class="label">已投总数</div></div>
  <div class="stat-card"><div class="num">{stats['interview_count']} / {stats['rejected_count']}</div><div class="label">面试 / 拒信数</div></div>
  <div class="stat-card"><div class="num">{stats['ready_backlog']}</div><div class="label">Ready 待投</div></div>
  <div class="stat-card"><div class="num">{stats['n_active']}</div><div class="label">在途 Active</div></div>
  <div class="stat-card"><div class="num">{stats['n_alerts']}</div><div class="label">告警数</div></div>
</div>

<section>
  <h2>今日行动 / 告警</h2>
  {alerts_html}
</section>

<section>
  <h2>看板</h2>
  <div class="kanban">{kanban_html}</div>
</section>

<section>
  <h2>全量表格（点列头排序）</h2>
  <div class="table-wrap">
    <table id="app-table">
      <thead><tr>{table_head_html}</tr></thead>
      <tbody>{table_body_html}</tbody>
    </table>
  </div>
</section>

<section>
  <h2>月度趋势（投递 · 拒信）</h2>
  {trend_html}
</section>

<footer>数据仅供参考，回应数等字段识别规则较粗糙，详见 build.py status 输出的字段说明。</footer>

<script id="dashboard-data" type="application/json">{data_json}</script>
<script>
(function() {{
  var sortState = {{}};
  window.sortTable = function(colIdx) {{
    var table = document.getElementById('app-table');
    var tbody = table.tBodies[0];
    var rows = Array.prototype.slice.call(tbody.rows);
    var asc = !sortState[colIdx];
    sortState = {{}};
    sortState[colIdx] = asc;
    rows.sort(function(a, b) {{
      var av = a.cells[colIdx].innerText.trim();
      var bv = b.cells[colIdx].innerText.trim();
      var an = parseFloat(av), bn = parseFloat(bv);
      var cmp;
      if (!isNaN(an) && !isNaN(bn) && /^-?[\\d.]+$/.test(av) && /^-?[\\d.]+$/.test(bv)) {{
        cmp = an - bn;
      }} else {{
        cmp = av.localeCompare(bv, 'zh');
      }}
      return asc ? cmp : -cmp;
    }});
    rows.forEach(function(r) {{ tbody.appendChild(r); }});
  }};
}})();
</script>
"""


def cmd_dashboard(args):
    """生成单文件只读投递看板 HTML（默认落 REPO_ROOT/dashboard.html）。
    铁律：单文件、自包含、零外部请求 —— 不引 CDN/外链字体/外链脚本。"""
    out_path = args.out or os.path.join(REPO_ROOT, "dashboard.html")
    pd = _collect_pipeline_data()
    generated_at = datetime.datetime.now().isoformat(timespec="seconds")
    body = _dashboard_html(pd, generated_at)
    full_html = (
        "<!doctype html>\n<html lang=\"zh\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>投递看板 · {html.escape(_dashboard_owner_label())}</title>"
        "</head><body>\n" + body + "\n</body></html>"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    size_kb = os.path.getsize(out_path) / 1024
    print(f"[OK] dashboard 生成完成：{out_path}（{size_kb:.1f} KB）")
    print(f"  APP 记录数：{len(pd['apps'])} · 告警数：{len(pd['actions'])}")
    print(f"  只读视图 —— 写入请用 build.py submit / close / tracker")


# ============================================================
# 子命令：prompt —— 渲染核对/质检 agent 派发 prompt（占位符注入）
# ============================================================

# 2026-07-07（发布阶段）：prompt 模板去个人化 —— 模板文件本身不含任何具体用户的
# 事实红线/策略规则，个性化内容只活在 workspace.yaml（fact_redlines / strategy_rules），
# 由本命令在渲染时注入。模板文件因此纳入引擎 lint 扫描范围（selftest 第 7 项）。

_PROMPT_TEMPLATES = {
    "verifier": "_verifier_prompt.md",
    "qualreview": "_quality_review_prompt.md",
}
_PROMPT_START = "<!-- PROMPT-START -->"
_PROMPT_END = "<!-- PROMPT-END -->"


def render_agent_prompt(app_id, prompt_type):
    """截取模板 PROMPT-START/END 区间并注入占位符，返回可直接派发的 prompt 文本。"""
    tpl_name = _PROMPT_TEMPLATES[prompt_type]
    tpl_path = os.path.join(JOBS_DIR, tpl_name)
    if not os.path.isfile(tpl_path):
        sys.exit(f"模板不存在：{tpl_path}")
    text = open(tpl_path, encoding="utf-8").read()
    if _PROMPT_START not in text or _PROMPT_END not in text.split(_PROMPT_START, 1)[1]:
        sys.exit(f"模板缺少 {_PROMPT_START} / {_PROMPT_END} 标记：{tpl_path}")
    body = text.split(_PROMPT_START, 1)[1].split(_PROMPT_END, 1)[0].strip()

    cfg = load_workspace_config()

    def numbered(items, empty_hint):
        if not items:
            return f"（本工作区未在 workspace.yaml 配置此段 —— {empty_hint}）"
        return "\n".join(f"{i}. {s}" for i, s in enumerate(items, start=1))

    try:
        candidate = (load_master().get("contact") or {}).get("name") or ""
    except SystemExit:
        candidate = ""
    if not candidate:
        candidate = "（候选人姓名未填写：master_resume.yaml contact.name）"

    subs = {
        "{{APP_ID}}": app_id,
        "{{APP_ID 去横线}}": app_id.replace("-", ""),
        "{{SSOT_PATH}}": os.path.relpath(SSOT, REPO_ROOT),
        "{{CANDIDATE_NAME}}": candidate,
        "{{FACT_REDLINES}}": numbered(cfg["fact_redlines"], "仅执行上方通用核对清单"),
        "{{STRATEGY_RULES}}": numbered(cfg["strategy_rules"], "无工作区专属策略规则"),
    }
    for k, v in subs.items():
        body = body.replace(k, v)

    leftover = sorted(set(re.findall(r"\{\{[^\n{}]+\}\}", body)))
    if leftover:
        sys.exit(f"模板存在未注入的占位符：{', '.join(leftover)}（检查 {tpl_name} 与本函数 subs 表）")
    return body


def cmd_prompt(args):
    """渲染派发 prompt。stdout 只输出纯 prompt（可直接整段作为 Agent 的 prompt），
    渲染信息走 stderr，避免污染复制内容。"""
    app_id = normalize_app_id(args.app)
    yp = os.path.join(JOBS_DIR, f"{app_id}.yaml")
    if not os.path.isfile(yp):
        sys.exit(f"数据文件不存在：{yp}（先跑 build.py prep）")
    body = render_agent_prompt(app_id, args.type)
    print(f"[prompt] {args.type} · {app_id} · 模板 {_PROMPT_TEMPLATES[args.type]} "
          f"+ workspace.yaml 注入（fact_redlines/strategy_rules）", file=sys.stderr)
    print(f"[prompt] 下一步：把下方 stdout 全文作为 Agent（general-purpose）的 prompt 派发",
          file=sys.stderr)
    print(body)


# ============================================================
# 子命令：check-update —— 引擎更新检查
# ============================================================
# 隐私边界：这是引擎里**唯一**会主动联网的命令，且只在用户显式运行时联网。
# status / selftest 的过期提醒是纯本地的（只读时间戳文件），绝不隐式发请求。

# 引擎上游仓库（GitHub owner/repo）。
_UPSTREAM_REPO = "YizhuangLin/job-application"  # engine-lint-allow: 上游仓库地址是项目署名，不是用户个人数据


def _update_stamp_path():
    """时间戳文件放引擎目录旁（更新检查关心的是引擎本体，不是某个工作区）。"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".last_update_check")


def _write_update_stamp():
    try:
        with open(_update_stamp_path(), "w", encoding="utf-8") as f:
            f.write(datetime.date.today().isoformat())
    except Exception:
        pass  # 写不进（只读目录等）只是丢失提醒节流，不影响功能


def update_check_nag():
    """纯本地的更新检查过期提醒。返回提醒文本，或 None（30 天内检查过）。不联网。"""
    try:
        ts = open(_update_stamp_path(), encoding="utf-8").read().strip()
        days = (datetime.date.today() - datetime.date.fromisoformat(ts)).days
    except Exception:
        return ("从未检查过引擎更新 —— 需要时跑 python3 auto-apply/build.py check-update"
                "（引擎唯一联网命令，手动触发）")
    if days > 30:
        return f"距上次引擎更新检查已 {days} 天 —— 可跑 python3 auto-apply/build.py check-update"
    return None


def _parse_semver(s):
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", (s or "").strip().lstrip("vV"))
    return tuple(int(x) for x in m.groups()) if m else None


def cmd_check_update(args):
    """对比本地 ENGINE_VERSION 与上游最新版本，打印结论与更新方法。
    若引擎目录位于上游仓库的 git clone 内（origin 指向上游），改用 git fetch 对比。
    任何网络失败都优雅降级 —— 离线不影响引擎使用。"""
    print("== check-update ==")
    print(f"  本地引擎版本：{ENGINE_VERSION}")

    # git clone 模式：从引擎目录向上找 .git，且 origin 指向上游仓库
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(3):
        if os.path.isdir(os.path.join(d, ".git")):
            try:
                url = subprocess.run(["git", "-C", d, "remote", "get-url", "origin"],
                                     capture_output=True, text=True, timeout=10).stdout.strip()
            except Exception:
                url = ""
            if _UPSTREAM_REPO in url:
                print(f"  安装方式：上游仓库 git clone（{d}）→ 用 git 对比")
                try:
                    subprocess.run(["git", "-C", d, "fetch", "--quiet", "origin"],
                                   timeout=60, check=True)
                    ref = subprocess.run(["git", "-C", d, "rev-parse", "--abbrev-ref", "origin/HEAD"],
                                         capture_output=True, text=True, timeout=10).stdout.strip() \
                          or "origin/master"
                    behind = subprocess.run(
                        ["git", "-C", d, "rev-list", "--count", f"HEAD..{ref}"],
                        capture_output=True, text=True, timeout=10).stdout.strip()
                    _write_update_stamp()
                    if behind == "0":
                        print(f"  ✓ 已是最新（与 {ref} 无差异）")
                    else:
                        print(f"  ⚠ 落后 {ref} {behind} 个提交")
                        print(f"  下一步：git -C {d} pull，然后把 auto-apply/ 重新同步进工作区")
                except Exception as e:
                    print(f"  ✗ git fetch 失败（离线/网络受限？）：{type(e).__name__}: {str(e)[:120]}")
                    print("  → 不影响使用；有网络时再跑本命令")
                return
            break  # 有 .git 但不是上游 clone（多半是工作区自己的仓库）→ 走 API 模式
        d = os.path.dirname(d)

    # API 模式：GitHub releases/latest，失败回退默认分支（HEAD ref，分支名无关）SKILL.md frontmatter
    import json

    def fetch(url):
        # 优先 curl：走系统信任库，避开 macOS 系统 Python 缺证书链（CERTIFICATE_VERIFY_FAILED）的坑
        ua = f"resume-pipeline-engine/{ENGINE_VERSION}"
        if shutil.which("curl"):
            r = subprocess.run(["curl", "-fsSL", "--max-time", "10", "-H", f"User-Agent: {ua}", url],
                               capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                return r.stdout
            raise RuntimeError(f"curl exit {r.returncode}")
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.read().decode("utf-8", "replace")

    latest, source = None, ""
    try:
        tag = json.loads(fetch(
            f"https://api.github.com/repos/{_UPSTREAM_REPO}/releases/latest")).get("tag_name", "")
        latest, source = _parse_semver(tag), f"GitHub release {tag}"
    except Exception:
        pass
    if latest is None:
        try:
            m = re.search(r"^version:\s*([0-9][0-9.]*)",
                          fetch(f"https://raw.githubusercontent.com/{_UPSTREAM_REPO}/HEAD/SKILL.md"),
                          re.M)
            if m:
                latest, source = _parse_semver(m.group(1)), "默认分支 SKILL.md frontmatter"
        except Exception as e:
            print(f"  ✗ 无法联网获取上游版本（离线/网络受限？）：{type(e).__name__}: {str(e)[:120]}")
            print("  → 不影响使用；有网络时再跑本命令")
            return
    if latest is None:
        print("  ✗ 上游版本号解析失败（releases 无 SemVer tag 且 SKILL.md 无 version 行）")
        return

    _write_update_stamp()
    local = _parse_semver(ENGINE_VERSION)
    print(f"  上游最新版本：{'.'.join(map(str, latest))}（来源：{source}）")
    if local is None or latest > local:
        print("  ⚠ 有新版本可用")
        print(f"  变更内容：https://github.com/{_UPSTREAM_REPO}/blob/HEAD/CHANGELOG.md")
        print(f"  更新方法：从 https://github.com/{_UPSTREAM_REPO} 获取新版 auto-apply/ 覆盖本地"
              "（workspace.yaml / SSOT / jobs 数据都在工作区，不会被覆盖）")
    elif latest == local:
        print("  ✓ 已是最新")
    else:
        print("  ✓ 本地版本比上游发布版新（开发中版本，无需动作）")


# ============================================================
# 子命令：selftest —— 环境 + 数据自检
# ============================================================

def engine_lint_patterns():
    """收集个人硬编码扫描模式（2026-07-07 发布阶段：模式不再内置在引擎代码里 ——
    内置列表本身就是维护者的个人信息）。来源两处，合并去重：
      1. workspace.yaml `lint_patterns`（显式列表：邮箱前缀、电话片段、用户名等）
      2. master_resume.yaml contact.name 派生：拆出 ≥ 4 个字母的 token，
         按「原样 + 首字母大写」两种写法加入（≥4 是为了避开 Lin→inline 这类误伤）。
    返回 list[str]；空列表 = 无可扫模式（裸工作区），由调用方决定怎么提示。"""
    pats = list(load_workspace_config()["lint_patterns"])
    try:
        name = (load_master().get("contact") or {}).get("name") or ""
    except (Exception, SystemExit):
        name = ""
    for tok in re.findall(r"[A-Za-z]{4,}", name):
        pats += [tok, tok.capitalize()]
    seen, out = set(), []
    for p in pats:
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def engine_lint():
    """扫描引擎文件（auto-apply/*.py + auto-apply/templates/* + jobs/ 下的 prompt 模板）
    里的个人硬编码字符串。
    2026-07-07 新增（阶段3 可复制性）：引擎代码不得写死任何具体用户的姓名/邮箱/电话，
    这些必须从 master_resume.yaml / workspace.yaml 派生。
    2026-07-07 发布阶段扩展：jobs/_verifier_prompt.md / _quality_review_prompt.md 已改为
    占位符模板（事实红线迁入 workspace.yaml，由 build.py prompt 注入），因此纳入扫描 ——
    模板里再出现个人事实即回归。

    返回 list[str]，每条 "相对路径:行号: 命中模式 | 行内容"。空列表 = 干净。
    """
    engine_dir = os.path.dirname(os.path.abspath(__file__))
    paths = sorted(glob.glob(os.path.join(engine_dir, "*.py"))) + \
            sorted(glob.glob(os.path.join(engine_dir, "templates", "*"))) + \
            [os.path.join(engine_dir, "jobs", t) for t in sorted(_PROMPT_TEMPLATES.values())]
    # templates 目录下可能含子目录（如 docx_skeleton/），用 glob 只取一层文件；
    # 子目录内文件另行遍历一层，覆盖 templates/*/*  但不递归更深。
    paths += sorted(glob.glob(os.path.join(engine_dir, "templates", "*", "*")))

    pats = engine_lint_patterns()
    if not pats:
        return []
    hits = []
    pattern = re.compile("|".join(re.escape(p) for p in pats))
    for path in paths:
        if not os.path.isfile(path):
            continue
        try:
            text = open(path, encoding="utf-8").read()
        except Exception:
            continue
        rel = os.path.relpath(path, os.path.dirname(engine_dir))
        lines = text.split("\n")
        for i, line in enumerate(lines, start=1):
            m = pattern.search(line)
            if not m:
                continue
            # 允许显式标记的向后兼容字面量（如 legacy SSOT 文件名常量定义本身）——
            # 标记必须写在常量定义那一行，且只免除那一行，不免除同名变量的其他使用处。
            if "engine-lint-allow" in line or (i >= 2 and "engine-lint-allow" in lines[i - 2]):
                continue
            hits.append(f"{rel}:{i}: 命中 {m.group(0)!r} | {line.strip()[:120]}")
    return hits


def _selftest_print(ok, label, detail=""):
    mark = "✓" if ok is True else ("⚠" if ok == "warn" else "✗")
    line = f"  {mark} {label}"
    if detail:
        line += f"（{detail}）"
    print(line)


def cmd_selftest(args):
    """环境 + 数据自检。退出码 0=全过 / 1=有 FAIL。"""
    print("== selftest ==")
    all_pass = True

    # ---- 1. 系统依赖 ----
    print("\n[1] 系统依赖")
    for tool in ("pdfinfo", "pdftotext"):
        found = shutil.which(tool) is not None
        _selftest_print(found, f"{tool} 存在")
        if not found:
            all_pass = False

    # ---- 2. 渲染路径真实可用 ----
    print("\n[2] 渲染路径真实可用")
    playwright_ok = False
    try:
        from playwright.sync_api import sync_playwright
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                browser.close()
            playwright_ok = True
            _selftest_print(True, "Playwright + Chromium 可启动")
        except Exception as e:
            _selftest_print(False, "Playwright 已安装但 Chromium 启动失败",
                             f"{type(e).__name__}: {str(e)[:150]}")
            all_pass = False
    except ImportError:
        _selftest_print(False, "Playwright 未安装（import 失败）")
        all_pass = False

    weasyprint_ok = False
    try:
        import weasyprint  # noqa: F401
        weasyprint_ok = True
        _selftest_print(True, "WeasyPrint 可 import（回退路径可用）")
    except Exception as e:
        if playwright_ok:
            _selftest_print("warn", "WeasyPrint 不可用",
                             "回退路径不可用（本机已知缺 native 库），Playwright 为唯一渲染路径")
        else:
            _selftest_print(False, "WeasyPrint 不可用且 Playwright 也不可用 —— 无任何渲染路径",
                             f"{type(e).__name__}: {str(e)[:150]}")
            all_pass = False

    # ---- 3. 端到端渲染 ----
    print("\n[3] 端到端渲染")
    if not playwright_ok and not weasyprint_ok:
        _selftest_print(False, "跳过端到端渲染 —— 无可用渲染引擎")
        all_pass = False
    else:
        tmp_dir = None
        try:
            master = load_master()
            content = {
                "contact": master["contact"],
                "summary": master["summary"],
                "experience": [
                    {"title": e["title"], "date": e["date"], "org_line": e["org_line"],
                     "bullets": e["bullets"]}
                    for e in master["experience"]
                ],
                "education": master["education"],
                "skills": [{"label": s["label"], "body": s["body"]} for s in master["skills"]],
            }
            import html_render
            tmp_dir = tempfile.mkdtemp(prefix="selftest_")
            pdf_path = os.path.join(tmp_dir, "selftest_resume.pdf")
            html_render.render_resume(content, pdf_path)
            layout_problems, layout_info = layout_check_resume(pdf_path)
            if layout_problems:
                _selftest_print(False, "端到端渲染 + 版式检查未全过",
                                 "; ".join(layout_problems))
                all_pass = False
            else:
                _selftest_print(True, "端到端渲染 + layout_check_resume 全过",
                                 "; ".join(layout_info))
        except Exception as e:
            _selftest_print(False, "端到端渲染异常", f"{type(e).__name__}: {str(e)[:200]}")
            all_pass = False
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    # ---- 4. 数据完整性 ----
    print("\n[4] 数据完整性")
    try:
        cfg = load_workspace_config()
        max_pages = cfg["resume_layout"]["max_pages"]
        if isinstance(max_pages, int) and max_pages > 0:
            _selftest_print(True, f"workspace.yaml 可解析，max_pages={max_pages}")
        else:
            _selftest_print(False, f"workspace.yaml max_pages 非正整数：{max_pages!r}")
            all_pass = False
    except Exception as e:
        _selftest_print(False, "workspace.yaml 解析异常", f"{type(e).__name__}: {e}")
        all_pass = False

    try:
        load_master()
        _selftest_print(True, "master_resume.yaml 结构断言通过")
    except SystemExit as e:
        _selftest_print(False, "master_resume.yaml 结构断言失败", str(e)[:200])
        all_pass = False
    except Exception as e:
        _selftest_print(False, "master_resume.yaml 解析异常", f"{type(e).__name__}: {e}")
        all_pass = False

    yaml_paths = _all_app_yaml_paths()
    n_ok, n_legacy_skip, n_bad = 0, 0, []
    for yp in yaml_paths:
        app_id = os.path.splitext(os.path.basename(yp))[0]
        d = _load_yaml_soft(yp)
        if d is None:
            n_bad.append(f"{app_id}（解析失败）")
            continue
        if d.get("legacy"):
            n_legacy_skip += 1
            continue
        if "resume" not in d:
            n_bad.append(f"{app_id}（非 legacy 但缺 resume 段）")
            continue
        if d.get("schema_version") != SCHEMA_VERSION:
            n_bad.append(f"{app_id}（schema_version={d.get('schema_version')} 不匹配 {SCHEMA_VERSION}）")
            continue
        n_ok += 1
    if n_bad:
        _selftest_print(False, f"jobs/APP-*.yaml 校验：{n_ok} 正常 / {n_legacy_skip} legacy 跳过 / "
                                f"{len(n_bad)} 异常", "; ".join(n_bad[:10]))
        all_pass = False
    else:
        _selftest_print(True, f"jobs/APP-*.yaml 校验：{n_ok} 正常 / {n_legacy_skip} legacy 跳过（共 {len(yaml_paths)} 份）")

    # ---- 5. tracker 幂等 ----
    print("\n[5] tracker 幂等")
    try:
        before = open(APPS_MD, encoding="utf-8").read()
        regenerate_tracker_tables()
        after1 = open(APPS_MD, encoding="utf-8").read()
        regenerate_tracker_tables()
        after2 = open(APPS_MD, encoding="utf-8").read()
        if after1 == after2:
            _selftest_print(True, "两次 regenerate_tracker_tables 结果一致")
            if after1 != before:
                # 内容变了但幂等 —— 说明 tracker 本来就没跑过全，属正常（用当前状态，不算 FAIL）
                with open(APPS_MD, "w", encoding="utf-8") as f:
                    f.write(after1)
            else:
                with open(APPS_MD, "w", encoding="utf-8") as f:
                    f.write(before)
        else:
            _selftest_print(False, "两次 regenerate_tracker_tables 结果不一致 —— tracker 非幂等")
            all_pass = False
            with open(APPS_MD, "w", encoding="utf-8") as f:
                f.write(before)
    except Exception as e:
        _selftest_print(False, "tracker 幂等检查异常", f"{type(e).__name__}: {e}")
        all_pass = False
        try:
            with open(APPS_MD, "w", encoding="utf-8") as f:
                f.write(before)
        except Exception:
            pass

    # ---- 6. 文档一致 ----
    print("\n[6] 文档一致（sync_check.py）")
    try:
        sync_check_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_check.py")
        r = subprocess.run([sys.executable, sync_check_path], capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            _selftest_print(True, "sync_check.py 通过（exit 0）")
        else:
            _selftest_print("warn", "sync_check.py 报告提醒级问题（exit != 0，不计入 FAIL）",
                             f"exit={r.returncode}")
    except Exception as e:
        _selftest_print("warn", "sync_check.py 调用异常（不计入 FAIL）", f"{type(e).__name__}: {e}")

    # ---- 7. 引擎 lint（个人硬编码扫描） ----
    print("\n[7] 引擎 lint（个人硬编码扫描）")
    try:
        lint_pats = engine_lint_patterns()
        if not lint_pats:
            _selftest_print("warn", "无可扫描模式，跳过扫描",
                            "workspace.yaml lint_patterns 为空且母版姓名未填；"
                            "建档后把姓名/邮箱前缀/电话片段等写进 lint_patterns 以启用防护")
        else:
            hits = engine_lint()
            if hits:
                _selftest_print(False, f"引擎文件含 {len(hits)} 处个人硬编码字符串",
                                 "; ".join(hits[:10]))
                all_pass = False
            else:
                _selftest_print(True, "引擎文件（*.py + templates/* + jobs/ prompt 模板）"
                                      f"无个人硬编码字符串（{len(lint_pats)} 个扫描模式）")
    except Exception as e:
        _selftest_print(False, "引擎 lint 扫描异常", f"{type(e).__name__}: {e}")
        all_pass = False

    # ---- 8. 引擎更新提醒（纯本地时间戳，不联网，只提示不计入 FAIL） ----
    nag = update_check_nag()
    if nag:
        print("\n[8] 引擎更新提醒")
        _selftest_print("warn", nag)

    print("\n" + "=" * 56)
    if all_pass:
        print("  ✅ selftest 全过")
        sys.exit(0)
    else:
        print("  ⛔ selftest 有 FAIL 项，见上方 ✗ 标记")
        sys.exit(1)


# ============================================================
# 子命令：init —— 新工作区脚手架（阶段3 可复制性）
# ============================================================

_INIT_WORKSPACE_YAML = """\
# ============================================================
# workspace.yaml — 工作区配置层
# ------------------------------------------------------------
# 这是配置层：引擎（build.py 等）从这里读取"这是谁的求职"的个性化设定。
# 规则调整 = 改这里一处，不改引擎代码。
# ============================================================

resume_layout:
  # 简历页数硬上限。1 = 单页铁律（大多数非学术岗位的行业惯例，默认值）。
  # 学术/科研/博士类岗位的 CV 惯例是多页 → 可改 2 或更大。
  # 约定：这里的值填一次就是最终答案——建档时想清楚这个问题，
  # 此后任何环节都不再重复确认、不再逐次提醒。
  max_pages: 1

  # 超页处理策略（唯一合法值 cut_content）：
  #   cut_content = 只允许缩减内容 —— 删低价值 bullet / 精简 rewritten 文案，
  #   按 APP yaml 的 page_compression.steplist 优先级从低价值内容删起。
  #   禁止用缩小字号、行距、边距等排版手段换取页数。
  overflow_strategy: cut_content

# 路径配置段：引擎默认读 Context_Master.md / applications.md（相对仓库根）。
# 如果你想用别的文件名，在这里覆盖。
paths:
  ssot: "Context_Master.md"
  applications: "applications.md"

# ------------------------------------------------------------
# 核对/质检 prompt 的工作区专属注入段。
# `build.py prompt --app APP### --type verifier|qualreview` 渲染 prompt 模板时，
# 把下面两段逐条注入 {{FACT_REDLINES}} / {{STRATEGY_RULES}} 占位符。
# 建档后随投递复盘逐步沉淀：每发现一次「简历写了 SSOT 没有的东西」，
# 就把对应判定标准固化成一条，写成核对 agent 可直接执行的一句话。
# ------------------------------------------------------------

# 事实红线：本工作区专属的「出现即问题」硬性核对项。
# 例：曾写错过的客户名拼写、不可降写的职级、货币单位规则。
fact_redlines: []

# 简历策略规则：跨岗位统一的取舍口径（写成含判定标准的一句话）。
# 例：summary 是否允许年限数字、大额预算金额对低薪岗位的取舍。
strategy_rules: []

# 引擎 lint 扫描模式（selftest 第 7 项）：防止你的个人信息被硬编码进引擎代码/模板。
# 母版 contact.name 里 ≥ 4 字母的 token 会自动派生，这里补充邮箱前缀、电话片段、
# 用户名等其他标识（留空 + 母版姓名未填时，lint 跳过并提示）。
lint_patterns: []
"""

_INIT_SSOT_MD = """\
# 上下文总记录（Master Reference / SSOT）

> 这是简历生成系统的事实唯一来源（Single Source of Truth）。
> 所有简历改写、核对 agent 判断"是否属实"，都以本文件为准。
> 事实变更 → 先改这里 + 追加下方「变更日志」一行，再考虑是否同步 `master_resume.yaml`。

---

## 一、个人基本档案

<!--
填写指引：
- 姓名（简历头部展示用的完整拼写，含惯用昵称可用括号标注，如 "FIRSTNAME (NICK) LASTNAME"）
- 联系方式：电话 / 邮箱 / 城市 / портfolio 或 LinkedIn（如有）
- 工作授权状态（是否需要 sponsorship，对目标市场很重要）
-->

- 姓名：
- 电话：
- 邮箱：
- 城市：
- Portfolio / LinkedIn：
- 工作授权：

---

## 二、完整工作经历

<!--
填写指引：
- 按时间倒序列出每段经历：职位 / 公司 / 起止时间 / 地点。
- 每段经历下列出可量化成果的 bullet（数字优先：增长百分比、流量倍数、
  预算规模、团队人数、时间节省等）——核对 agent 会逐条核对这里的数字。
- 标注清楚哪些是历史事实（客户名/职级/预算数字），生成简历时这些不可篡改。
-->

### 简历生成策略统一口径（建档时先定好，写在这里避免每次重复讨论）

<!--
建议在这里明确团队的通用规则，例如：
1. summary 是否允许写年限数字
2. 货币单位统一用哪种（尤其跨国经历换算）
3. 双语/多语能力句是否默认保留，按 JD 增删的判断标准
-->

---

## 三、核心项目经历

<!-- 独立于工作经历之外的项目（开源贡献、个人项目、side project 等），
     有则填，无则删除本节。 -->

---

## 四、教育背景

<!-- 学位 / 专业 / 学校 / 起止时间，按时间倒序 -->

---

## 五、技能评级（分层）

<!--
填写指引：按熟练度分层列出技能，例如：
- Expert / Advanced：日常主力使用、可独立解决复杂问题
- Proficient：能独立完成常规任务
- Familiar：接触过、了解基础用法

核对 agent 会用这张表核对简历里的措辞（如 "expert in X"）是否与这里的
评级一致——评级为 familiar 的技能不应在简历里被包装成 expert。
-->

| 技能 | 熟练度 | 备注 |
|---|---|---|
|  |  |  |

---

## 变更日志（Change Log）

> `build.py fact` 命令在这张表最后一行之后机械追加一行，并刷新文末「最后更新」日期。
> 事实变更本身仍需要人读判断落在哪一节、怎么措辞——这个命令只负责留痕。

| 日期 | 字段/变更项 | 旧值→新值 | Tier2已同步 | Tier3状态 |
|---|---|---|---|---|
|  |  |  |  |  |

---

最后更新：
"""

_INIT_MASTER_RESUME_YAML = """\
# ============================================================
# master_resume.yaml — 简历母版（结构化内容）
# ------------------------------------------------------------
# 这是纯内容，不含排版；排版由 auto-apply/templates/ 下的模板文件负责。
# 与 SSOT（paths.ssot 指向的文件）并存：SSOT 是事实库，本文件是简历
# 素材的结构化版本。事实变更仍先改 SSOT，再考虑是否同步到这里。
#
# 特殊字符须保真：× (乘号 U+00D7) · – (en-dash) · — (em-dash)
#   · (中点分隔符 U+00B7) · ' (curly apostrophe U+2019)
# ============================================================
schema_version: 2

contact:
  name: ""              # 简历头部展示姓名，如 "JANE DOE" 或 "JANE (JJ) DOE"
  line: ""              # 联系行一整行，如 "555-123-4567  ·  jane@example.com  ·  City, ST"

summary: ""              # 简历 Summary 段。建议成果/角色导向开头，不写具体年限数字（跨岗位改写规则见 SSOT 第二节）

experience:
  # 每段经历一个 id（稳定 key，改写时按 id 引用，不要改动）
  - id: "example_role"
    title: ""            # 职位
    date: ""             # 如 "Jan 2023 – Present"
    org_line: ""         # 如 "Company Name  ·  Contract  ·  City, ST"
    bullets:
      - ""                # 可量化成果优先；多条按重要性排序

education:
  - degree: ""
    date: ""
    org_line: ""

skills:
  - label: "Development:"
    body: ""
  - label: "Tools:"
    body: ""
  - label: "Languages:"
    body: ""
    role: "languages"     # 语义标记：仅 Languages 行需要，用于 bilingual_line.keep=false 时隐藏本行

meta:
  # 如果 summary 里含双语/多语能力句，把原文精确复制到这里；
  # bilingual_line.keep=false 时 make 按此精确句删除，不用正则盲扫。
  bilingual_sentence: ""
"""

_INIT_APPLICATIONS_MD = """\
# Application Tracker

> **Maintained by:** build.py tracker（区间由 AUTO-GENERATED 标记，勿手编辑）
> **Backend:** flat markdown (default, zero-setup)
> **Last updated:**

---

## Active Applications

<!-- AUTO-GENERATED: build.py tracker（勿手编辑，改 yaml 后重跑）-->
| APP | Company | Role | Category | Location | Applied | Stage | Outcome | Match | Follow-up by | Resume File | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|

---

## Closed / Skipped

<!-- AUTO-GENERATED: build.py tracker（勿手编辑，改 yaml 后重跑）-->
| APP | Company | Role | Reason | Date |
|---|---|---|---|---|

---

## Stage Definitions

- **Drafting** — resume being generated / reviewed (build.py prep→make pipeline)
- **Ready** — resume generated, not yet submitted
- **Applied** — submitted, waiting for first response
- **In Conversation** — HR screen scheduled or in progress
- **Interview** — hiring manager / panel interview confirmed or completed
- **Offer** — offer received, evaluating or negotiating
- **Closed** — role filled, rejected, withdrawn, or offer accepted

---

## Response Rate Log

> Trigger a diagnostics review when: 10+ Applied rows with fewer than 2 responses.

| Date | Applied count | Responses | Rate | Action |
|---|---|---|---|---|
"""

_INIT_GITIGNORE = """\
__pycache__/
dashboard.html
.DS_Store
.last_update_check
"""


def cmd_init(args):
    """新工作区脚手架。生成 workspace.yaml / SSOT 模板 / master_resume.yaml 骨架 /
    applications.md 空表骨架 / auto-apply/jobs · applications 目录 / .gitignore。

    目标目录须为空或不含 workspace.yaml（已有则拒绝，防止误覆盖现有工作区）。
    注意：init 只在目标目录生成模板骨架，不生成 build.py 本体——目标目录复用
    某处已有的 build.py（通过 RESUME_WORKSPACE 环境变量指向目标目录运行）。
    模板内容不含任何具体个人信息（占位骨架），符合本引擎"可复制给任何人用"的目标。
    """
    target_dir = os.path.abspath(getattr(args, "dir", None) or os.getcwd())
    os.makedirs(target_dir, exist_ok=True)

    ws_path = os.path.join(target_dir, "workspace.yaml")
    if os.path.isfile(ws_path):
        sys.exit(f"[BLOCKED] {ws_path} 已存在 —— init 拒绝覆盖现有工作区。"
                 f"\n  → 换一个空目录，或手动确认后自行删除 workspace.yaml 再重跑")

    entries = [e for e in os.listdir(target_dir) if not e.startswith(".")]
    if entries:
        print(f"  ⚠ {target_dir} 非空（含 {len(entries)} 项），但未发现 workspace.yaml，继续生成。"
              f"\n    如有文件名冲突会直接覆盖，建议在真正空目录里跑 init。")

    def write_new(rel_path, content):
        full = os.path.join(target_dir, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return full

    write_new("workspace.yaml", _INIT_WORKSPACE_YAML)
    write_new("Context_Master.md", _INIT_SSOT_MD)
    write_new("master_resume.yaml", _INIT_MASTER_RESUME_YAML)
    write_new("applications.md", _INIT_APPLICATIONS_MD)
    write_new(".gitignore", _INIT_GITIGNORE)
    os.makedirs(os.path.join(target_dir, "auto-apply", "jobs"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "auto-apply", "applications"), exist_ok=True)

    print(f"[OK] 新工作区脚手架已生成：{target_dir}")
    print("  已创建：")
    print("    workspace.yaml（配置层：页数上限 + paths 段）")
    print("    Context_Master.md（SSOT 模板，按章节骨架 + 填写指引填）")
    print("    master_resume.yaml（母版骨架，schema_version 2）")
    print("    applications.md（空表骨架）")
    print("    .gitignore")
    print("    auto-apply/jobs/ · auto-apply/applications/")
    print()
    print("  下一步：")
    print("    1. 填 Context_Master.md（履历事实 SSOT）与 master_resume.yaml（结构化简历素材）")
    print("       —— 可以自己填，也可以让 AI 访谈式建档（读 Context_Master.md 骨架逐节问你）")
    print(f"    2. 跑自检：RESUME_WORKSPACE={target_dir} python3 <build.py 所在路径> selftest")
    print(f"    3. 第一次生成：RESUME_WORKSPACE={target_dir} python3 <build.py 所在路径> "
          f"prep --company \"X\" --role \"Y\" --jd-file jd.txt")
    print()
    print("  说明：本目录没有独立的 build.py 本体——引擎是共享的，用 RESUME_WORKSPACE")
    print("  环境变量指向本目录即可让引擎把这里当仓库根（find_repo_root 优先探测")
    print("  RESUME_WORKSPACE，其次逐级向上找 workspace.yaml）。")


# ============================================================
# CLI
# ============================================================

def main():
    ap = argparse.ArgumentParser(description="JD 驱动的简历生成系统（母版 YAML 化）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prep", help="生成 APP###.yaml 草稿")
    p.add_argument("--app")
    p.add_argument("--company", required=True)
    p.add_argument("--role", required=True)
    p.add_argument("--reuse", action="store_true", help="允许对已存在 APP 重新生成数据文件")
    p.add_argument("--force", action="store_true", help="强制覆盖已填阶段2 内容的 YAML")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--jd-url")
    g.add_argument("--jd-file")

    v = sub.add_parser("verify", help="检查阶段2 完整性 + 核对状态")
    v.add_argument("--app", required=True)

    pr = sub.add_parser("prompt", help="渲染核对/质检 agent 派发 prompt"
                        "（模板占位符 + workspace.yaml fact_redlines/strategy_rules 注入，stdout 纯 prompt）")
    pr.add_argument("--app", required=True)
    pr.add_argument("--type", required=True, choices=list(_PROMPT_TEMPLATES),
                    help="verifier=事实核对 agent · qualreview=质量审核 agent")

    fp = sub.add_parser("factcheck-pass",
                        help="用户完成 factcheck 裁决后锁定 PASS（写 yaml review_status.factcheck）")
    fp.add_argument("--app", required=True)
    fp.add_argument("--report", required=True,
                    help="核对 agent 报告文本文件路径（首个非空行须是 RESULT: PASS|NEEDS-USER）")
    fp.add_argument("--note", help="（可选）裁决摘要，记入 yaml 留痕")

    qp = sub.add_parser("qualreview-pass",
                        help="qualreview agent 跑完后写 yaml + applications.md Match 列")
    qp.add_argument("--app", required=True)
    qp.add_argument("--rating", required=True,
                    choices=["High", "Medium-High", "Medium", "Low"],
                    help="4 级匹配度评级")
    qp.add_argument("--expectation", required=True,
                    help="期待管理一句话（会同步进 applications.md）")
    qp.add_argument("--report", help="（可选）qualreview agent 报告文本文件路径，"
                    "首个非空行须是 RATING: <4级> 且与 --rating 一致")

    m = sub.add_parser("make", help="生成简历+CL（默认只留 PDF）")
    m.add_argument("--app", required=True)
    m.add_argument("--skip-verify", action="store_true", help="跳过核对门禁（测试用，产物打 _UNVERIFIED）")
    m.add_argument("--dry-run", action="store_true", help="预演内容组装，不打包")
    m.add_argument("--docx", action="store_true", help="同时保留 docx（默认只留 PDF）")

    rv = sub.add_parser("review", help="投递前总闸：核对/版式/质量")
    rv.add_argument("--app", required=True)

    hv = sub.add_parser("harvest", help="从已 factcheck PASS 的 APP###.yaml 提取 rewritten 入库 rewrite_library.yaml")
    hv.add_argument("--app", required=True)
    hv.add_argument("--tags", help="逗号分隔的侧重标签，如 seo,sem（写入 snippet.angle）")
    hv.add_argument("--allow-legacy", action="store_true",
                    help="放行 content_hash 缺失的旧版 PASS 锁定（默认拒绝）")

    sub.add_parser("status", help="只读全景仪表盘：管道全景 + 今日行动 + 一致性自检 + 统计（不写文件）")

    db = sub.add_parser("dashboard", help="生成单文件只读投递看板 HTML（默认 REPO_ROOT/dashboard.html）")
    db.add_argument("--out", help="输出路径，默认 REPO_ROOT/dashboard.html")

    sub.add_parser("selftest", help="环境 + 数据自检（依赖/渲染路径/端到端渲染/数据完整性/tracker幂等/文档一致）")

    sub.add_parser("check-update", help="检查引擎更新（引擎唯一联网命令，仅手动触发；"
                   "status/selftest 有 30 天纯本地提醒）")

    tr = sub.add_parser("tracker", help="从全部 APP###.yaml 的 tracking 子树重新生成 applications.md 两张表")
    tr.add_argument("--migrate", action="store_true",
                    help="一次性迁移：解析 applications.md 现有表格 → 写入/创建各 APP 的 tracking 子树")

    sm = sub.add_parser("submit", help="登记投递：过投递闸 → 写 tracking.applied → 生成表格 → 打印 Notion payload")
    sm.add_argument("--app", required=True)
    sm.add_argument("--date", help="投递日期 YYYY-MM-DD，默认今天")
    sm.add_argument("--external", action="store_true",
                    help="跳过投递闸——登记在流水线外完成的投递（如内推/猎头渠道）")

    cl = sub.add_parser("close", help="关闭投递：写 tracking.closed → stage=Closed → 生成表格 → 打印 Notion payload")
    cl.add_argument("--app", required=True)
    cl.add_argument("--reason", required=True,
                    choices=list(CLOSE_REASON_LABELS),
                    help="关闭原因：no-response|rejected|withdrawn|skipped|expired")
    cl.add_argument("--note", help="（可选）追加说明，拼进 tracking.closed.reason 描述")
    cl.add_argument("--date", help="关闭日期 YYYY-MM-DD，默认今天")

    fc = sub.add_parser("fact", help="SSOT Change Log 机械追加（Claude 先手动改 SSOT 正文，此命令只留 Change Log 痕）")
    fc.add_argument("--topic", required=True, help="字段/变更项")
    fc.add_argument("--content", required=True, help="旧值→新值 / 变更内容")
    fc.add_argument("--cause", help="（可选）起因，拼进第 3 列前缀")
    fc.add_argument("--files", help="（可选）Tier 2 已同步文件清单")
    fc.add_argument("--tier3", help="（可选）Tier 3 外部镜像状态")

    it = sub.add_parser("init", help="新工作区脚手架（workspace.yaml/SSOT模板/母版骨架/applications.md空表）")
    it.add_argument("--dir", help="目标目录，默认当前目录。须为空或不含 workspace.yaml")

    args = ap.parse_args()
    {"prep": cmd_prep,
     "verify": cmd_verify,
     "prompt": cmd_prompt,
     "factcheck-pass": cmd_factcheck_pass,
     "qualreview-pass": cmd_qualreview_pass,
     "make": cmd_make,
     "review": cmd_review,
     "harvest": cmd_harvest,
     "status": cmd_status,
     "dashboard": cmd_dashboard,
     "init": cmd_init,
     "selftest": cmd_selftest,
     "check-update": cmd_check_update,
     "tracker": cmd_tracker,
     "submit": cmd_submit,
     "close": cmd_close,
     "fact": cmd_fact}[args.cmd](args)


if __name__ == "__main__":
    main()
