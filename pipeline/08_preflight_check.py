# -*- coding: utf-8 -*-
# ============================================================================
# 端游周报流水线 · 步骤 08：交付前体检（拦住「数据是新的、文案是旧的」）
# 用法：python 08_preflight_check.py [--strict]
# ----------------------------------------------------------------------------
# 为什么需要它：
#   04 的判定文案（verdict）、05 的热点（HOT）与总结（SUMMARY）都是**每期人工撰写**。
#   AI 复刻时最容易犯的错不是跑不出数据，而是**沿用上一期的文案** ——
#   数据全对、结论全错，而且肉眼很难发现（2026-10-12 就发生过旧 verdict 链
#   静默覆盖 9 款游戏判定的事故）。
#
# 本脚本检查两类事：
#   A/B  期次与产物是否对得上（配置、data.json、看板三方一致）
#   C/D  文案是否真的属于本期（热点条数与固定栏目、大盘数值是否与 KPI 吻合、占位符）
#
# 严重级别：
#   ERROR → 退出码 1，禁止发布
#   WARN  → 退出码 0，但必须人工确认；--strict 下升级为 ERROR
# ============================================================================
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cfg import CFG  # noqa: E402

STRICT = "--strict" in sys.argv

rows: list[tuple[str, str, str]] = []   # (level, name, detail)
ERRORS = WARNINGS = 0


def ok(name, detail=""):
    rows.append(("✅", name, detail))


def warn(name, detail=""):
    global WARNINGS
    WARNINGS += 1
    rows.append(("⚠️", name, detail))


def err(name, detail=""):
    global ERRORS
    ERRORS += 1
    rows.append(("❌", name, detail))


def section(title):
    rows.append(("", "─" * 4 + " " + title + " " + "─" * 4, ""))


# ---------------------------------------------------------------- 读产物
data_path = CFG.tmp / "data.json"
# 可用 GH_BOARD 指定待检看板（默认按 config 推导）；GH_TMP 可指定中间产物目录
board_path = Path(os.environ["GH_BOARD"]) if os.environ.get("GH_BOARD") else CFG.board_out()
xlsx_path = CFG.report_out()

data = None
if data_path.is_file():
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except Exception as e:
        err("data.json 可解析", str(e))

board = board_path.read_text(encoding="utf-8") if board_path.is_file() else ""


def js_literal(text: str, name: str):
    """从 HTML 里取 `const NAME = [...]` 的 JSON 值（带字符串状态机的括号配对）。"""
    m = re.search(r"const\s+%s\s*=\s*" % re.escape(name), text)
    if not m:
        return None
    i = text.find("[", m.end())
    if i < 0:
        return None
    depth, j, in_str, quote, esc = 0, i, False, "", False
    while j < len(text):
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == quote:
                in_str = False
        else:
            if c in "\"'":
                in_str, quote = True, c
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[i:j + 1])
                    except Exception:
                        return None
        j += 1
    return None


HOT = js_literal(board, "HOT") if board else None
SUM = js_literal(board, "SUM") if board else None

# ---------------------------------------------------------------- A 期次
section("A. 配置与数据期次")

cur_lab, prev_lab = None, None
try:
    cur_lab, prev_lab = CFG.label("cur"), CFG.label("prev")
except SystemExit as e:
    err("期次配置", str(e).replace("\n", " "))

if data:
    meta = data.get("meta") or {}
    if meta.get("cur") == cur_lab:
        ok("data.json 本期标签", meta.get("cur"))
    else:
        err("data.json 本期标签", "文件=%r 期望=%r（data.json 可能是上一期残留）"
            % (meta.get("cur"), cur_lab))

    if meta.get("prev") == prev_lab:
        ok("data.json 上期标签", meta.get("prev"))
    else:
        err("data.json 上期标签", "文件=%r 期望=%r" % (meta.get("prev"), prev_lab))

    snap, want = meta.get("snapshot"), CFG.run_date
    if not want:
        warn("出报告日期未设置", "config.run_date 为空，快照日期未校验")
    elif snap == want:
        ok("data.json 快照日期", snap)
    else:
        err("data.json 快照日期", "文件=%r 期望=%r" % (snap, want))

# ---------------------------------------------------------------- B 产物
section("B. 产物存在与新鲜度")

if data:
    ok("data.json", str(data_path))
else:
    err("data.json 缺失", str(data_path) + " —— 先跑 01→04")

if board:
    ok("看板 HTML", "%s（%.0f KB）" % (board_path.name, len(board) / 1024))
else:
    err("看板缺失", str(board_path) + " —— 先跑 05")

if data and board:
    if board_path.stat().st_mtime >= data_path.stat().st_mtime - 1:
        ok("看板晚于 data.json", "顺序正确（04 → 05）")
    else:
        err("看板比 data.json 旧", "看板可能是上一次生成的，需重跑 05")

if xlsx_path.is_file():
    ok("Excel 大报告", "%s（%.0f KB）" % (xlsx_path.name, xlsx_path.stat().st_size / 1024))
else:
    err("Excel 缺失", str(xlsx_path))

if board:
    m = re.search(r'"cur"\s*:\s*"([^"]+)"', board)
    if not m:
        warn("看板内嵌期次未知", "未在 HTML 中找到 \"cur\" 字段")
    elif m.group(1) == cur_lab:
        ok("看板内嵌期次", m.group(1))
    else:
        err("看板内嵌期次不符", "HTML=%r 期望=%r（看板是旧文件）" % (m.group(1), cur_lab))

# ---------------------------------------------------------------- C 热点
kpi = (data or {}).get("kpi") or {}
s_chg = kpi.get("s_chg")
dl_chg = kpi.get("dl_chg")

section("C. 热点 12 条与固定栏目")

if HOT is None:
    err("热点数据可解析", "未在 HTML 中找到 const HOT = [...]")
else:
    if len(HOT) == 12:
        ok("热点条数", "12 条（3 列 × 4 行，不留空位）")
    else:
        err("热点条数", "实际 %d 条，必须固定 12 条" % len(HOT))

    if len(HOT) >= 11 and "版号" in (HOT[10].get("tag", "") + HOT[10].get("title", "")):
        ok("第 11 条 = 版号重点", HOT[10].get("title", "")[:30])
    else:
        err("第 11 条 = 版号重点", "标题未含「版号」，固定栏目缺失")

    if len(HOT) >= 12:
        h12 = HOT[11]
        has_both = "移植" in (h12.get("tag", "") + h12.get("title", ""))
        if has_both and h12.get("cover4"):
            ok("第 12 条 = 移植候选", "%s（cover4 × %d）" % (h12.get("title", "")[:24], len(h12["cover4"])))
        elif not has_both:
            err("第 12 条 = 移植候选", "标题未含「移植」，固定栏目缺失")
        else:
            err("第 12 条缺 cover4", "移植候选必须是 2×2 拼贴")

    naked = [h.get("title", "?")[:18] for h in HOT
             if not any(h.get(k) for k in ("cover", "cover4", "viz", "vizdata"))]
    if not naked:
        ok("每条热点都有主视觉", "%d 条全部具备 cover/cover4/viz" % len(HOT))
    else:
        err("热点缺主视觉", "；".join(naked))

    # 文案是否属于本期：用「数字指纹」判断，比看日期可靠 ——
    # 沿用上期文案时，里面必然是上期的总量与环比，一个都对不上本期 KPI。
    hot_text = " ".join(str(h.get(k, "")) for h in HOT for k in ("tag", "title", "desc", "src"))
    marks = []
    if kpi.get("search_total"):
        marks.append(("{:,}".format(int(kpi["search_total"])), "搜索总量"))
    if kpi.get("dl_total"):
        marks.append(("{:,}".format(int(kpi["dl_total"])), "下载总量"))
    if s_chg is not None:
        marks.append(("%+.1f%%" % s_chg, "搜索环比"))
    if dl_chg is not None:
        marks.append(("%+.1f%%" % dl_chg, "下载环比"))
    hit = [n for v, n in marks if v in hot_text]
    stale = []
    if kpi.get("search_total_prev"):
        stale.append("{:,}".format(int(kpi["search_total_prev"])))
    if kpi.get("dl_total_prev"):
        stale.append("{:,}".format(int(kpi["dl_total_prev"])))
    stale_hit = [v for v in stale if v in hot_text and v not in ("", "0")]

    if hit:
        ok("热点文案属于本期", "命中本期数字：%s" % "、".join(hit))
    elif stale_hit:
        err("热点文案疑似沿用上期",
            "只命中上期数值 %s，本期 %s 一个都没提 —— 请重写 HOT" % ("、".join(stale_hit), "、".join(v for v, _ in marks)))
    else:
        warn("热点文案无法验证期次", "既未命中本期也未命中上期数字，请人工确认本期热点已重写")

    # 辅助提示：本期日期是否出现在热点里（不是硬判据）
    tokens = [t for t in re.split(r"[-~至]", cur_lab or "") if t]
    if tokens and not any(t in hot_text for t in tokens):
        rows.append(("", "", "（提示：热点未写明本期日期 %s，建议至少一条带时点以便读者定位）" % cur_lab))

# ---------------------------------------------------------------- D 文案口径
section("D. 判定与总结的口径一致性")

if data and s_chg is not None:
    s4 = data.get("s4") or []
    bad = []
    for r in s4:
        txt = str(r.get("判定/说明", ""))
        for num in re.findall(r"大盘\s*([+-]?\d+(?:\.\d+)?)\s*%", txt):
            v = abs(float(num))
            near = [x for x in (s_chg, dl_chg) if x is not None and abs(abs(float(x)) - v) <= 0.15]
            if not near:
                bad.append("%s → 大盘 %s%%（本期实际 %+.1f%% / %+.1f%%）"
                           % (str(r.get("游戏", "?"))[:14], num, s_chg, dl_chg))
    if not bad:
        ok("重点表引用的大盘值", "全部与本期 KPI 吻合（%+.1f%% / %+.1f%%）" % (s_chg, dl_chg))
    else:
        warn("重点表可能有旧口径残留", "；".join(bad[:5]) +
             ("…共 %d 处" % len(bad) if len(bad) > 5 else ""))

    if SUM is not None:
        sum_text = json.dumps(SUM, ensure_ascii=False)
        found = [x for x in (s_chg, dl_chg)
                 if x is not None and ("%+.1f%%" % x in sum_text or "%.1f%%" % abs(x) in sum_text)]
        if found:
            ok("总结引用本期大盘值", "命中 %s" % "、".join("%+.1f%%" % x for x in found))
        else:
            warn("总结未引用本期大盘值",
                 "本期 %+.1f%% / %+.1f%% 均未出现 —— 疑似沿用上期总结" % (s_chg, dl_chg))

# 占位符（必须先剥掉内嵌 base64 —— 图片数据里随机出现 XXX 会造成误报）
if board:
    visible = re.sub(r"data:image/[a-zA-Z]+;base64,[A-Za-z0-9+/=]+", "", board)
    marks = [w for w in ("TODO", "FIXME", "待补", "待填", "PLACEHOLDER", "示例文案", "这里写")
             if w in visible]
    if not marks:
        ok("无占位符残留", "")
    else:
        err("发现占位符", "、".join(marks))

# ---------------------------------------------------------------- E 自洽
section("E. 表内合计自洽")

if data:
    s1, s2 = data.get("s1") or [], data.get("s2") or []
    try:
        s1_sum = sum(int(r.get("本期搜索") or 0) for r in s1)
        if kpi.get("search_hit") and abs(s1_sum - kpi["search_hit"]) <= max(2, kpi["search_hit"] * 0.001):
            ok("① 搜索表合计", "{:,} = KPI 命中 {}".format(s1_sum, kpi["search_hit"]))
        else:
            warn("① 搜索表合计", "{:,} vs KPI {}".format(s1_sum, kpi.get("search_hit")))
    except Exception:
        pass
    try:
        s2_sum = sum(int(r.get("本期下载") or 0) for r in s2)
        if kpi.get("dl_total") and abs(s2_sum - kpi["dl_total"]) <= max(2, kpi["dl_total"] * 0.001):
            ok("② 下载表合计", "{:,} = KPI 总量 {}".format(s2_sum, kpi["dl_total"]))
        else:
            warn("② 下载表合计", "{:,} vs KPI {}".format(s2_sum, kpi.get("dl_total")))
    except Exception:
        pass

# ---------------------------------------------------------------- 输出
print()
print("=" * 74)
print("端游三源周报 · 交付前体检     期次 %s（上期 %s）" % (cur_lab, prev_lab))
print("配置：%s" % (CFG.config_path or "未找到"))
print("=" * 74)
for mark, name, detail in rows:
    if not mark and name:
        print("\n" + name)
    elif mark:
        print("%s %-26s %s" % (mark, name, detail))

n_warn_eff = WARNINGS
verdict = "PASS"
if ERRORS:
    verdict = "BLOCK"
elif WARNINGS and STRICT:
    verdict = "BLOCK(strict)"
    n_warn_eff = 0

print("-" * 74)
print("ERROR %d · WARN %d → %s" % (ERRORS, WARNINGS, verdict))
if verdict == "PASS":
    print("✅ 可以进入发布环节")
elif verdict.startswith("BLOCK"):
    print("⛔ 禁止发布：先修正上面的 ❌（仅 WARN 时可加 --strict 复检）")
print()
sys.exit(1 if ERRORS or (WARNINGS and STRICT) else 0)
