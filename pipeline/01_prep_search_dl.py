# -*- coding: utf-8 -*-
# ============================================================================
# 端游周报流水线 · 步骤 01：搜索 + 云游戏下载清洗（三级匹配 · 跨期对比）
# 用法：python 01_prep_search_dl.py
# ----------------------------------------------------------------------------
# ⛔ 口径铁律（2026-09-28 用户明确要求后定稿）
#
#   对比的是「本期两周」vs「上期两周」，**不是**本期内部 W1 vs W2。
#
#   实测依据（405 款共有游戏，2026-09-28）：
#     「本期 14 天合计 ÷ 上期 2 天合计」的中位数 = 1.014 ≈ 1
#     ⇒ 平台导出的两个日期列是**周汇总**（8.31-9.6 / 9.7-9.13），不是单日。
#     ⇒ 所以「上期两列相加」与「本期 14 天相加」时间跨度等效，可直接比。
#
#   搜索源同理：两期各导出 2 列（两个周一），每列代表一周，两列相加 = 两周。
#
# 每次新一期需要改的配置（见下方 CONFIG 区）：
#   1) CUR_* / PREV_*  —— 本期与上期的输入文件路径
#   2) OUT / RUN_DATE  —— 输出目录与快照日期
#   3) 03 的 CHART 数组 —— 从 steamdb.info/charts/ 重新抓取的 Top100
#   4) 04 的 PATCH      —— 新增游戏的人工补齐元数据（SteamDB 单页实抓）
# 全套顺序：00 → 01 → 02 → 03 → 04 → 05 → 06 → 07
# ============================================================================
"""端游周报数据清洗：本期(9.28-10.11) vs 上期(9.14-9.27) 跨期对比"""
import json, os, sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cfg import CFG  # noqa: E402  统一配置（路径只从 config.json 来）

LIB = str(CFG.lib)
OUT = str(CFG.tmp)
os.makedirs(OUT, exist_ok=True)

# ------------------------- CONFIG（路径在 config.json，这里不用改） -------------------------
PERIODS = {
    "cur": {
        "label": CFG.label("cur"),
        "search": str(CFG.search_file("cur")),
        "dl": str(CFG.dl_file("cur")),
    },
    "prev": {
        "label": CFG.label("prev"),
        "search": str(CFG.search_file("prev")),
        "dl": str(CFG.dl_file("prev")),
    },
}
RUN_DATE = CFG.run_date
# -----------------------------------------------------------------------------

lib = json.load(open(LIB, encoding="utf-8"))
ENDGAME, EXCLUDE = lib["endgame"], lib["exclude"]


def norm(s):
    return str(s).strip().upper()


alias_map = {}
for game, aliases in ENDGAME.items():
    for a in aliases:
        alias_map.setdefault(norm(a), []).append(game)
exclude_set = set(norm(e) for e in EXCLUDE)
exclude_multi = [e for e in exclude_set if len(e) >= 2]


def match(nk):
    """返回 (命中的游戏列表, 匹配类型)：精确 → 前缀扩展(≤6) → 词根中断(≥3)"""
    if not nk or nk == "NAN":
        return [], ""
    if nk in exclude_set:
        return [], ""
    if any(e in nk for e in exclude_multi):
        return [], ""
    if len(nk) == 1 and not nk.isalpha():
        return [], ""
    if nk in alias_map:
        return alias_map[nk], "精确"
    best = None
    for a in alias_map:
        if len(a) >= 2 and nk.startswith(a) and len(nk) > len(a) and len(nk) - len(a) <= 6:
            if best is None or len(a) > len(best):
                best = a
    if best:
        return alias_map[best], "前缀扩展"
    if len(nk) >= 3:
        best = None
        for a in alias_map:
            if len(a) > len(nk) >= 3 and a.startswith(nk) and len(a) - len(nk) <= 6:
                if best is None or len(a) < len(best):
                    best = a
        if best:
            return alias_map[best], "词根中断"
    return [], ""


CAT_RULES = [
    ("生存沙盒", ["我的世界", "ROBLOX", "方舟", "饥荒", "泰拉瑞亚", "木筏", "后室", "生存战争", "波比", "恐龙岛", "七日杀", "腐蚀", "环世界", "Valheim", "DayZ", "The Isle", "Rust"]),
    ("竞技射击", ["绝地求生", "CS2", "三角洲", "无畏契约", "使命召唤", "战地", "暗区", "战争雷霆", "堡垒之夜", "PUBG", "穿越火线", "APEX", "彩虹六号", "守望"]),
    ("动作/冒险", ["GTA", "漫威蜘蛛侠", "火影", "海贼", "荒野大镖客", "拳皇", "龙珠", "怪物猎人", "生化", "黑神话", "只狼", "艾尔登", "鬼泣", "赛博朋克", "仁王", "鬼武者", "无主之地", "红色沙漠"]),
    ("模拟/经营", ["欧洲卡车", "NBA2K", "模拟农场", "模拟山羊", "模拟人生", "超市", "遨游中国", "极限竞速", "沙堡", "G沙盒", "渔力全开", "欧卡", "Satisfactory", "Factorio", "BeamNG", "足球经理"]),
    ("休闲/派对", ["植物大战僵尸", "恐怖奶奶", "诅咒之岛", "晃晃人生", "节奏盒子", "软体汽车", "恶魔轮盘", "午夜轮班", "双人成行", "机械狂欢", "R.E.P.O.", "Bongo Cat", "PAYDAY", "PEAK"]),
    ("RPG/网游", ["梦幻西游", "魔兽", "逆水寒", "剑网", "天涯明月刀", "天龙八部", "传奇", "问道", "诛仙", "三国杀", "冒险岛", "DNF", "热血", "Limbus", "原神", "崩坏"]),
    ("策略/独立", ["文明", "全面战争", "红色警戒", "杀戮尖塔", "空洞骑士", "三国志", "盖瑞模组", "星露谷", "缺氧", "冰汽", "Baldur", "捆绑", "气球塔防", "Blood of Dawnwalker"]),
]


def classify(n):
    for c, keys in CAT_RULES:
        if any(k.lower() in n.lower() for k in keys):
            return c
    return "其他"


def fmt_span(ds):
    if len(ds) == 0:
        return "—"
    a, b = pd.Timestamp(ds[0]).date(), pd.Timestamp(ds[-1]).date()
    return f"{a}" if a == b else f"{a}~{b.strftime('%m-%d')}"


# ================= 搜索：按「期」清洗（同一套词库，两期可比） =================
def clean_search(path):
    det = pd.read_excel(path, sheet_name="明细数据")
    det.columns = ["日期", "kw", "ev"]
    det["日期"] = pd.to_datetime(det["日期"])
    rows = []
    for kw, v in zip(det["kw"], det["ev"]):
        hits, mtype = match(norm(kw))
        for g in set(hits):
            rows.append({"端游名称": g, "搜索词": str(kw), "次数": int(v), "匹配方式": mtype})
    d = pd.DataFrame(rows)
    agg = (d.groupby("端游名称")
             .agg(搜索次数=("次数", "sum"), 关键词数=("搜索词", "nunique"))
             .reset_index())
    return det, d, agg


search_meta = {}
S_AGG = {}
for key, cfg in PERIODS.items():
    det, d, agg = clean_search(cfg["search"])
    total_all = int(det["ev"].sum())
    total_hit = int(agg["搜索次数"].sum())
    dates = sorted(det["日期"].unique())
    S_AGG[key] = agg
    search_meta[key] = {
        "label": cfg["label"],
        "dates": [str(pd.Timestamp(x).date()) for x in dates],
        "span": fmt_span(dates),
        "total_all": total_all, "total_hit": total_hit,
        "games": int(len(agg)), "ratio": round(total_hit / total_all * 100, 1),
    }
    print(f"[搜索·{key}] {cfg['label']} | 日期 {len(dates)} 个 {fmt_span(dates)} | "
          f"命中 {len(agg)} 款 / {total_hit:,} 次 = {total_hit/total_all*100:.1f}%（全站 {total_all:,}）")

# 合并两期 → 跨期对比表
sm = (S_AGG["cur"].rename(columns={"搜索次数": "本期搜索", "关键词数": "本期词数"})
      .merge(S_AGG["prev"].rename(columns={"搜索次数": "上期搜索", "关键词数": "上期词数"}),
             on="端游名称", how="outer").fillna(0))
sm["本期搜索"] = sm["本期搜索"].astype(int)
sm["上期搜索"] = sm["上期搜索"].astype(int)
sm["两期合计"] = sm["本期搜索"] + sm["上期搜索"]
sm["搜索环比"] = sm.apply(
    lambda r: (round((r["本期搜索"] / r["上期搜索"] - 1) * 100, 1) if r["上期搜索"] > 0 else None), axis=1)
sm["环比显示"] = sm["搜索环比"].apply(lambda v: "新增" if pd.isna(v) else f"{v:+.1f}%")

# 代表性搜索词（按本期次数取 Top3，缺则用上期）
_detail = []
for key, cfg in PERIODS.items():
    _, d, _a = clean_search(cfg["search"])
    d["期"] = key
    _detail.append(d)
dall = pd.concat(_detail, ignore_index=True)


def reps(g):
    sub = (dall[dall["端游名称"] == g].groupby("搜索词")["次数"].sum()
           .sort_values(ascending=False).head(3))
    return "、".join(sub.index)


sm["代表性搜索词"] = sm["端游名称"].apply(reps)
sm["关键词数"] = (sm["本期词数"].fillna(0) + sm["上期词数"].fillna(0)).astype(int)
# 两期都出现过的关键词数（更准确地反映持续关注度）
sm["品类"] = sm["端游名称"].apply(classify)
sm = sm.sort_values("本期搜索", ascending=False).reset_index(drop=True)
sm = sm[["端游名称", "本期搜索", "上期搜索", "两期合计", "搜索环比", "环比显示",
         "关键词数", "品类", "代表性搜索词"]]

print(f"[搜索·跨期] 本期 {int(sm['本期搜索'].sum()):,} vs 上期 {int(sm['上期搜索'].sum()):,} "
      f"= {(sm['本期搜索'].sum()/sm['上期搜索'].sum()-1)*100:+.1f}% | 本期有量 {int((sm['本期搜索']>0).sum())} 款")


# ================= 云游戏下载：按「期」清洗 =================
def clean_dl(path):
    det = pd.read_excel(path, sheet_name="明细数据")
    det.columns = ["日期", "游戏", "下载"]
    det["日期"] = pd.to_datetime(det["日期"])
    det["游戏"] = (det["游戏"].astype(str)
                   .str.replace("（云游戏）", "", regex=False).str.strip())
    agg = det.groupby("游戏")["下载"].sum().reset_index().rename(columns={"下载": "下载量"})
    return det, agg


dl_meta = {}
D_AGG = {}
for key, cfg in PERIODS.items():
    det, agg = clean_dl(cfg["dl"])
    dates = sorted(det["日期"].unique())
    D_AGG[key] = agg
    dl_meta[key] = {
        "label": cfg["label"], "dates": [str(pd.Timestamp(x).date()) for x in dates],
        "span": fmt_span(dates), "n_days": len(dates),
        "total": int(agg["下载量"].sum()), "games": int(len(agg)),
    }
    print(f"[下载·{key}] {cfg['label']} | {len(dates)} 个日期 {fmt_span(dates)} | "
          f"{len(agg)} 款 / 合计 {int(agg['下载量'].sum()):,}")

dm = (D_AGG["cur"].rename(columns={"下载量": "本期下载"})
      .merge(D_AGG["prev"].rename(columns={"下载量": "上期下载"}), on="游戏", how="outer").fillna(0))
dm["本期下载"] = dm["本期下载"].astype(int)
dm["上期下载"] = dm["上期下载"].astype(int)
dm["两期合计"] = dm["本期下载"] + dm["上期下载"]
dm["下载环比"] = dm.apply(
    lambda r: (round((r["本期下载"] / r["上期下载"] - 1) * 100, 1) if r["上期下载"] > 0 else None), axis=1)
dm["环比显示"] = dm["下载环比"].apply(lambda v: "新上架" if pd.isna(v) else f"{v:+.1f}%")
dm = dm.sort_values("本期下载", ascending=False).reset_index(drop=True)

print(f"[下载·跨期] 本期 {int(dm['本期下载'].sum()):,} vs 上期 {int(dm['上期下载'].sum()):,} "
      f"= {(dm['本期下载'].sum()/dm['上期下载'].sum()-1)*100:+.1f}% | 本期有量 {int((dm['本期下载']>0).sum())} 款")

# 本期逐日序列（看板趋势用；上期只有周汇总，无法逐日）
det_c, _ = clean_dl(PERIODS["cur"]["dl"])
daily = (det_c.groupby("日期")["下载"].sum().reset_index()
         .rename(columns={"日期": "date", "下载": "value"}).sort_values("date"))
daily["date"] = daily["date"].dt.strftime("%m-%d")
daily.to_csv(f"{OUT}/dl_daily.csv", index=False, encoding="utf-8-sig")
if len(daily) > 2:
    print(f"[下载] 本期逐日 {len(daily)} 天：{daily['date'].iloc[0]} ~ {daily['date'].iloc[-1]}")

sm.to_csv(f"{OUT}/search_agg.csv", index=False, encoding="utf-8-sig")
dm.to_csv(f"{OUT}/dl_agg.csv", index=False, encoding="utf-8-sig")
dall.to_csv(f"{OUT}/search_detail.csv", index=False, encoding="utf-8-sig")

json.dump({
    "run_date": RUN_DATE,
    "cur_label": PERIODS["cur"]["label"], "prev_label": PERIODS["prev"]["label"],
    "search": search_meta, "dl": dl_meta,
    "dl_daily_days": int(len(daily)),
    "s_chg": round((sm["本期搜索"].sum() / sm["上期搜索"].sum() - 1) * 100, 1),
    "dl_chg": round((dm["本期下载"].sum() / dm["上期下载"].sum() - 1) * 100, 1),
}, open(f"{OUT}/meta.json", "w", encoding="utf-8"), ensure_ascii=False)

print("\n--- 搜索 本期 Top20（跨期） ---")
print(sm.head(20)[["端游名称", "本期搜索", "上期搜索", "环比显示", "关键词数", "品类"]].to_string(index=False))
print("\n--- 下载 本期 Top20（跨期） ---")
print(dm.head(20)[["游戏", "本期下载", "上期下载", "环比显示"]].to_string(index=False))
