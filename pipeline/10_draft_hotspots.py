# -*- coding: utf-8 -*-
"""10_draft_hotspots.py —— 12 条热点的半自动初稿（机器挑料 + 模板句，人工润色）

为什么需要它
============
05_gen_board.py 里的 HOT 是每期手写的 12 条。手写有两个毛病：
  ① 换期容易忘改 —— 产出「数据是新的、热点还是上期的」假报告（08 门禁专治这个）；
  ② 12 条里至少 9 条本来就能规则化选出（涨幅第一、在线第一、退潮第一…），
     人真正做的只有两件事：「确认选对标的」+「补一句因果」。
所以把机械部分交给脚本，人只改语感和归因。

它产出三个文件（都落在中间产物目录）
====================================
  hot_draft.json    12 条热点初稿            → 05 --hot 读取
  covers_plan.json  配套封面计划              → 04b 自动读取（决定抓哪几张 Steam 主视觉）
  hot_review.md     人工校对清单              → 按「必须改 / 建议改」列出待办

它绝不替你做两件事
==================
  ① 第 11 条「版号重点」：要查国家新闻出版署当期公告，脚本拿不到 → 标 _needs_human
  ② 涨跌的**原因**：模板句只陈述数字与事实，归因必须人来写（每条 _hint 给了提示）

只要还有 _needs_human 未清，05 会拒绝出看板（--allow-draft 可放行但会打草稿水印，
08 门禁照样拦），因此「半成品被当成成品发出去」这条路是堵死的。

用法
====
    python 10_draft_hotspots.py              # 用 config.json 的当前期
    python 10_draft_hotspots.py --show       # 只打印，不落盘
    python 10_draft_hotspots.py --out <目录>  # 指定输出目录（默认中间产物目录）
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _cfg  # noqa: E402

CFG = _cfg.CFG

# 封面兜底配色（Steam 抓取失败时程序化封面用）。按槽位轮转，无需人工指定。
PALETTE = [
    dict(c1=(12, 18, 46), c2=(162, 34, 44), c3=(244, 132, 108), glow=(255, 150, 120)),
    dict(c1=(8, 20, 46), c2=(20, 96, 140), c3=(120, 220, 226), glow=(140, 235, 240)),
    dict(c1=(34, 20, 14), c2=(170, 96, 58), c3=(250, 206, 168), glow=(255, 220, 180)),
    dict(c1=(14, 18, 40), c2=(96, 52, 148), c3=(214, 166, 240), glow=(226, 180, 255)),
    dict(c1=(12, 26, 32), c2=(40, 110, 116), c3=(150, 216, 208), glow=(170, 236, 226)),
    dict(c1=(26, 12, 40), c2=(176, 58, 120), c3=(252, 168, 120), glow=(255, 180, 130)),
    dict(c1=(18, 26, 38), c2=(46, 62, 86), c3=(122, 140, 166), glow=(130, 150, 180)),
    dict(c1=(10, 22, 52), c2=(30, 78, 150), c3=(120, 196, 236), glow=(140, 210, 255)),
    dict(c1=(24, 22, 12), c2=(140, 118, 32), c3=(240, 220, 140), glow=(250, 236, 170)),
    dict(c1=(20, 14, 30), c2=(84, 40, 120), c3=(180, 140, 230), glow=(200, 170, 250)),
]

# 已知已有官方或成熟手游版的作品 —— 仅作「端游转手游候选」的初筛排除，需人工复核。
# ⚠️ 必须**精确匹配**，不能用子串：`杀戮尖塔` 是 `杀戮尖塔2` 的子串，但后者是本期新作、
#    尚无手游版。用子串会把新作误杀（本项目踩过的老坑，见 docs/05-坑位清单.md）。
MOBILE_ALREADY = {
    "星露谷物语", "泰拉瑞亚", "饥荒", "饥荒联机版", "以撒的结合", "以撒的结合：重生",
    "几何冲刺", "盖瑞模组", "杀戮尖塔", "我的世界",
}

# 触屏适配度打分：命中越多越适合端转手
TOUCH_TAGS = {
    "卡组构筑": 3, "卡牌": 3, "Roguelike": 2, "roguelike": 2,
    "挂机": 3, "放置": 3, "桌面伴侣": 3, "休闲": 2,
    "模拟": 2, "殖民地模拟": 3, "农场模拟": 3, "生活模拟": 2,
    "策略": 2, "解谜": 2, "音乐": 2, "塔防": 2, "经营": 3,
    "像素": 1, "单人": 1,
}


# ----------------------------------------------------------------- 基础工具
def num(v, default=None):
    """把 "8,212" / "+278.4%" / 8212 / None 统一成 float 或 int。"""
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return v
    s = str(v).replace(",", "").replace("%", "").replace("+", "").strip()
    try:
        return float(s)
    except ValueError:
        return default


def find_key(rows, prefix):
    """在表头里按前缀找列名 —— 列名带日期（当前在线(10/12)）也不能写死。"""
    if not rows:
        return None
    for k in rows[0]:
        if str(k).startswith(prefix):
            return k
    return None


def size_gb(s):
    """'1.16GB' / '0.31GB' / '—' → float(GB)，未知返回 None。"""
    if s is None:
        return None
    m = re.search(r"([\d.]+)\s*GB", str(s), re.I)
    return float(m.group(1)) if m else None


def fmt(n):
    return "{:,}".format(int(round(n))) if n is not None else "—"


def pct(v, sign=True):
    if v is None:
        return "—"
    return ("{:+.1f}%" if sign else "{:.1f}%").format(v)


def item(tag, cls, title, desc, src, hint, **kw):
    d = {"tag": tag, "cls": cls, "title": title, "desc": desc, "src": src, "_hint": hint}
    d.update(kw)
    return d


def cover_key(appid):
    return "s%s" % appid


def attach_cover(it, appid, en, cn, big, bigsub, idx):
    """给热点挂封面：有 appid 走 Steam 主视觉，无 appid 返回 None（改走程序化）。"""
    it["_appid"] = appid
    if appid:
        it["cover"] = cover_key(appid)
        plan = dict(steam=str(appid), en=en or "", cn=cn or "", tag=it["tag"],
                    big=big, bigsub=bigsub, **PALETTE[idx % len(PALETTE)])
        return it, cover_key(appid), plan
    return it, None, None


# ----------------------------------------------------------------- 取数
def load(tmp: Path):
    p = tmp / "data.json"
    if not p.is_file():
        sys.exit("[中止] 找不到 %s —— 先跑 04_build_report.py" % p)
    d = json.loads(p.read_text(encoding="utf-8"))
    for k in ("kpi", "s1", "s2", "s3", "s4", "top_search", "top_dl", "top_steam",
              "rise", "fall", "dl_rise", "dl_fall", "cat"):
        if k not in d:
            sys.exit("[中止] data.json 缺字段 %s —— data.json 版本过旧，重跑 04" % k)
    return d


def period_start(data):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", str((data.get("meta") or {}).get("range", "")))
    return "%s-%s-%s" % m.groups() if m else None


# ----------------------------------------------------------------- 规则
def build_hot(data):
    k = data["kpi"]
    s3 = data["s3"]
    online_k = find_key(s3, "当前在线")
    items, plans = [], {}
    used = set()          # 已用过的游戏名，避免同一款占两个槽位

    def take(name):
        if name in used:
            return False
        used.add(name)
        return True

    # ---- 1) 大盘总览（纯数据，无需 appid）
    s_chg = num(k.get("s_chg"))
    site = num(k.get("site_chg"))
    dl_chg = num(k.get("dl_chg"))
    edge = (s_chg - site) if (s_chg is not None and site is not None) else None
    items.append(item(
        "📈 大盘总览", "up" if (s_chg or 0) >= 0 else "down",
        "端游两源同涨：搜索 {:s}、下载 {:s}".format(pct(s_chg), pct(dl_chg)),
        "本期端游搜索命中 {n} 款 / {hit} 次，跨期 {sc}（上期 {prev} 次）；"
        "鲸云下载 {dl} 次，跨期 {dc}（上期 {dlp} 次）。全站搜索同期 {sz}，"
        "端游占比由 {r2}% 变为 {r1}%{edge}。".format(
            n=k.get("games_s"), hit=fmt(k.get("search_hit")), sc=pct(s_chg),
            prev=fmt(k.get("search_hit_prev")), dl=fmt(k.get("dl_total")), dc=pct(dl_chg),
            dlp=fmt(k.get("dl_total_prev")), sz=pct(site),
            r2=k.get("share2"), r1=k.get("share1"),
            edge="" if edge is None else
            "，{}大盘 {:.1f} 个百分点".format("跑赢" if edge >= 0 else "跑输", abs(edge))),
        "神策搜索 / 鲸云下载",
        "判断口径：若本期或上期含法定假期，绝对涨幅会失真，必须用「端游 vs 全站」的超额来讲。",
        vizdata={"tt": "本期跨期涨跌", "rows": [
            {"n": "端游搜索", "v": s_chg if s_chg is not None else 0},
            {"n": "全站搜索", "v": site if site is not None else 0},
            {"n": "鲸云下载", "v": dl_chg if dl_chg is not None else 0}],
            "sub": "端游搜索{}全站 {:+.1f}pp，份额 {}%".format(
                "跑赢" if (edge or 0) >= 0 else "跑输", edge or 0, k.get("share1"))},
    ))

    # ---- 2) 搜索涨幅冠军（要求足够大的基数，避免小基数噪音）
    floor = max(20000, (num(k.get("search_hit"), 0) or 0) * 0.004)
    r2 = next((x for x in data["rise"] if num(x.get("v"), 0) >= floor), None)
    if r2 and take(r2["n"]):
        items.append(item(
            "🚀 搜索涨幅冠军", "up",
            "《{n}》搜索 {chg}，为本期增速第一（{v} 次）".format(
                n=r2["n"], chg=pct(num(r2.get("chg"))), v=fmt(r2.get("v"))),
            "搜索量由上期 {p} 次升至 {v} 次，跨期 {chg}；大盘同期 {sc}，"
            "超额约 {ex:+.1f} 个百分点。基数量级足够（已过滤低于 {fl} 次的小基数噪音）。".format(
                p=fmt(r2.get("p")), v=fmt(r2.get("v")), chg=pct(num(r2.get("chg"))),
                sc=pct(s_chg), ex=(num(r2.get("chg"), 0) - (s_chg or 0)), fl=fmt(floor)),
            "神策搜索",
            "必须补：为什么涨？新品/版本节点/短视频导流/促销，四选一并给证据。",
            vizdata={"tt": "相对大盘的超额", "rows": [
                {"n": "该款", "v": round(num(r2.get("chg"), 0), 1)},
                {"n": "大盘", "v": round(s_chg or 0, 1)}],
                "sub": "{} {}，大盘 {}".format(
                    r2["n"], pct(num(r2.get("chg"))), pct(s_chg))},
        ))

    # ---- 3) 下载涨幅冠军
    r3 = next((x for x in data["dl_rise"] if num(x.get("v"), 0) >= 300), None)
    if r3 and take(r3["n"]):
        items.append(item(
            "📥 下载涨幅冠军", "up",
            "《{n}》鲸云下载 {chg}，增速居下载端首位".format(
                n=r3["n"], chg=pct(num(r3.get("chg")))),
            "下载量由上期 {p} 次升至 {v} 次，跨期 {chg}；下载大盘同期 {dc}，"
            "超额约 {ex:+.1f} 个百分点。".format(
                p=fmt(r3.get("p")), v=fmt(r3.get("v")), chg=pct(num(r3.get("chg"))),
                dc=pct(dl_chg), ex=(num(r3.get("chg"), 0) - (dl_chg or 0))),
            "鲸云下载",
            "必须补：是新品首发、版本更新，还是被搜索端带起来的？结合 Steam 在线判断。",
            vizdata={"tt": "相对下载大盘的超额", "rows": [
                {"n": "本期", "v": round(num(r3.get("chg"), 0), 1)},
                {"n": "大盘", "v": round(dl_chg or 0, 1)}],
                "sub": "{} {}，大盘 {}".format(r3["n"], pct(num(r3.get("chg"))), pct(dl_chg))},
        ))

    # ---- 4) 搜索榜首
    t4 = (data["top_search"] or [None])[0]
    if t4 and take(t4["n"]):
        items.append(item(
            "🏆 搜索榜首", "up",
            "《{n}》{v} 次搜索蝉联端游第一（{chg}）".format(
                n=t4["n"], v=fmt(t4.get("v")), chg=pct(num(t4.get("chg")))),
            "本期 {v} 次、上期 {p} 次，跨期 {chg}；大盘 {sc}，"
            "{rel}。头部单品占端游搜索总量约 {share:.1f}%。".format(
                v=fmt(t4.get("v")), p=fmt(t4.get("p")), chg=pct(num(t4.get("chg"))),
                sc=pct(s_chg),
                rel="跑赢大盘".format() if num(t4.get("chg"), 0) >= (s_chg or 0) else "跑输大盘",
                share=(num(t4.get("v"), 0) / max(num(k.get("search_hit"), 1), 1) * 100)),
            "神策搜索",
            "建议补：常青款是否值得继续给资源位；与云游戏端转化率交叉看。",
            vizdata={"tt": "榜首 vs 大盘（跨期）", "rows": [
                {"n": "榜首", "v": round(num(t4.get("chg"), 0), 1)},
                {"n": "大盘", "v": round(s_chg or 0, 1)}],
                "sub": "{} {} 次，占端游搜索 {:.1f}%".format(
                    t4["n"], fmt(t4.get("v")),
                    num(t4.get("v"), 0) / max(num(k.get("search_hit"), 1), 1) * 100)},
        ))

    # ---- 5) Steam 在线王
    t5 = (data["top_steam"] or [None])[0]
    if t5 and take(t5["n"]):
        row = next((r for r in s3 if r.get("中文名称") == t5["n"]), None)
        it = item(
            "🎮 Steam 在线王", "up",
            "《{n}》{v} 人在线，居本期端游在线第一".format(
                n=t5["n"], v=fmt(t5.get("v"))),
            "当前在线 {v}、24h 峰值 {p}；{extra}".format(
                v=fmt(t5.get("v")), p=fmt(t5.get("p")),
                extra=("玩法标签 {}、安装 {}。".format(row.get("玩法标签"), row.get("安装大小"))
                       if row else "该款未带完整元数据，需人工核对。")),
            "SteamDB",
            "必须补：这个在线量能否支撑云游戏并发？安装体积与显存门槛决定上架成本。",
        )
        it, ck, plan = attach_cover(
            it, (row or {}).get("appid"),
            (row or {}).get("游戏名称(原名)"), t5["n"],
            fmt(t5.get("v")), "当前在线 · 24h 峰值 %s" % fmt(t5.get("p")), 2)
        if ck:
            plans[ck] = plan
        items.append(it)

    # ---- 6) 三源共振（搜索 + 下载 + Steam 在线都有数据）
    k_s, k_d, k_t = find_key(data["s4"], "搜索端"), find_key(data["s4"], "鲸云下载"), find_key(data["s4"], "Steam端")
    tri = []
    for r in data["s4"]:
        st, dl, tw = str(r.get(k_s, "")), str(r.get(k_d, "")), str(r.get(k_t, ""))
        if ("✅" in st or "新增" in st) and "第" in dl and "第" in tw and "不在本期" not in tw:
            m = re.search(r"([\d,]{3,})", st)
            tri.append((num(m.group(1), 0) if m else 0, r))
    tri.sort(key=lambda x: -x[0])
    t6 = next(((v, r) for v, r in tri if r["游戏"] not in used), None)
    if t6:
        _, r6 = t6
        take(r6["游戏"])
        it = item(
            "🔗 三源共振", "up",
            "《{n}》三源同时在线，为本期共振度最高的单品".format(n=r6["游戏"]),
            "搜索端 {s}、鲸云下载 {d}、Steam {t}；玩法标签 {tag}，安装 {sz}。"
            "三源同时有量意味着「有认知 + 有下载意愿 + 有实际在线」，是云游戏最该锁的标的类型。".format(
                s=r6.get(k_s), d=r6.get(k_d), t=r6.get(k_t),
                tag=r6.get("玩法标签"), sz=r6.get("安装大小")),
            "神策 / 鲸云 / SteamDB",
            "建议补：这类标的是否已进资源位？三源共振款的转化率通常显著高于单源款。",
        )
        it, ck, plan = attach_cover(
            it, r6.get("appid"), r6.get("游戏名称(原名)") if "游戏名称(原名)" in r6 else r6["游戏"],
            r6["游戏"], r6.get("安装大小"), "安装体积 · %s" % r6.get("玩法标签"), 4)
        if ck:
            plans[ck] = plan
        items.append(it)

    # ---- 7) 新游观察（优先「本期发行」，退一档取「近一月发行」，都空则跳过）
    ps = period_start(data)

    def _date(r):
        d = str(r.get("发行日期") or "")[:10]
        return d if re.match(r"\d{4}-\d{2}-\d{2}$", d) else None

    tiers = []
    if ps:
        tiers.append(("本期发行", lambda d: d >= ps))
        try:
            edge = (dt.date.fromisoformat(ps) - dt.timedelta(days=30)).isoformat()
            tiers.append(("近一月发行", lambda d, e=edge: d >= e))
        except ValueError:
            pass
    tiers.append(("近一年新游", lambda d: True))

    t7, t7_tier = None, None
    for tier_name, cond in tiers:
        pool = [r for r in s3
                if str(r.get("近一年内上线")) == "是" and _date(r) and cond(_date(r))
                and r.get("中文名称") not in used]
        if pool:
            pool.sort(key=lambda r: -num(r.get(online_k), 0))
            t7, t7_tier = pool[0], tier_name
            break

    if t7:
        take(t7["中文名称"])
        ol = num(t7.get(online_k), 0)
        it = item(
            "🆕 新游观察", "up",
            "《{n}》发行于 {d}，当前 {v} 人在线，为{tier}最高".format(
                n=t7["中文名称"], d=str(t7.get("发行日期"))[:10], v=fmt(ol), tier=t7_tier),
            "本期 Steam 端游名录里，{tier}的在线最高者：发行 {d}、当前在线 {v}、"
            "24h 峰值 {p}、历史峰值 {h}；玩法标签 {tag}，安装 {sz}。"
            "新游看首月曲线，不看首发峰值 —— 峰值靠宣发，次月留存才决定要不要长期给位。".format(
                tier=t7_tier, d=str(t7.get("发行日期"))[:10], v=fmt(ol),
                p=fmt(t7.get("24h峰值")), h=fmt(t7.get("历史峰值")),
                tag=t7.get("玩法标签"), sz=t7.get("安装大小")),
            "SteamDB / Steam 商店",
            "必须补：好评率与首发活动；若本期无新游进榜（如被口径排除），"
            "这条要换成行业侧的新品事件（外部检索），别硬凑。",
        )
        it, ck, plan = attach_cover(
            it, t7.get("appid"), t7.get("游戏名称(原名)"), t7["中文名称"], fmt(ol),
            "当前在线 · 发行 %s" % str(t7.get("发行日期"))[:10], 5)
        if ck:
            plans[ck] = plan
        items.append(it)

    # ---- 8) 退潮预警（搜索跌 vs 下载跌，取更狠的那个；带基数下限，避免小基数噪音）
    # 搜落下限 2 万、下载下限 1,500 —— 上期基数低于此值，跌幅再大也不构成运营信号。
    floors = {"搜索": 20000, "下载": 1500}
    cands = []
    for side, lst in (("搜索", data["fall"]), ("下载", data["dl_fall"])):
        for x in lst or []:
            if abs(num(x.get("chg"), 0)) >= 15 and num(x.get("p"), 0) >= floors[side]:
                cands.append((side, x))
    cands.sort(key=lambda c: abs(num(c[1].get("chg"), 0)), reverse=True)
    t8 = next((c for c in cands if c[1]["n"] not in used), None)
    if t8:
        side, r8 = t8
        take(r8["n"])
        base = s_chg if side == "搜索" else dl_chg
        it = item(
            "📉 退潮预警", "down",
            "《{n}》{side} {chg}，为本期{dn}端跌幅最大".format(
                n=r8["n"], side=side, chg=pct(num(r8.get("chg"))),
                dn="搜索" if side == "搜索" else "下载"),
            "{side}量由上期 {p} 降至 {v}，跨期 {chg}；同期{side}大盘 {dc}，"
            "跑输约 {gap:.1f} 个百分点。".format(
                side=side, p=fmt(r8.get("p")), v=fmt(r8.get("v")),
                chg=pct(num(r8.get("chg"))), dc=pct(base),
                gap=abs((base or 0) - num(r8.get("chg"), 0))),
            "神策搜索" if side == "搜索" else "鲸云下载",
            "必须补：是自然退潮、被同品类新品分流，还是一次性事件结束？决定要不要撤资源位。",
            vizdata={"tt": "{} vs 大盘（跨期）".format(side), "rows": [
                {"n": "该款", "v": round(num(r8.get("chg"), 0), 1)},
                {"n": "大盘", "v": round(base or 0, 1)}],
                "sub": "{} {}，大盘 {}".format(r8["n"], pct(num(r8.get("chg"))), pct(base))},
        )
        items.append(it)

    # ---- 9) 跨端外溢警示（搜索暴涨但 Steam 端查无此游 ⇒ 大概率不是端游）
    s3_names = {r.get("中文名称") for r in s3} | {r.get("游戏名称(原名)") for r in s3}
    leak = None
    for r in data["rise"]:
        chg, v, nm = num(r.get("chg"), 0), num(r.get("v"), 0), r["n"]
        if chg >= 100 and v >= 80000 and nm not in s3_names and nm not in used:
            leak = r
            break
    if leak:
        take(leak["n"])
        items.append(item(
            "⚠️ 跨端外溢", "hot",
            "《{n}》搜索 {chg} 但 Steam 端查无此游 —— 疑似非端游".format(
                n=leak["n"], chg=pct(num(leak.get("chg")))),
            "搜索 {v} 次、跨期 {chg}，但本期 Steam Top100 与元数据里都没有对应条目。"
            "神策搜索源不区分端游/手游，这类脉冲多来自移动端渠道铺量与短视频导流。"
            "**先核实平台属性再解读，不要直接写进运营建议。**".format(
                v=fmt(leak.get("v")), chg=pct(num(leak.get("chg")))),
            "神策搜索 × SteamDB",
            "必须核：搜「中文名 + 手游下载」看渠道站是否集中铺量、看包名与安装包体积、"
            "比对 Steam 同名 appid 的真实在线。核实后二选一：写进警示，或调词库排除。",
            vizdata={"tt": "该条 vs 大盘（跨期）", "rows": [
                {"n": "该条", "v": round(num(leak.get("chg"), 0), 1)},
                {"n": "大盘", "v": round(s_chg or 0, 1)}],
                "sub": "{} {} 次（{}），Steam 端无对应条目".format(
                    leak["n"], fmt(leak.get("v")), pct(num(leak.get("chg"))))},
        ))
    else:
        # 兜底：品类结构（也是纯数据，不需要 appid）
        cats = sorted(data["cat"], key=lambda c: -num(c.get("s"), 0))[:5]

        def _cchg(c):
            s, p = num(c.get("s"), 0), num(c.get("p"), 0)
            return (s / p * 100 - 100) if p else None

        items.append(item(
            "📊 品类结构", "up",
            "本期 {} 个品类中，{} 占搜索量最高".format(
                len(data["cat"]), cats[0]["c"] if cats else "—"),
            "；".join("{}（{} 款，搜索 {} 次，跨期 {}）".format(
                c["c"], c.get("n"), fmt(c.get("s")), pct(_cchg(c))) for c in cats)
            + "。品类口径用于判断资源位该往哪边倾斜。",
            "神策搜索",
            "建议补：与上期品类结构对比，指出哪一类在结构性上升。",
            vizdata={"tt": "品类搜索量（本期）", "rows": [
                {"n": c["c"], "v": round(num(c.get("s"), 0) / 10000, 1)} for c in cats],
                "sub": "单位：万次"},
        ))

    # ---- 10) 独立游戏在线王
    ind = [r for r in s3 if str(r.get("独立游戏")) == "是"]
    ind.sort(key=lambda r: -num(r.get(online_k), 0))
    t10 = next((r for r in ind if r.get("中文名称") not in used), None)
    if t10:
        take(t10["中文名称"])
        ol = num(t10.get(online_k), 0)
        it = item(
            "🎯 独立游戏王", "up",
            "《{n}》{v} 人在线，居本期独立游戏第一".format(n=t10["中文名称"], v=fmt(ol)),
            "本期共 {cnt} 款独立游戏进榜，该款在线最高：当前 {v}、安装 {sz}、"
            "玩法标签 {tag}。轻量独立游戏是云游戏上架成本最低的一档。".format(
                cnt=len(ind), v=fmt(ol), sz=t10.get("安装大小"), tag=t10.get("玩法标签")),
            "SteamDB",
            "建议补：小体量高在线的款是否已进云游戏库？这类是「低成本铺量」的主力。",
        )
        it, ck, plan = attach_cover(
            it, t10.get("appid"), t10.get("游戏名称(原名)"), t10["中文名称"], fmt(ol),
            "当前在线 · 安装 %s" % t10.get("安装大小"), 6)
        if ck:
            plans[ck] = plan
        items.append(it)

    # ---- 11) 版号重点（必须人工：要查国家新闻出版署当期公告）
    items.append(item(
        "📜 版号重点", "hot",
        "[待人工填写] 本期版号批次与关键产品",
        "[待人工填写] 查国家新闻出版署当期公告：本批数量、国产/进口拆分、年内累计、"
        "重点产品与「手游补端」变更名单。脚本无法获取此数据，必须人工核实后改写。",
        "国家新闻出版署",
        "必须做：确认本批公布日是否落在本期内；写清「本批 + 上期累计 == 本期累计」自洽校验；"
        "不拿上一批冒充当期。",
        cover="license", _needs_human=True))
    plans["license"] = dict(
        en="GAME LICENSES", cn="版号动态 · 待人工填写",
        tag="版号 · 待核对", big="---", bigsub="[待人工填写] 本批数量 / 年内累计",
        **PALETTE[7])

    # ---- 12) 端游转手游候选（按触屏适配 + 体积 + 人气打分挑 4 款）
    def mobile_score(r):
        gb = size_gb(r.get("安装大小"))
        tag = str(r.get("玩法标签") or "")
        touch = sum(w for t, w in TOUCH_TAGS.items() if t in tag)
        sc = float(touch)
        if touch == 0:
            sc -= 4                       # 没有任何触屏友好标签：降级
        if gb is None:
            sc -= 2                       # 体积未知，云化成本不可估
        elif gb <= 4:
            sc += (4 - gb) * 1.5          # 越小越加分
        elif gb > 8:
            sc -= 5                       # 过大，云化/移植成本高
        sc += (num(r.get(online_k), 0) / 10000) ** 0.5
        if str(r.get("中文名称")) in MOBILE_ALREADY:
            sc -= 100                     # 已有成熟手游版，实质排除
        return sc, touch > 0

    pool = [r for r in ind if r.get("中文名称") not in used]
    pool.sort(key=lambda r: -mobile_score(r)[0])
    # 优先「有触屏友好标签」的；凑不够 4 款再放宽（宁可给弱候选，也不放弃这一栏）
    picked = [r for r in pool if mobile_score(r)[0] > -50 and mobile_score(r)[1]][:4]
    if len(picked) < 4:
        picked += [r for r in pool if mobile_score(r)[0] > -50 and r not in picked]
        picked = picked[:4]
    keys = []
    for i, r in enumerate(picked):
        ck = cover_key(r.get("appid"))
        keys.append(ck)
        plans[ck] = dict(steam=str(r.get("appid")), en=r.get("游戏名称(原名)") or "",
                         cn="%s · %s" % (r.get("中文名称"), r.get("玩法标签") or ""),
                         tag="移植候选 · %s" % (str(r.get("玩法标签") or "").split("/")[0] or "独立"),
                         big=r.get("安装大小") or "—",
                         bigsub="安装体积 · 当前在线 %s" % fmt(num(r.get(online_k), 0)),
                         **PALETTE[(i + 3) % len(PALETTE)])
    items.append(item(
        "🎮 移植候选", "up",
        "端游转手游：本期 {} 款独立游戏里，这 4 款最值得谈".format(len(ind)),
        "从本期 {} 款 Steam 端游中筛出 {} 款独立游戏，按「适配触屏 + 体量小 + 人气在线 + "
        "尚无成熟手游版」四条标准打分，优先标的：{}。体积与在线均已实测。".format(
            len(s3), len(ind),
            "、".join("{}（{}，在线 {}）".format(
                r.get("中文名称"), r.get("安装大小") or "体积未知",
                fmt(num(r.get(online_k), 0))) for r in picked)),
        "Steam 在线 / 神策搜索 / 鲸云下载",
        "必须核：这 4 款是否已有官方或第三方手游版（脚本的排除表不可能覆盖全）；"
        "顺带看是否与第 11 条版号「补客户端」名单重合。",
        cover4=keys))

    return items, plans


# ----------------------------------------------------------------- 校对清单
def review_md(items, data):
    k = data["kpi"]
    lab = (data.get("meta") or {}).get("cur", "")
    lines = ["# 热点初稿校对清单 · %s" % lab, "",
             "> 由 `10_draft_hotspots.py` 生成。数字已全部核对自 `data.json`，"
             "**需要你动的是「归因」和「判断」**，不是数字。", "",
             "| # | 栏目 | 标的是谁 | 状态 | 必须做的事 |",
             "|---|---|---|---|---|"]
    for i, h in enumerate(items, 1):
        need = "🔴 必改" if h.get("_needs_human") else ("🟡 建议润色" if i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10) else "🟢 可用")
        lines.append("| %d | %s | %s | %s | %s |" % (
            i, h["tag"], h["title"][:40].replace("|", "/"), need,
            (h.get("_hint") or "").replace("|", "/")))
    lines += ["", "## 大盘基准（判断「跑赢/跑输」时用）", "",
              "| 指标 | 本期 | 上期 | 跨期 |", "|---|---|---|---|",
              "| 端游搜索 | %s | %s | %s |" % (fmt(k.get("search_hit")), fmt(k.get("search_hit_prev")), pct(num(k.get("s_chg")))),
              "| 全站搜索 | %s | %s | %s |" % (fmt(k.get("search_total")), fmt(k.get("search_total_prev")), pct(num(k.get("site_chg")))),
              "| 鲸云下载 | %s | %s | %s |" % (fmt(k.get("dl_total")), fmt(k.get("dl_total_prev")), pct(num(k.get("dl_chg")))),
              "", "## 改完后", "",
              "```bash",
              "python 04b_make_covers.py          # 自动读 covers_plan.json 抓封面",
              "python 05_gen_board.py --hot <中间产物目录>/hot_draft.json",
              "python 08_preflight_check.py       # 必须 PASS 才能发布",
              "```", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="12 条热点的半自动初稿")
    ap.add_argument("--out", help="输出目录（默认中间产物目录）")
    ap.add_argument("--show", action="store_true", help="只打印，不落盘")
    a = ap.parse_args()

    tmp = Path(a.out) if a.out else CFG.tmp
    data = load(tmp)
    items, plans = build_hot(data)

    if len(items) != 12:
        print("[警告] 生成 %d 条，期望 12 条 —— 数据缺失导致某条规则没有候选，请人工补" % len(items))

    if a.show:
        for i, h in enumerate(items, 1):
            print("%2d %-12s %s" % (i, h["tag"], h["title"]))
            print("     %s" % h["desc"][:160])
        return 0

    (tmp / "hot_draft.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    (tmp / "covers_plan.json").write_text(
        json.dumps(plans, ensure_ascii=False, indent=1), encoding="utf-8")
    (tmp / "hot_review.md").write_text(review_md(items, data), encoding="utf-8")

    need = [i for i, h in enumerate(items, 1) if h.get("_needs_human")]
    print("OK hot_draft.json     %d 条（封面计划 %d 张）" % (len(items), len(plans)))
    print("OK covers_plan.json   %s" % ", ".join(sorted(plans)))
    print("OK hot_review.md      校对清单")
    print()
    for i, h in enumerate(items, 1):
        flag = "🔴" if h.get("_needs_human") else "  "
        print("  %s %2d %-12s %s" % (flag, i, h["tag"], h["title"][:52]))
    if need:
        print()
        print("[注意] 第 %s 条标了 _needs_human，05 默认会拒绝出看板。" % "、".join(map(str, need)))
        print("       改完 hot_draft.json 把那两条的 _needs_human 去掉（或置 false）即可。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
