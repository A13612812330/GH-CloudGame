# -*- coding: utf-8 -*-
# ============================================================================
# 端游周报流水线 · 步骤 00：探查输入 xlsx 的 sheet 与列结构（每次新格式先跑）
# 用法：python 00_probe_inputs.py
# ----------------------------------------------------------------------------
# 每次新一周需要改的配置（见本文件顶部 CONFIG 区）：
#   1) SRC_SEARCH / SRC_DL  —— 明说输入文件名（可带日期前缀）
#   2) OUT_* / RUN_DATE     —— 输出文件名与快照日期
#   3) 03 的 CHART 数组     —— 从 steamdb.info/charts/ 重新抓取的 Top100
#   4) 04 的 PATCH          —— 新增游戏的人工补齐元数据（SteamDB 单页实抓）
# 全套顺序：00 → 01 → 02 → 03 → 04 → 05 → 06
# ============================================================================
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cfg import CFG  # noqa: E402  统一配置（路径只从 config.json 来）

files = {
    "搜索": CFG.search_file("cur"),
    "下载": CFG.dl_file("cur"),
}
for tag, f in files.items():
    f = str(f)
    xl = pd.ExcelFile(f)
    print("=" * 70)
    print(tag, f)
    print("sheets:", xl.sheet_names)
    for s in xl.sheet_names:
        full = pd.read_excel(f, sheet_name=s)
        head = full.head(5)
        print(f"  -- sheet [{s}] shape={full.shape}")
        print("     cols:", list(full.columns))
        print(head.to_string()[:2000])
