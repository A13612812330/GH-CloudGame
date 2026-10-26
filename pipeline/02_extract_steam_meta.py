# -*- coding: utf-8 -*-
# ============================================================================
# 端游周报流水线 · 步骤 02：抽取 Steam 元数据（appid → 中文名/开发者/标签/日期/大小/独立/峰值）
# 用法：python 02_extract_steam_meta.py
# ----------------------------------------------------------------------------
# 数据来源（按优先级）：
#   1) assets/steam_meta_seed.json  —— 随仓库发行的种子元数据（开箱可用）
#   2) 产出目录下的历史大报告 ③Steam源（有就用，字段更全、更新）
# 任何一份缺失都只跳过、不报错 —— 保证同事首次跑也能出结果。
# 全套顺序：00 → 01 → 02 → 03 → 04 → 04b → 05 → 06
# ============================================================================
"""从历史交付物 + 种子文件抽取 Steam 元数据"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cfg import CFG  # noqa: E402

meta: dict = {}


def norm_appid(v):
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s if s.isdigit() else None


# ---------------------------------------------------------------- 0) 种子
seed = CFG.assets_dir / "steam_meta_seed.json"
if seed.is_file():
    try:
        base = json.loads(seed.read_text(encoding="utf-8"))
        meta.update({str(k): dict(v) for k, v in base.items()})
        print("种子元数据: %d 条 (%s)" % (len(meta), seed.name))
    except Exception as e:
        print("种子元数据读取失败（跳过）: %s" % e)
else:
    print("种子元数据: 无（%s）" % seed)


# ---------------------------------------------------------------- 1) 历史交付物
def load_into(fname: str, sheet: str, pairs: list, overwrite: bool = False) -> None:
    """从产出目录下某个 xlsx 的某个 sheet 抽字段。文件/表不存在则跳过。"""
    p = CFG.out(fname)
    if not p.is_file():
        print("  · 跳过（无此文件）: %s" % fname)
        return
    try:
        df = pd.read_excel(p, sheet_name=sheet)
    except Exception as e:
        print("  · 跳过（无此 sheet：%s）: %s" % (sheet, fname))
        return
    n = 0
    for _, r in df.iterrows():
        a = norm_appid(r.get("appid"))
        if not a:
            continue
        if overwrite:
            m = meta[a] = meta.get(a, {})
        else:
            m = meta.setdefault(a, {})
        for src, dst in pairs:
            v = str(r.get(src) or "").strip()
            if v and v != "nan" and (overwrite or not m.get(dst)):
                m[dst] = v
        n += 1
    print("  · %s [%s] → %d 行" % (fname, sheet, n))


STD = [("中文名称", "cn"), ("游戏名称(原名)", "en"), ("开发者", "dev"),
       ("玩法标签", "tags"), ("发行日期", "date"), ("安装大小", "size"),
       ("独立游戏", "indie"), ("最低配置", "min"), ("推荐配置", "rec")]

print("历史交付物扫描：")
# 1) 汇总v4（字段最全，含开发者/安装大小/配置）
load_into("端游三源数据汇总v4_完整版_7.1-8.24.xlsx", "③Steam源(近一年·60款)",
          STD + [("近一年峰值", "peak")])
# 2) 三源关联重点表补充（峰值字段名不同）
load_into("端游三源数据汇总v4_完整版_7.1-8.24.xlsx", "④三源关联重点表",
          [("玩法标签", "tags"), ("发行日期", "date"), ("安装大小", "size"),
           ("独立游戏", "indie"), ("最低配置", "min"), ("推荐配置", "rec"),
           ("历史峰值", "peak")])
# 3) 早期周报（补备注）
load_into("端游三源周报_8.17-8.30.xlsx", "③Steam源(8.31)", STD + [("备注", "note")])
# 4) 历次大报告（字段最全，越新越优先 —— 按日期倒序后覆盖）
reports = sorted(CFG.out_dir.glob("端游三源周报_大报告_*.xlsx")) if CFG.out_dir.is_dir() else []
for p in reports:  # 旧的先读，新的后读覆盖
    load_into(p.name, "③Steam源", STD)

# ---------------------------------------------------------------- 2) 落盘
out = CFG.tmp / "steam_meta.json"
out.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n合并后 appid 总数:", len(meta))
print("有发行日期的:", sum(1 for v in meta.values() if v.get("date")))
print("有安装大小的:", sum(1 for v in meta.values() if v.get("size")))
print("有标签的:", sum(1 for v in meta.values() if v.get("tags")))
print("→", out)
