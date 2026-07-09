#!/usr/bin/env python3
"""evals/inject_canaries.py — 金丝雀注入器

用途：把 evals/canaries.yaml 定义的 13 类已知违规注入一份「干净的、已填好阶段2」
的 APP###.yaml 副本里，产出：
  - <out>/canary_<APPID>.yaml     注入后的数据文件（source 原件不改）
  - <out>/answer_key.yaml         注入清单：id/category/落点字段路径/注入片段/expected 判定

用法：
  python3 inject_canaries.py --source <干净的已填 APP yaml> --out <目录> [--sample N] [--seed S] [--only ID]

  --sample N   用 --seed 做确定性随机抽样，只注入 N 条（默认不传 = 全部 13 条）
  --seed S     随机种子，默认 42。同 seed 同 --sample N 产出同一组抽样（幂等）。
  --only ID    只注入这一个 canary（按 id 精确选择，忽略 --sample）——用于单条冒烟测试
               （如第 13 条 library_launder 需要工作区里已放置 rewrite_library.yaml）。

设计要点：
  - 幂等/确定性：不传 --sample/--only 时始终注入全部 13 条，顺序固定（canaries.yaml 顺序）；
    传 --sample 时用 random.Random(seed) 做确定性抽样，同参数重跑结果一致。
  - 不改 source 原件：所有写入都发生在 --out 目录下的副本。
  - 注入落点必须先存在（rewritten 为空则先把 master 复制进 rewritten），
    保证 append/prepend/replace 操作作用在真实存在的文本上，读起来语法自然。
  - 第 13 条 library_launder（mode: set_source_and_replace）需要工作区里已有非空的
    rewrite_library.yaml（build.py harvest 产出）——找不到库文件会直接报错，不静默跳过。
  - 每条注入落点后打印自检信息（落点字段路径 + 注入前后长度变化），
    便于跑完立刻用肉眼核对全部是否落位。
"""
import argparse
import copy
import hashlib
import random
import sys
from pathlib import Path

import yaml


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 字段路径解析：把 canaries.yaml 里语义化的 target 字符串解析成对 resume dict
# 的实际访问路径。支持的路径形式（均是本仓库 schema 里会用到的形状）：
#
#   resume.summary.rewritten
#   resume.bilingual_line.keep
#   resume.skills[label='Tools:'].rewritten
#   resume.experience[id=ore].bullets[master~='Implemented GA4'].rewritten
#
# [key='exact'] = 列表项按字段精确匹配；[key~='substr'] = 子串匹配（用于
# bullets 定位，因为 master 文本较长，用关键子串比整段抄写更稳）。
# ---------------------------------------------------------------------------

def _find_list_item(items, key, matcher, mode):
    for item in items:
        val = item.get(key, "")
        if mode == "eq" and val == matcher:
            return item
        if mode == "substr" and matcher in val:
            return item
    return None


def _split_path(target: str):
    """按顶层 '.' 切分路径，但忽略 [...] 选择器内部的 '.'（例如 '1.9M+ CAD'）。"""
    parts = []
    buf = []
    depth = 0
    for ch in target:
        if ch == "[":
            depth += 1
            buf.append(ch)
        elif ch == "]":
            depth -= 1
            buf.append(ch)
        elif ch == "." and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def resolve_container(data: dict, target: str):
    """返回 (container_dict, leaf_key)，leaf_key 是最终要读写的字段名。"""
    parts = _split_path(target)
    cur = data
    for i, part in enumerate(parts):
        is_last = i == len(parts) - 1
        if "[" in part:
            field, sel = part.split("[", 1)
            sel = sel.rstrip("]")
            if "~=" in sel:
                key, val = sel.split("~=", 1)
                mode = "substr"
            else:
                key, val = sel.split("=", 1)
                mode = "eq"
            key = key.strip()
            val = val.strip().strip("'\"")
            container = cur[field]
            item = _find_list_item(container, key, val, mode)
            if item is None:
                die(f"target 解析失败：字段 '{field}' 里找不到 {key}{'~=' if mode=='substr' else '='}'{val}' 匹配项 (target={target})")
            cur = item
        else:
            if is_last:
                return cur, part
            if part not in cur:
                die(f"target 解析失败：字段 '{part}' 不存在 (target={target})")
            cur = cur[part]
    die(f"target 路径未能解析出叶子字段：{target}")


def get_leaf(data: dict, target: str):
    container, key = resolve_container(data, target)
    return container, key, container.get(key)


# ---------------------------------------------------------------------------
# 注入操作
# ---------------------------------------------------------------------------

def ensure_rewritten_seeded(container: dict, key: str):
    """若目标是 *.rewritten 且当前为空，先用同级 master 文本播种，
    保证后续 append/prepend/replace 操作在真实存在的文本上进行，
    且注入后的字段会落在核对 agent 实际核对的范围内（rewritten 非空才核对）。
    """
    if key != "rewritten":
        return
    val = container.get(key, "")
    if val:
        return
    master = container.get("master", "")
    if not master:
        die(f"无法播种 rewritten：同级 master 也是空 (container keys={list(container.keys())})")
    container[key] = master


def _load_library_snippet_ids(workspace_dir: Path):
    """从工作区根目录读 rewrite_library.yaml，返回 snippet id 列表。
    文件不存在/无 snippets → 返回空列表（调用方据此报错，不静默跳过）。
    workspace_dir 是 --source APP yaml 所在工作区的根目录猜测——本脚本约定
    library_launder 注入时会用 --source 所在目录向上找 rewrite_library.yaml
    （通常 auto-apply/jobs/APP###.yaml 的工作区根是 jobs 的上上级）。
    为避免过度猜测目录结构，实际调用方直接传入待搜索的候选目录列表。"""
    candidates = [
        workspace_dir / "rewrite_library.yaml",
        workspace_dir.parent / "rewrite_library.yaml",
        workspace_dir.parent.parent / "rewrite_library.yaml",
    ]
    for p in candidates:
        if p.is_file():
            try:
                lib = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            ids = [sn.get("id") for sn in (lib.get("snippets") or []) if sn.get("id")]
            if ids:
                return ids, p
    return [], None


def apply_injection(data: dict, canary: dict, *, library_ids=None, only_id=None,
                     rng=None) -> dict:
    """执行一条 canary 的注入，返回落点自检信息 dict。
    library_ids: library_launder 注入用——rewrite_library.yaml 里真实存在的 snippet id 列表。
    only_id: --only 参数指定时，library_launder 精确引用这个 id（而不是随机/首个选取）。
    """
    inj = canary["injection"]
    target = inj["target"]
    mode = inj["mode"]

    if mode == "set_source_and_replace":
        if not library_ids:
            die(f"canary '{canary['id']}': injection mode 'set_source_and_replace' 需要 "
                f"rewrite_library.yaml 存在且非空 —— 当前工作区找不到库文件或库为空。"
                f"请先在目标工作区跑 build.py harvest 放置库文件，再重新注入。")
        if only_id:
            if only_id not in library_ids:
                die(f"canary '{canary['id']}': --only 指定的 id '{only_id}' 在 "
                    f"rewrite_library.yaml 里不存在")
            ref_id = only_id
        else:
            picker = rng or random.Random(42)
            ref_id = picker.choice(sorted(library_ids))

        container, key = resolve_container(data, target)
        ensure_rewritten_seeded(container, key)
        before_text = container.get(key, "")
        text = inj["text"]
        base = before_text.rstrip()
        if base and base[-1] not in ".!?":
            base += "."
        after_text = base + text
        container[key] = after_text
        container["source"] = f"library:{ref_id}"

        return {
            "id": canary["id"],
            "target": target,
            "mode": mode,
            "before_len": len(before_text),
            "after_len": len(after_text),
            "injected_fragment": text,
            "library_id_ref": ref_id,
            "landed": after_text != before_text and text in after_text
                      and container.get("source") == f"library:{ref_id}",
        }

    if mode == "set_flag":
        container, key = resolve_container(data, target)
        before = container.get(key)
        if inj.get("params", {}).get("flip"):
            after = (not before) if isinstance(before, bool) else before
        else:
            after = inj.get("text", before)
        container[key] = after
        return {
            "id": canary["id"],
            "target": target,
            "mode": mode,
            "before": before,
            "after": after,
            "landed": container.get(key) == after,
        }

    container, key = resolve_container(data, target)
    ensure_rewritten_seeded(container, key)
    before_text = container.get(key, "")

    if mode == "append_sentence" or mode == "append_phrase":
        text = inj["text"]
        base = before_text.rstrip()
        if mode == "append_sentence" and base and base[-1] not in ".!?":
            base += "."
        after_text = base + text
    elif mode == "prepend_phrase":
        text = inj["text"]
        after_text = text + before_text
    elif mode == "replace_phrase":
        find = inj["find"]
        text = inj["text"]
        if find not in before_text:
            die(f"canary '{canary['id']}': replace_phrase 目标短语 '{find}' 在字段里不存在 (target={target})")
        after_text = before_text.replace(find, text)
    else:
        die(f"canary '{canary['id']}': 未知 injection mode '{mode}'")

    container[key] = after_text

    return {
        "id": canary["id"],
        "target": target,
        "mode": mode,
        "before_len": len(before_text),
        "after_len": len(after_text),
        "injected_fragment": inj.get("text") or inj.get("find", ""),
        "landed": after_text != before_text and (inj.get("text", "") in after_text if mode != "replace_phrase" else inj["text"] in after_text),
    }


def content_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(description="注入金丝雀违规到 APP yaml 副本")
    ap.add_argument("--source", required=True, help="干净的、已填好阶段2的 APP###.yaml 路径")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--sample", type=int, default=None, help="随机抽样注入 N 条（默认全部 13 条）")
    ap.add_argument("--seed", type=int, default=42, help="随机种子，默认 42")
    ap.add_argument("--canaries", default=str(Path(__file__).parent / "canaries.yaml"), help="canaries.yaml 路径")
    ap.add_argument("--only", help="只注入这一个 canary id（按 id 精确选择，忽略 --sample）")
    args = ap.parse_args()

    source_path = Path(args.source)
    out_dir = Path(args.out)
    canaries_path = Path(args.canaries)

    if not source_path.exists():
        die(f"source 文件不存在：{source_path}")
    if not canaries_path.exists():
        die(f"canaries 定义文件不存在：{canaries_path}")

    out_dir.mkdir(parents=True, exist_ok=True)

    with open(source_path, "r", encoding="utf-8") as f:
        source_data = yaml.safe_load(f)

    with open(canaries_path, "r", encoding="utf-8") as f:
        canary_defs = yaml.safe_load(f)

    all_canaries = [c for c in canary_defs["canaries"] if not c.get("skip")]
    if len(all_canaries) != 13:
        print(f"WARNING: canaries.yaml 定义了 {len(all_canaries)} 条，非预期的 13 条", file=sys.stderr)

    if args.only:
        selected = [c for c in all_canaries if c["id"] == args.only]
        if not selected:
            die(f"--only 指定的 canary id '{args.only}' 在 canaries.yaml 里不存在")
    elif args.sample is not None:
        rng = random.Random(args.seed)
        selected = sorted(all_canaries, key=lambda c: c["id"])  # 稳定排序后再抽样，保证确定性
        selected = rng.sample(selected, min(args.sample, len(selected)))
    else:
        selected = all_canaries

    app_id = source_data.get("app_id", source_path.stem)
    injected_data = copy.deepcopy(source_data)

    # library_launder（set_source_and_replace）需要 rewrite_library.yaml 里真实存在的 snippet id。
    # 只在 selected 里真的出现该 mode 的 canary 时才去找库文件——避免其余注入场景无谓地要求库存在。
    needs_library = any(c["injection"]["mode"] == "set_source_and_replace" for c in selected)
    library_ids, library_path = ([], None)
    if needs_library:
        library_ids, library_path = _load_library_snippet_ids(source_path.parent)
        if not library_ids:
            die(f"canaries 里含 set_source_and_replace 注入，但从 {source_path.parent} 及上级目录 "
                f"找不到非空的 rewrite_library.yaml —— 请先在目标工作区跑 build.py harvest 放置库文件")

    inject_rng = random.Random(args.seed)
    landed_records = []
    for canary in selected:
        record = apply_injection(injected_data, canary, library_ids=library_ids,
                                  rng=inject_rng)
        record["category"] = canary["category"]
        record["expected"] = canary["expected"]
        record["rule_ref"] = canary.get("rule_ref", "")
        landed_records.append(record)

    out_yaml_path = out_dir / f"canary_{app_id}.yaml"
    with open(out_yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(injected_data, f, allow_unicode=True, sort_keys=False, width=100)

    # 验证产物可被 safe_load 重新解析（防止 yaml.safe_dump 产出损坏内容）
    with open(out_yaml_path, "r", encoding="utf-8") as f:
        reparsed = yaml.safe_load(f)
    if reparsed is None:
        die("产物 yaml safe_load 后为空，注入失败")

    answer_key = {
        "source_file": str(source_path),
        "app_id": app_id,
        "canary_yaml": str(out_yaml_path),
        "seed": args.seed if args.sample is not None else None,
        "sample_size": len(selected),
        "canaries": [],
    }
    for rec in landed_records:
        entry = {
            "id": rec["id"],
            "category": rec["category"],
            "expected": rec["expected"],
            "rule_ref": rec["rule_ref"],
            "field_path": rec["target"],
            "mode": rec["mode"],
            "landed": rec["landed"],
        }
        if "injected_fragment" in rec:
            entry["injected_fragment"] = rec["injected_fragment"]
        if "before" in rec:
            entry["before"] = rec["before"]
            entry["after"] = rec["after"]
        if "library_id_ref" in rec:
            entry["library_id_ref"] = rec["library_id_ref"]
        answer_key["canaries"].append(entry)
    if library_path:
        answer_key["library_source"] = str(library_path)

    answer_key_path = out_dir / "answer_key.yaml"
    with open(answer_key_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(answer_key, f, allow_unicode=True, sort_keys=False, width=100)

    # 自检打印
    print(f"注入完成：{len(selected)}/{len(all_canaries)} 条 canary → {out_yaml_path}")
    print(f"answer_key → {answer_key_path}")
    print()
    print(f"{'id':<32} {'落点字段路径':<55} {'landed':<8}")
    print("-" * 100)
    all_landed = True
    for rec in landed_records:
        landed = rec["landed"]
        all_landed = all_landed and landed
        marker = "OK" if landed else "MISS"
        print(f"{rec['id']:<32} {rec['target']:<55} {marker:<8}")

    if not all_landed:
        die("部分注入未落位（landed=False），见上表 MISS 行")

    print()
    print(f"全部 {len(selected)} 处注入确认落位。source 原件未改动：{source_path}")


if __name__ == "__main__":
    main()
