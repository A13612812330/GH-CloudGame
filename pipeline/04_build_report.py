# -*- coding: utf-8 -*-
# ============================================================================
# 端游周报流水线 · 步骤 04：生成五表 Excel（①搜索②鲸云③Steam④重点表⑤概览）+ data.json
# 用法：python 04_build_report.py
# ----------------------------------------------------------------------------
# 每次新一周需要改的配置（见本文件顶部 CONFIG 区）：
#   1) SRC_SEARCH / SRC_DL  —— 明说输入文件名（可带日期前缀）
#   2) OUT_* / RUN_DATE     —— 输出文件名与快照日期
#   3) 03 的 CHART 数组     —— 从 steamdb.info/charts/ 重新抓取的 Top100
#   4) 04 的 PATCH          —— 新增游戏的人工补齐元数据（SteamDB 单页实抓）
# 全套顺序：00 → 01 → 02 → 03 → 04 → 05 → 06
#
# ⛔ 口径铁律（2026-09-28 用户明确要求后定稿）：
#   对比的是「本期两周(9.28-10.11)」vs「上期两周(9.14-9.27)」，**不是**本期内部 W1 vs W2。
#   上期导出的 2 个日期列是**周汇总**（实测：405 款共有游戏「本期14天÷上期2天」中位数 = 1.014），
#   因此「上期两列相加」与「本期 14 天相加」时间跨度等效，可直接比。
# ============================================================================
"""端游三源周报 9.28-10.11 主构建（跨期对比）：③Steam源 + ④三源关联重点表 + 五表 Excel"""
import json, sys, datetime as dt
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cfg import CFG  # noqa: E402  统一配置（路径只从 config.json 来）

TMP = str(CFG.tmp)
OUT_XLSX = str(CFG.report_out())
TODAY = dt.date.fromisoformat(CFG.run_date) if CFG.run_date else dt.date.today()

chart = pd.read_csv(f"{TMP}/chart.csv")
meta = json.load(open(f"{TMP}/steam_meta.json", encoding="utf-8"))
# 历史元数据修正（发现与 SteamDB 实抓不符时在此覆盖）
META_FIX = {
    "4001890": {"peak": "373,971"},   # 渔力全开：SteamDB 实抓 all-time peak = 373,971
}
for _a, _f in META_FIX.items():
    meta.setdefault(_a, {}).update(_f)

# 已跌出 Top100、但单独实抓过当期数据的游戏（展示用，不混进 s3）
LIVE_OUT = {}
sa = pd.read_csv(f"{TMP}/search_agg.csv")
dl = pd.read_csv(f"{TMP}/dl_agg.csv")
daily = pd.read_csv(f"{TMP}/dl_daily.csv")
mjs = json.load(open(f"{TMP}/meta.json", encoding="utf-8"))

# 列名口径（跨期对比：左=本期，右=上期）
CUR_LAB, PREV_LAB = CFG.label("cur"), CFG.label("prev")
S1C1 = "本期(%s)" % CUR_LAB   # 搜索：本期两周合计
S1C2 = "上期(%s)" % PREV_LAB  # 搜索：上期两周合计
C2C1 = "本期(%s)" % CUR_LAB   # 下载：本期 14 天合计
C2C2 = "上期(%s)" % PREV_LAB  # 下载：上期 14 天逐日合计


def _range_text(lab: str) -> str:
    """"9.28-10.11" -> "2026-09-28 ~ 10-11"（看板 hero 用）"""
    try:
        a, b = lab.split("-")
        m1, d1 = a.split(".")
        return "%d-%02d-%02d ~ %s" % (TODAY.year, int(m1), int(d1), b.replace(".", "-"))
    except Exception:
        return lab

# ---------- 新增/缺失条目的人工补齐（来自 2026-10-12 SteamDB / Steam 支持页实抓） ----------
PATCH = {
    "3393110": dict(cn="永恒之塔2", en="AION 2", dev="NCSOFT", date="2026-09-30",
                    size="—", indie="否", type="MMORPG（已按网游排除）",
                    tags="MMORPG/韩系/阵营对抗/大规模PVPvE/免费",
                    note="🆕 9/30 上线，10/12 抓取时已冲到 Steam 在线第 4（21.1 万），24h 峰值 39.2 万；韩国国民级 IP 续作，上线即顶流"),
    "4623570": dict(cn="Deskrawl: Idle ARPG", en="Deskrawl: Idle ARPG", dev="—", date="2026-09-01",
                    size="—", indie="是", type="放置挂机 ARPG",
                    tags="放置/挂机/ARPG/桌面伴侣/像素/独立",
                    note="🔥 挂机品类新爆款：4.43 万在线（Steam 第 20），峰值 4.82 万；桌面常驻形态极适合云游戏「挂机托管」场景"),
    "1181000": dict(cn="UBERMOSH:OMEGA", en="UBERMOSH:OMEGA", dev="Walter Machado", date="2019-05-09",
                    size="—", indie="是", type="单机动作",
                    tags="动作/街机/复古/像素/快节奏/独立/单人",
                    note="🟡 10/11 单日冲高：24h 峰值 = 历史峰值 17.49 万（当前回落至 2.76 万），典型的限免/捆绑脉冲，不宜按长线热度理解"),
    "292030": dict(cn="巫师3：狂猎 次世代版", en="The Witcher 3: Wild Hunt Remastered", dev="CD PROJEKT RED", date="2022-12-14",
                    size="50GB", indie="否", type="单机 RPG",
                    tags="RPG/开放世界/剧情丰富/奇幻/单人/第三人称",
                    note="🟢 长青 RPG 回榜第 24（3.81 万在线），十周年/次世代版长尾稳固；50GB 体量云化成本中等"),
    "2054970": dict(cn="龙之信条2", en="Dragon's Dogma 2", dev="CAPCOM", date="2024-03-22",
                    size="—", indie="否", type="单机动作 RPG",
                    tags="动作/RPG/开放世界/奇幻/单人/捏脸自由",
                    note="🟢 CAPCOM 开放世界动作 RPG，2.6 万在线稳居第 39"),
    "632360": dict(cn="雨中冒险2", en="Risk of Rain 2", dev="Hopoo Games / Gearbox", date="2020-08-11",
                    size="—", indie="是", type="单机/联机 Roguelike",
                    tags="Roguelike/第三人称射击/合作/多人/独立/刷宝",
                    note="🟢 独立 Roguelike 长青款，2.05 万在线；体积小、适配触屏，是端转手候选池常客"),
    "1304930": dict(cn="逃生试炼", en="The Outlast Trials", dev="Red Barrels", date="2024-03-05",
                    size="—", indie="否", type="单机/合作 恐怖",
                    tags="恐怖/合作/多人/心理恐怖/血腥/第一人称",
                    note="🟡 1.79 万在线，但 24h 峰值 10.9 万 —— 期间有活动拉动的脉冲"),
    "2288340": dict(cn="皇牌空战8：希孚之翼", en="ACE COMBAT 8: WINGS OF THEVE", dev="Bandai Namco", date="2026-09-25",
                    size="—", indie="否", type="单机/联机 空战",
                    tags="飞行/空战/动作/拟真/单人/多人",
                    note="🆕 9/25 发售，1.66 万在线即历史峰值 —— 硬核飞行模拟，手柄/摇杆依赖度高，云化操作门槛偏高"),
    "1621690": dict(cn="核心守护者", en="Core Keeper", dev="Pugstorm / Fireshine", date="2024-08-27",
                    size="—", indie="是", type="单机/联机 沙盒",
                    tags="沙盒/生存/挖掘/建造/合作/像素/独立",
                    note="🟢 2D 沙盒挖矿生存，1.42 万在线；体积小、触屏适配好，端转手候选"),
    "2622380": dict(cn="艾尔登法环 黑夜君临", en="ELDEN RING NIGHTREIGN", dev="FromSoftware", date="2025-05-30",
                    size="—", indie="否", type="联机合作 Roguelike",
                    tags="动作/Roguelike/合作/多人/魂系/联机",
                    note="🟢 法环衍生联机作，1.35 万在线、峰值 31.4 万，长尾稳定"),
    "766570": dict(cn="俄罗斯钓鱼4", en="Russian Fishing 4", dev="Fish Soft", date="2018-11-09",
                    size="—", indie="否", type="免费在线模拟",
                    tags="模拟/钓鱼/在线/免费/拟真/休闲",
                    note="🟢 F2P 拟真钓鱼，1.24 万在线；上手低门槛、强养成，云游戏留存型内容"),
    "582010": dict(cn="怪物猎人：世界", en="Monster Hunter: World", dev="CAPCOM", date="2018-08-09",
                    size="—", indie="否", type="单机/联机 动作",
                    tags="动作/狩猎/合作/多人/开放世界/装备驱动",
                    note="🟢 MH 系列长青，1.23 万在线；与《荒野》形成系列双榜"),
    "2183900": dict(cn="战锤40K：星际战士2", en="Warhammer 40,000: Space Marine 2", dev="Saber Interactive", date="2024-09-09",
                    size="—", indie="否", type="单机/联机 动作射击",
                    tags="动作/射击/合作/多人/PvE/科幻/血腥",
                    note="🟢 1.16 万在线，口碑长尾稳定"),
    "1446780": dict(cn="怪物猎人 崛起", en="MONSTER HUNTER RISE", dev="CAPCOM", date="2022-01-12",
                    size="—", indie="否", type="单机/联机 动作",
                    tags="动作/狩猎/合作/多人/和风/装备驱动",
                    note="🟢 1.15 万在线；体量较《世界》小，云化成本更友好"),
}

rows = []
for _, r in chart[~chart["excluded"]].iterrows():
    a = str(r["appid"])
    m = meta.get(a, {})
    p = PATCH.get(a, {})
    rows.append({
        "中文名称": p.get("cn") or m.get("cn") or r["name"],
        "游戏名称(原名)": m.get("en") or r["name"],
        "appid": a,
        "开发者": p.get("dev") or m.get("dev") or "—",
        "玩法标签": p.get("tags") or m.get("tags") or "—",
        "发行日期": p.get("date") or m.get("date") or "—",
        "类型": p.get("type") or ("单机/合作" if m.get("indie") == "是" else "单机/联机"),
        "安装大小": p.get("size") or m.get("size") or "—",
        "当前在线(10/12)": r["cur"],
        "24h峰值": r["h24"],
        "历史峰值": r["peak"],
        "独立游戏": p.get("indie") or m.get("indie") or "否",
        "Steam排名": int(r["rank"]),
        "备注": p.get("note") or m.get("note") or "",
    })

s3 = pd.DataFrame(rows)
s3["_d"] = pd.to_datetime(s3["发行日期"], errors="coerce")
s3["近一年内上线"] = s3["_d"].apply(lambda d: "是" if pd.notna(d) and 0 <= (pd.Timestamp(TODAY) - d).days <= 366 else "否")
s3 = s3.sort_values("当前在线(10/12)", ascending=False).reset_index(drop=True)
s3 = s3[["中文名称", "游戏名称(原名)", "appid", "开发者", "玩法标签", "发行日期", "近一年内上线",
         "类型", "安装大小", "当前在线(10/12)", "24h峰值", "历史峰值", "独立游戏", "Steam排名", "备注"]]
print(f"③Steam源: {len(s3)} 款（非网游/非工具）")
print(f"   近一年内上线 {sum(s3['近一年内上线']=='是')} 款 | 独立游戏 {sum(s3['独立游戏']=='是')} 款")

# ---------------- ① 搜索关键词源（本期 vs 上期） ----------------
s1 = sa[["端游名称", "本期搜索", "上期搜索", "两期合计", "搜索环比", "环比显示",
         "关键词数", "品类", "代表性搜索词"]].copy()
s1.columns = ["端游名称", "本期搜索", "上期搜索", "两期合计", "环比%", "环比",
              "关键词数", "品类", "代表性搜索词"]
s1 = s1.reset_index(drop=True)

# ---------------- ② 鲸云源（本期 vs 上期） ----------------
s2 = dl[["游戏", "本期下载", "上期下载", "两期合计", "下载环比", "环比显示"]].copy()
s2.columns = ["游戏名称", "本期下载", "上期下载", "两期合计", "环比%", "环比"]

# ---------------- ④ 三源关联重点表 ----------------
search_map = {r["端游名称"]: r for _, r in s1.iterrows()}
dl_map = {r["游戏名称"]: r for _, r in s2.iterrows()}
steam_map = {r["中文名称"]: r for _, r in s3.iterrows()}
steam_by_app = {r["appid"]: r for _, r in s3.iterrows()}


def find_search(*names):
    for n in names:
        for k, v in search_map.items():
            if n and (n in k or k in n):
                return k, v
    return None, None


def find_dl(*names):
    for n in names:
        for k, v in dl_map.items():
            if n and (n in k or k in n):
                return k, v
    return None, None


# (展示名, Steam中文名, appid, 鲸云名, 搜索名候选)
FOCUS = [
    ("OVERPEAK 超人模拟器", "OVERPEAK", None, None, ["OVERPEAK"]),
    ("巴士模拟", None, None, None, ["巴士模拟"]),
    ("软体汽车", None, None, None, ["软体汽车"]),
    ("梦想之路", None, None, None, ["梦想之路"]),
    ("王国保卫战", None, None, "王国保卫战5：联盟", ["王国保卫战"]),
    ("漫威蜘蛛侠2", None, "2651280", "漫威蜘蛛侠2", ["漫威蜘蛛侠"]),
    ("尖叫才能跑", None, None, "尖叫才能跑", []),
    ("渔力全开", "渔力全开", "4001890", "渔力全开", ["渔力全开"]),
    ("极限竞速：地平线5", None, "1551360", "极限竞速：地平线5", ["极限竞速", "地平线"]),
    ("遨游中国2（欧卡MOD）", None, "227300", "遨游中国2：欧洲卡车模拟", ["欧洲卡车模拟器", "欧洲卡车模拟2"]),
    ("黑神话：悟空", None, "2358720", "黑神话：悟空", ["黑神话"]),
    ("三角洲行动", None, None, None, ["三角洲行动"]),
    ("恐龙岛 The Isle", None, "376210", "恐龙岛The Isle", ["恐龙岛"]),
    ("人渣 SCUM", None, "513710", "人渣 SCUM", ["人渣"]),
    ("模拟农场25", None, "2300320", "模拟农场25", ["模拟农场"]),
    ("植物大战僵尸", None, None, None, ["植物大战僵尸"]),
    ("ROBLOX", None, None, None, ["ROBLOX"]),
    ("我的世界", None, None, None, ["我的世界"]),
    ("GTA 侠盗猎车手", None, "271590", None, ["GTA"]),
    ("绝地求生 PUBG", None, "578080", None, ["绝地求生", "PUBG"]),
    ("杀戮尖塔2", None, "2868840", None, []),
    ("NBA 2K", None, None, "NBA2K26·MOD", ["NBA2K"]),
    ("战狗 WARDOGS", "战狗", "1867240", None, []),
    ("伊莫 Aniimo", "伊莫", "4126040", None, ["伊莫"]),
    ("海贼无双", None, None, "海贼无双4", ["海贼无双"]),
    ("沙堡 Sandcastle", None, None, "沙堡：海边挖沙模拟器", ["沙堡"]),
    ("G沙盒", None, None, "G沙盒27", ["G沙盒"]),
    ("神力科莎", None, None, "神力科莎", ["神力科莎"]),
    ("恶魔轮盘", None, None, "恶魔轮盘", ["恶魔轮盘"]),
]

def fmt_peak(v):
    """历史元数据里的峰值可能带千分位逗号，统一转 int 展示"""
    s = str(v or "").strip().replace(",", "")
    if s in ("", "None", "nan"):
        return "未采集"
    try:
        return f"{int(float(s)):,}"
    except ValueError:
        return "未采集"


def field(st, is_hist, key_en, key_cn=None):
    """兼容两种结构：本期 s3 行（中文列名） / 历史 meta（英文键）"""
    if st is None:
        return "—"
    if is_hist:
        return str(st.get(key_en) or "").strip() or "未采集"
    return str(st.get(key_cn or key_en) or "").strip() or "—"


f4 = []
for label, scn, appid, jyname, snames in FOCUS:
    sk, sr = find_search(*snames) if snames else (None, None)
    jk, jr = find_dl(jyname) if jyname else (None, None)
    st = steam_by_app.get(str(appid)) if appid else None
    if st is None and scn:
        st = steam_map.get(scn)
    hist = meta.get(str(appid)) if appid else None
    st_is_hist = False
    if st is None and hist:
        st, st_is_hist = hist, True

    hits = sum(1 for x in [sr is not None, jr is not None, st is not None] if x)
    if hits == 0:
        continue

    chg = sr["环比%"] if sr is not None else None
    dchg = jr["环比%"] if jr is not None else None
    rank_txt = f"第{list(s2['游戏名称']).index(jk)+1}({int(jr['本期下载']):,})" if jr is not None else "—"

    # Steam 端描述：本期在榜 / 跌出 Top100（有实抓）/ 历史采集
    live = LIVE_OUT.get(str(appid)) if appid else None
    if st is None:
        steam_txt = "—"
    elif not st_is_hist:
        steam_txt = f"第{int(st['Steam排名'])}（{int(st['当前在线(10/12)']):,}/{int(st['历史峰值']):,}）"
    elif live:
        steam_txt = f"跌出Top100（{live['cur']:,}/峰值 {fmt_peak(st.get('peak'))}）"
    else:
        steam_txt = "不在本期Top100（历史峰值 {}）".format(fmt_peak(st.get("peak")))

    if hits == 3:
        if dchg is not None and dchg <= -20:
            verdict = "⚠️ 三源在榜但鲸云下载显著回落，热度进入退潮期"
        elif chg is not None and chg >= 20 and dchg is not None and dchg >= 0:
            verdict = "🔥 三源共振：搜索上行 + 鲸云下载同步增长"
        else:
            verdict = "🟢 三源共振：搜索 / 鲸云 / Steam 均有覆盖"
    elif hits == 2:
        verdict = "🟢 双源共振"
    else:
        verdict = "🟡 单源信号"

    # 跨期口径下的人工判定（大盘：搜索 +72.9% / 下载 +46.0%；本期含国庆 10.1-10.7）
    if label == "OVERPEAK 超人模拟器":
        verdict = ("🔥 本期搜索榜最大异动，但不是端游：搜索 318,165 次（第 2）跨期 +1082%，"
                   "实为国际服手游《巅峰崛起》（玩家称「祖国人模拟器」，包名 com.rusergames.overpeak），"
                   "国内渠道站自 10/6 起集中铺量下载页，热度主要来自移动端与短视频导流；"
                   "其搜索含泛词「超人」9.96 万（占 31%），上架价值须先核实平台属性")
    elif label == "巴士模拟":
        verdict = ("🔥 搜索涨幅冠军：125,499 次、跨期 +1280.8%（上期仅 9,089），"
                   "「巴士模拟2 / 巴士模拟二」为新增搜索词主体 —— 模拟驾驶细分需求在假期集中释放")
    elif label == "软体汽车":
        verdict = ("🔥 解压向爆款：搜索 56,255、跨期 +577.1%（「软体汽车碰撞」为词根），"
                   "低配 + 短时长，天然适配云游戏「开即玩」场景")
    elif label == "梦想之路":
        verdict = ("🟢 新补入词库：搜索 94,730、跨期 +195.2%（Dream Road，Steam 移植赛车），"
                   "上期基数 32,086 说明需求持续，非一次性脉冲")
    elif label == "王国保卫战":
        verdict = ("🟢 新补入词库：搜索 72,810、跨期 +135.6%；该系列已在鲸云上架（王国保卫战5：联盟），"
                   "是本期「搜索—下载」同源度最高的塔防标的")
    elif label == "漫威蜘蛛侠2":
        verdict = ("🔥 鲸云下载第 1（8,212）跨期 +278.4%，同时搜索 +216.4% —— 本期最强三源共振单品；"
                   "系列作（迈尔斯莫拉莱斯 +148.1%）同步走高，IP 集中爆发")
    elif label == "尖叫才能跑":
        verdict = ("🟢 鲸云下载第 2（6,003）跨期 +51.4%，跑赢下载大盘 +46.0%；"
                   "继上期逆势上行后继续站稳头部")
    elif label == "渔力全开":
        verdict = ("⚠️ 由盛转衰：鲸云下载 5,305（第 3）跨期 -39.5%，而下载大盘 +46.0% —— "
                   "跑输大盘约 86 个百分点；搜索 25,877 亦 -0.8%（大盘 +72.9%）。"
                   "上期还是双源第 1，本期已明显退潮，建议转存量运营")
    elif label == "极限竞速：地平线5":
        verdict = ("🔥 鲸云下载 5,014（第 4）跨期 +110.1%，搜索 +128.0% —— 拟真驾驶双源齐涨，"
                   "同系列的《地平线6》下载 1,040（+125.6%）同步走高")
    elif label == "遨游中国2（欧卡MOD）":
        verdict = "🟢 鲸云下载 4,868（第 5）跨期 +51.3%，欧卡 MOD 生态需求稳定"
    elif label == "黑神话：悟空":
        verdict = "🟢 鲸云下载 2,800（第 6）跨期 +48.9%，国产 3A 长尾稳定"
    elif label == "三角洲行动":
        verdict = "🔥 搜索 64,703、跨期 +115.5%（大盘 +72.9%），跑赢大盘；竞技射击头部集中度提升"
    elif label == "恐龙岛 The Isle":
        verdict = "🟢 鲸云下载 2,753（第 8）跨期 +54.6%，生存沙盒细分保持增长"
    elif label == "人渣 SCUM":
        verdict = "🟢 鲸云下载 2,469（第 9）跨期 +56.2%，跑赢大盘"
    elif label == "模拟农场25":
        verdict = "🟢 鲸云下载 1,716（第 10）跨期 +62.5%，拟真经营类持续走高"
    elif label == "植物大战僵尸":
        verdict = "🟢 搜索第 1（415,007 次）跨期 +31.3%，蝉联端游搜索榜首，头部基本盘稳固"
    elif label == "ROBLOX":
        verdict = "🟢 搜索第 3（220,175 次）跨期 +30.1%，青少年沙盒平台需求稳固"
    elif label == "我的世界":
        verdict = "🟢 搜索第 4（216,991 次）跨期 +60.6%，与大盘基本同步"
    elif label == "GTA 侠盗猎车手":
        verdict = "🟢 搜索 136,124、跨期 +30.3%，跑输大盘但绝对量仍居第 5"
    elif label == "绝地求生 PUBG":
        verdict = "🟡 搜索 128,058、跨期 +42.9%，跑输大盘 +72.9% 约 30 个百分点，常青网游热度被新品分流"
    elif label == "杀戮尖塔2":
        verdict = "🟢 Steam 在线 4.85 万（第 17）、历史峰值 57.5 万；卡牌构筑品类头部，触屏适配好，端转手候选常客"
    elif label == "NBA 2K":
        verdict = ("🟢 搜索第 9（107,950）跨期 +42.2%，跑输大盘 +72.9%；鲸云侧 NBA2K 系列多代同时在榜"
                   "（NBA2K26·MOD 567、NBA2K25 552）—— 年货体育 IP 在云游戏有稳定长尾")
    elif label == "战狗 WARDOGS":
        verdict = ("🟢 Steam 在线 67,901（第 2）、历史峰值 42.9 万；自上期全球销量两连冠后仍维持高位，"
                   "是本期非新游标的中在线最高的端游，云游戏资源位应继续优先保障")
    elif label == "伊莫 Aniimo":
        verdict = ("⚠️ 上期头条标的未能延续：Steam 在线已从公测时的 9.4 万回落至 39,212，"
                   "且未进入本期搜索 / 下载榜前列 —— 新品首发热度衰减快于预期，"
                   "建议对「首发即上云」标的设定 2 周留存观察期")
    elif label == "海贼无双":
        verdict = "📉 搜索回落榜第 1（17,852，-34.7%）—— 本期跌幅最大单品；下载端仅 9 次，IP 热度已退，建议下调资源位"
    elif label == "沙堡 Sandcastle":
        verdict = ("🟡 搜索 4,644（+41.1%）与下载 1,348（+26.7%）双双低于大盘；较上期"
                   "（下载 1,064、跨期 -51.1%）有企稳迹象，但仍属弱势标的")
    elif label == "G沙盒":
        verdict = ("🟡 搜索 25,141（+25.4%）大幅跑输大盘 +72.9%；下载 G沙盒27 429（+38.8%）同样低于大盘"
                   "—— 上期搜索涨幅第一的沙盒类持续退潮")
    elif label == "神力科莎":
        verdict = "🔥 下载增长榜第 2（1,018，+242.8%）—— 拟真赛车细分与《地平线5》同向走高，可作模拟驾驶资源位的补充标的"
    elif label == "恶魔轮盘":
        verdict = "🔥 下载 1,120（+127.6%）、搜索 7,879（+45.5%）双源齐涨；低配 + 短局时长，解压向转化路径短"

    f4.append({
        "游戏": label,
        "appid": str(appid) if appid else "—",
        "搜索端(跨期环比)": "—" if sr is None else f"✅ {sr['环比']}（{int(sr['本期搜索']):,}）",
        "鲸云下载(排名)": "—" if jr is None else f"{rank_txt}  {jr['环比']}",
        "Steam端(在线/峰值)": steam_txt,
        "源数": hits,
        "玩法标签": field(st, st_is_hist, "tags", "玩法标签"),
        "独立游戏": field(st, st_is_hist, "indie", "独立游戏"),
        "发行日期": field(st, st_is_hist, "date", "发行日期"),
        "安装大小": field(st, st_is_hist, "size", "安装大小"),
        "历史峰值": ("—" if st is None else (fmt_peak(st.get('peak')) if st_is_hist else f"{int(st['历史峰值']):,}")),
        "判定/说明": verdict,
    })

s4 = pd.DataFrame(f4).sort_values("源数", ascending=False).reset_index(drop=True)
s4 = s4.drop(columns=["源数"])
print(f"\n④三源关联重点表: {len(s4)} 行")

# ---------------- ⑤ 概览（跨期：本期 9.28-10.11 vs 上期 9.14-9.27） ----------------
smc, smp = mjs["search"]["cur"], mjs["search"]["prev"]
dlc, dlp = mjs["dl"]["cur"], mjs["dl"]["prev"]
tot_all, tot_all_prev = int(smc["total_all"]), int(smp["total_all"])
tot_hit, tot_hit_prev = int(s1["本期搜索"].sum()), int(s1["上期搜索"].sum())
dl_total, dl_total_prev = int(s2["本期下载"].sum()), int(s2["上期下载"].sum())
S_CHG = round((tot_hit / tot_hit_prev - 1) * 100, 1)
DL_CHG = round((dl_total / dl_total_prev - 1) * 100, 1)
SITE_CHG = round((tot_all / tot_all_prev - 1) * 100, 1)
s_share1, s_share2 = tot_hit / tot_all * 100, tot_hit_prev / tot_all_prev * 100  # 本期 / 上期

RISE = s1[(s1["环比%"].notna()) & (s1["本期搜索"] >= 5000)].nlargest(6, "环比%")
FALL = s1[(s1["环比%"].notna()) & (s1["本期搜索"] >= 5000)].nsmallest(6, "环比%")
DLTOP = s2.nlargest(6, "本期下载")
DLRISE = s2[s2["上期下载"] > 200].nlargest(6, "环比%")
DLLOSS = s2[s2["上期下载"] > 200].nsmallest(6, "环比%")

ov = [
    ("端游三源周报（%s）" % _range_text(CUR_LAB), ""),
    ("", ""),
    ("一、数据源与口径", ""),
    # ⚠️ 以下三行里凡「本期专属」的叙述（假期、词库变更、核心结论）属人工撰写内容，
    #     换期时必须改写；结构性的日期与文件名已自动派生。见 08_preflight_check.py。
    ("① 搜索源", "神策 搜索事件导出（{} vs {}）；两期各含 2 个日期列（周一），"
                 "每列代表一周。本期全站 {:,} 次 / 上期 {:,} 次".format(
                     CFG.search_file("cur").stem, CFG.search_file("prev").stem, tot_all, tot_all_prev)),
    ("② 鲸云源", "神策 云游戏下载报表；两期均为 14 天逐日明细（本期 9.28~10.11，416 款；上期 9.14~9.27，410 款）。"
                 "合计：本期 {:,} / 上期 {:,}".format(dl_total, dl_total_prev)),
    ("③ Steam源", "SteamDB 在线 Top100 实时抓取（{}）× 历史元数据沉淀；筛出非网游/非工具端游 {} 款".format(
        CFG.run_date or TODAY.isoformat(), len(s3))),
    ("★ 本期口径说明", "对比基准为「本期两周 vs 上期两周」。本期含国庆假期 10.1-10.7，"
                   "全站搜索同期 {:+.1f}%、下载 {:+.1f}%，**环比涨幅须先减去假期效应再解读**。".format(SITE_CHG, DL_CHG)),
    ("★ 词库变更", "本期新增 3 款词库条目：OVERPEAK（超人模拟器/超峰时刻/祖国人模拟器）、梦想之路、王国保卫战。"
                 "①修正了此前把 OVER* 截断词（OVER/OVERP/OVERPE 等共 36,503 次）误计入守望先锋的问题，"
                 "守望先锋由错误的 +941.9% 回落为 +97.7%；②这批截断词现归入 OVERPEAK，其归属在 OVERPEAK 与守望先锋之间"
                 "无法完全区分 —— 因两期使用同一词库，跨期趋势不受影响，仅绝对归属存疑；"
                 "③「甜瓜游乐场」未纳入词库，因其与 exclude 排除词「甜瓜」冲突（本期仍为未覆盖）"),
    ("★ 端手混流提示", "神策搜索源不区分端游/手游，跨端搜索外溢会污染端游榜。本期《OVERPEAK》即典型案例；"
                   "凡某款「端游」搜索出现异常脉冲，须先核实其平台属性再解读"),
    ("⛔ 已停用", "鲸云注册数据源（按用户要求移出流程，本报告不含注册数据）"),
    ("", ""),
    ("二、核心结论", ""),
    ("1. 搜索大盘：假期加成下大涨", "端游命中 {} 款 / {:,} 次，跨期 {:+.1f}%（上期 {:,} 次）".format(
        int((s1["本期搜索"] > 0).sum()), tot_hit, S_CHG, tot_hit_prev)),
    ("2. 端游跑赢全站", "全站同期 {:+.1f}%（{:,} → {:,}），端游占比由 {:.2f}% 升至 {:.2f}% —— "
                     "端游增速快于大盘约 {:.1f} 个百分点".format(
                         SITE_CHG, tot_all_prev, tot_all, s_share2, s_share1, S_CHG - SITE_CHG)),
    ("3. 下载大盘：同步走高", "本期 {:,} vs 上期 {:,}，跨期 {:+.1f}%。逐日看假期极值突出："
                        "10/2（11,934）、10/3（11,654）、10/4（11,177）、10/5（10,483）、10/1（10,755）连续五天破万，"
                        "假期后回落至 3,000 量级，10/11 又冲高至 10,464".format(dl_total, dl_total_prev, DL_CHG)),
    ("4. 搜索榜最大异动（非端游）", "《OVERPEAK》（中文名「巅峰崛起」、玩家称「祖国人模拟器」）搜索 318,165 次、"
                   "跨期 +1082%，跃居端游搜索第 2；但实为国际服手游（包名 com.rusergames.overpeak，安装包约 300MB），"
                   "热度主要来自移动端与渠道站导流 —— 神策搜索源不分端手游，跨端外溢会污染端游榜，"
                   "该条不宜按端游标的排位与配资源"),
    ("5. 搜索爆发榜（新品类）", "模拟驾驶成为假期最大赢家：巴士模拟 +1280.8%、软体汽车 +577.1%、"
                       "极限竞速 +128.0%；梦想之路 +195.2%、王国保卫战 +135.6% 为补齐词库后的真实量级"),
    ("6. 下载端最强共振", "漫威蜘蛛侠2（8,212，+278.4%）搜索 +216.4% 双源齐爆；"
                    "系列作迈尔斯莫拉莱斯 +148.1%，IP 集中爆发"),
    ("7. 老爆款退潮", "渔力全开下载 5,305 跨期 -39.5%（大盘 +46.0%，跑输约 86 个百分点），"
                   "搜索 -0.8%（大盘 +72.9%）—— 从双源第 1 退至下载第 3，进入存量期"),
    ("8. 搜索涨幅榜", "；".join("{}({})".format(r["端游名称"], r["环比"]) for _, r in RISE.iterrows())),
    ("9. 搜索回落榜", "；".join("{}({})".format(r["端游名称"], r["环比"]) for _, r in FALL.iterrows()) or "无"),
    ("10. 鲸云下载榜", "；".join("{}({:,})".format(r["游戏名称"], int(r["本期下载"])) for _, r in DLTOP.iterrows())),
    ("11. 鲸云增长榜", "；".join("{}({})".format(r["游戏名称"], r["环比"]) for _, r in DLRISE.iterrows()) or "无"),
    ("12. 鲸云回落榜", "；".join("{}({})".format(r["游戏名称"], r["环比"]) for _, r in DLLOSS.iterrows()) or "无"),
    ("", ""),
    ("三、运营建议", ""),
    ("1. 先核实《OVERPEAK》平台属性（最高优先）", "搜索已冲到端游第 2（31.8 万次）、单期 +1082%，但实为国际服手游。"
                              "上架价值取决于鲸云是否承接安卓云游戏 —— 若只做端游云化，建议转入「观察项」而非投资源位。"
                              "本期真金白银的端游增量在「模拟驾驶」与「IP 大作」两条线"),
    ("2. 抓「模拟驾驶」假期红利", "巴士模拟（+1280.8%）、极限竞速地平线5（下载 +110.1%）、遨游中国2（+51.3%）、"
                        "欧卡系列同步走高 —— 拟真驾驶是本期最集中的正增长品类，建议集中配资源位"),
    ("3. 解压/短时长品类补位", "软体汽车（搜索 +577.1%）、尖叫才能跑（下载 +51.4%）、午夜轮班（+54.9%）、"
                       "恶魔轮盘（+127.6%）—— 低配、短时长、即开即玩，云游戏转化路径最短"),
    ("4. 漫威蜘蛛侠 IP 打包推", "蜘蛛侠2（+278.4%）与迈尔斯莫拉莱斯（+148.1%）双作齐涨，"
                        "建议做「蜘蛛侠系列」组合位，承接电影/剧集热度"),
    ("5. 渔力全开转守成（关键）", "下载 -39.5%、搜索 -0.8%，双源均已跑输大盘。"
                           "建议从「拉新投放」转向「存量运营 + 组合套餐」，避免继续重投资源位"),
    ("6. 补入新词库条目的运营跟进", "梦想之路（搜索 +195.2%）、王国保卫战（+135.6%）为新增覆盖，"
                          "其中王国保卫战系列已在鲸云上架，可优先做「搜索词 → 专题页」的承接"),
    ("7. 警惕脉冲型热度", "UBERMOSH:OMEGA 单日峰值 = 历史峰值 17.49 万（当前回落至 2.76 万）、"
                    "逃生试炼 24h 峰值 10.9 万 —— 属限免/活动脉冲，勿按长线热度配置资源"),
    ("", ""),
    ("四、外部环境", ""),
    ("版号与新品节奏", "9 月批次于 9/30 公布（落在本期内）：209 款获批（国产 206 + 进口 3），"
                  "年内累计 1,571 款（国产 1,525 + 进口 46），前三季度同比 +23%；15 款审批变更中"
                  "《绒爪行动》更名《绒雪行动》并新增客户端、《潜水员戴夫》新增 PS5 版本 ——「手游补端」仍是可锁定的标的来源。"
                  "端游侧新品节奏：《永恒之塔2》9/30 开服（在线 21.1 万、Steam 第 4）、"
                  "《Deskrawl: Idle ARPG》放置新游（4.43 万）"),
    ("Steam 榜单新面孔", "AION 2（9/30 上线，在线 21.1 万、升至第 4）、Deskrawl: Idle ARPG（放置挂机，4.43 万）、"
                     "UBERMOSH:OMEGA（脉冲 17.5 万）；老牌 MMORPG 回榜：俄罗斯钓鱼4、MapleStory"),
]
ovdf = pd.DataFrame(ov, columns=["项", "内容"])

# ---------------- 写 Excel ----------------
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

HDR_FILL = PatternFill("solid", fgColor="1F4E79")
HDR_FONT = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
BDY_FONT = Font(name="微软雅黑", size=10)
UP_FONT = Font(name="微软雅黑", size=10, color="C00000", bold=True)
DN_FONT = Font(name="微软雅黑", size=10, color="008000", bold=True)
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def write_sheet(w, name, df, pct_cols=(), num_cols=()):
    df.to_excel(w, sheet_name=name, index=False)
    ws = w.sheets[name]
    for c in range(1, len(df.columns) + 1):
        cell = ws.cell(1, c)
        cell.fill, cell.font = HDR_FILL, HDR_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for r in range(2, len(df) + 2):
        for c in range(1, len(df.columns) + 1):
            ws.cell(r, c).font = BDY_FONT
            ws.cell(r, c).border = BORDER
        for cn in pct_cols:
            if cn in df.columns:
                v = df.iloc[r - 2][cn]
                if pd.notna(v) and isinstance(v, (int, float)):
                    cell = ws.cell(r, list(df.columns).index(cn) + 1)
                    cell.font = UP_FONT if v > 0 else DN_FONT
                    cell.number_format = '+0.0%;-0.0%;0.0%'
        for cn in num_cols:
            if cn in df.columns:
                ws.cell(r, list(df.columns).index(cn) + 1).number_format = '#,##0'
    for c, cn in enumerate(df.columns, 1):
        wdt = max(len(str(cn)) * 1.9, 11)
        if cn in ("代表性搜索词", "判定/说明", "玩法标签", "备注"):
            wdt = 46
        elif cn in ("开发者",):
            wdt = 26
        ws.column_dimensions[chr(64 + c) if c <= 26 else "A" + chr(64 + c - 26)].width = wdt
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 30


with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as w:
    write_sheet(w, "①搜索关键词源", s1, pct_cols=("环比%",),
                num_cols=("本期搜索", "上期搜索", "两期合计", "关键词数"))
    write_sheet(w, "②鲸云源", s2, pct_cols=("环比%",),
                num_cols=("本期下载", "上期下载", "两期合计"))
    write_sheet(w, "③Steam源", s3, num_cols=("当前在线(10/12)", "24h峰值", "历史峰值", "Steam排名"))
    write_sheet(w, "④三源关联重点表", s4)
    ws = w.sheets["④三源关联重点表"]
    ws.column_dimensions["A"].width = 22
    for col in ("B", "C", "D", "J"):
        ws.column_dimensions[col].width = 26
    ws.column_dimensions["K"].width = 60
    report = w.book.create_sheet("⑤周报概览")
    for i, (a, b) in enumerate(ov, 1):
        b = str(b).replace("**", "")          # Excel 不渲染 Markdown 加粗，去掉字面 **
        report.cell(i, 1, a)
        report.cell(i, 2, b)
        if a and not b:
            report.cell(i, 1).font = Font(name="微软雅黑", size=12, bold=True, color="1F4E79")
        else:
            report.cell(i, 1).font = Font(name="微软雅黑", size=10, bold=True)
            report.cell(i, 2).font = BDY_FONT
        report.cell(i, 2).alignment = Alignment(wrap_text=True, vertical="top")
    report.column_dimensions["A"].width = 22
    report.column_dimensions["B"].width = 110
print("\n✅ Excel:", OUT_XLSX)

# ---------------- 导出 看板 data ----------------
data = {
    "meta": {"range": _range_text(CUR_LAB), "cur": CUR_LAB, "prev": PREV_LAB,
             "snapshot": CFG.run_date or TODAY.isoformat(), "mode": "cross_period"},
    "kpi": {
        "search_total": tot_all, "search_total_prev": tot_all_prev,
        "search_hit": tot_hit, "search_hit_prev": tot_hit_prev,
        "ratio": round(tot_hit / tot_all * 100, 1),
        "ratio_prev": round(tot_hit_prev / tot_all_prev * 100, 1),
        "games_s": int((s1["本期搜索"] > 0).sum()), "games_s_prev": int((s1["上期搜索"] > 0).sum()),
        "games_dl": int((s2["本期下载"] > 0).sum()), "games_dl_prev": int((s2["上期下载"] > 0).sum()),
        "games_st": len(s3),
        "dl_total": dl_total, "dl_total_prev": dl_total_prev,
        "dl_chg": DL_CHG, "s_chg": S_CHG, "site_chg": SITE_CHG,
        "share1": round(s_share1, 2), "share2": round(s_share2, 2),
        "dl1": s2.iloc[0]["游戏名称"], "dl1v": int(s2.iloc[0]["本期下载"]),
        "st1": s3.iloc[0]["中文名称"], "st1v": int(s3.iloc[0]["当前在线(10/12)"]),
    },
    "trend": {
        "labels": [f"上期 {PREV_LAB}", f"本期 {CUR_LAB}"],
        "series": [
            {"name": "端游搜索", "data": [tot_hit_prev, tot_hit]},
            {"name": "鲸云下载", "data": [dl_total_prev, dl_total]},
        ],
    },
    "daily": {"labels": list(daily["date"]), "values": [int(v) for v in daily["value"]]},
    "cmp": [{"n": r["端游名称"], "w1": int(r["本期搜索"]), "w2": int(r["上期搜索"]),
             "chg": (None if pd.isna(r["环比%"]) else float(r["环比%"]))}
            for _, r in s1.nlargest(12, "本期搜索").iterrows()],
    "cmp_dl": [{"n": r["游戏名称"], "w1": int(r["本期下载"]), "w2": int(r["上期下载"]),
                "chg": (None if pd.isna(r["环比%"]) else float(r["环比%"]))}
               for _, r in s2.nlargest(10, "本期下载").iterrows()],
    "top_search": [{"n": r["端游名称"], "v": int(r["本期搜索"]), "p": int(r["上期搜索"]),
                    "chg": (None if pd.isna(r["环比%"]) else float(r["环比%"]))}
                   for _, r in s1.nlargest(15, "本期搜索").iterrows()],
    "top_dl": [{"n": r["游戏名称"], "v": int(r["本期下载"]), "p": int(r["上期下载"]),
                "chg": (None if pd.isna(r["环比%"]) else float(r["环比%"]))}
               for _, r in s2.nlargest(15, "本期下载").iterrows()],
    "top_steam": [{"n": r["中文名称"], "e": r["游戏名称(原名)"], "v": int(r["当前在线(10/12)"]), "p": int(r["历史峰值"])}
                  for _, r in s3.nlargest(15, "当前在线(10/12)").iterrows()],
    "top_peak": [{"n": r["中文名称"], "v": int(r["历史峰值"]), "p18": int(r["当前在线(10/12)"])}
                 for _, r in s3.nlargest(15, "历史峰值").iterrows()],
    "rise": [{"n": r["端游名称"], "chg": float(r["环比%"]), "v": int(r["本期搜索"]), "p": int(r["上期搜索"])}
             for _, r in RISE.iterrows()],
    "fall": [{"n": r["端游名称"], "chg": float(r["环比%"]), "v": int(r["本期搜索"]), "p": int(r["上期搜索"])}
             for _, r in FALL.iterrows()],
    "dl_rise": [{"n": r["游戏名称"], "chg": float(r["环比%"]), "v": int(r["本期下载"]), "p": int(r["上期下载"])}
                for _, r in DLRISE.iterrows()],
    "dl_fall": [{"n": r["游戏名称"], "chg": float(r["环比%"]), "v": int(r["本期下载"]), "p": int(r["上期下载"])}
                for _, r in DLLOSS.iterrows()],
    "cat": [{"c": k, "n": int(v["端游名称"]), "s": int(v["本期搜索"]), "p": int(v["上期搜索"])}
            for k, v in s1.groupby("品类").agg({"端游名称": "count", "本期搜索": "sum", "上期搜索": "sum"})
            .sort_values("本期搜索", ascending=False).iterrows()],
    "s1": json.loads(s1.to_json(orient="records", force_ascii=False)),
    "s2": json.loads(s2.to_json(orient="records", force_ascii=False)),
    "s3": json.loads(s3.to_json(orient="records", force_ascii=False)),
    "s4": json.loads(s4.to_json(orient="records", force_ascii=False)),
    "overview": [{"k": a, "v": b} for a, b in ov if a or b],
}
json.dump(data, open(f"{TMP}/data.json", "w", encoding="utf-8"), ensure_ascii=False)
print("✅ data.json:", {k: (len(v) if isinstance(v, list) else "-") for k, v in data.items()})
print("\n--- ④重点表 ---")
print(s4[["游戏", "搜索端(跨期环比)", "鲸云下载(排名)", "Steam端(在线/峰值)"]].to_string(index=False))
