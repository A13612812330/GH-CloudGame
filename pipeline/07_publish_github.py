# -*- coding: utf-8 -*-
# ============================================================================
# 端游周报流水线 · 步骤 07：GitHub Pages 归档发布
# 运行：python 07_publish_github.py [发布目录]
#        发布目录默认 <out_dir>/_gh_publish
# ----------------------------------------------------------------------------
# 作用：
#   1) 扫描发布目录下的 <YYYY-MM-DD> 日期子目录，收集交付物
#   2) 生成根 index.html（浅色优雅风归档索引，最新一期置顶高亮）
#   3) 生成 README.md（仓库说明 + 各期索引表）
#   4) 保证 .nojekyll 存在（否则 GitHub Pages 会跑 Jekyll，忽略 _ 开头文件）
#   5) 生成**稳定短链**：每期 <date>/index.html + 根 latest/index.html
#      ⇒ <BASE>/<date>/  与  <BASE>/latest/  都能直接打开
#
# 约定：
#   - 归档以「日期目录」为单位，目录名 = YYYY-MM-DD（产出日）
#   - <date>/index.html = 该期看板副本（稳定短链入口，派生产物，不计入交付文件数）
#   - latest/index.html = 最新一期看板副本（永远指向最新）
#   - 元数据表 META 按日期写死「期次/说明」，新增一期需在此补一行
# ============================================================================
import os
import re
import sys
import shutil
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cfg import CFG  # noqa: E402  统一配置（路径只从 config.json 来）

PUB = sys.argv[1] if len(sys.argv) > 1 else str(CFG.out_dir / "_gh_publish")

# ---- 各期元数据（新增一期在此追加一行）--------------------------------------
META = {
    "2026-08-25": {
        "tag": "数据基础",
        "title": "7.1 – 8.24 关键词清洗与三源汇总",
        "desc": "端游关键词三级匹配清洗、鲸云平台表现、Steam 近一年 60 款、三源关联重点表 v4",
        "report": False,
    },
    "2026-08-26": {
        "tag": "可视化",
        "title": "三源联动看板 v2 增强版",
        "desc": "首次产出可视化看板，并导出 4 张源表 CSV + 全量 JSON",
        "report": False,
    },
    "2026-08-31": {
        "tag": "周报",
        "title": "8.17 – 8.30 首期周报",
        "desc": "搜索源 + 鲸云下载源 + Steam 源 + 三源关联重点表，附可视化看板",
        "report": True,
    },
    "2026-09-14": {
        "tag": "周报 · 大报告",
        "title": "8.31 – 9.13 大报告",
        "desc": "133 款端游 / 162.5 万次搜索、409 款鲸云下载、58 款 Steam，联网采集热点与总结",
        "report": True,
    },
    "2026-10-12": {
        "tag": "周报 · 大报告",
        "title": "9.28 – 10.11 大报告（跨期对比 · 国庆档）",
        "desc": "国庆档跨期对比：端游搜索 300.38 万次（+72.9%）、鲸云下载 104,846（+46.0%）。"
                "重点提示：《OVERPEAK》跃居搜索第 2 但实为国际服手游，端手游数据混流；"
                "热点固定 12 条（末两条为版号重点、端游转手游独立游戏候选）",
        "report": True,
    },
    "2026-09-28": {
        "tag": "周报 · 大报告",
        "title": "9.14 – 9.27 大报告（跨期对比）",
        "desc": "跨期对比本期 vs 上期 8.31-9.13；热点固定 12 条（末两条为版号重点、端游转手游独立游戏候选）、"
                "Steam 真实主视觉、品类环形图、三源重点表一屏可览；"
                "端游搜索 164.96 万次（+1.5%，占全站 18.6%）、鲸云下载 71,795 次（-11.5%）、Steam 58 款",
        "report": True,
    },
}


def q(p: str) -> str:
    """按路径分段做 URL 编码，保留 /"""
    return "/".join(quote(seg) for seg in p.split("/"))


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def human_size(n: int) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024.0


# ---- 1) 扫描 -----------------------------------------------------------------
if not os.path.isdir(PUB):
    sys.exit(f"[ERR] 发布目录不存在：{PUB}")

dates = sorted([d for d in os.listdir(PUB)
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) and os.path.isdir(os.path.join(PUB, d))],
               reverse=True)
if not dates:
    sys.exit("[ERR] 未找到 <YYYY-MM-DD> 日期目录")

periods = {}
for d in dates:
    files = []
    for root, _dirs, fs in os.walk(os.path.join(PUB, d)):
        for f in sorted(fs):
            if f == "index.html":
                continue          # 派生的短链入口副本，不是交付物，不计入文件数
            full = os.path.join(root, f)
            rel = os.path.relpath(full, PUB).replace("\\", "/")
            files.append({"rel": rel, "name": f, "size": os.path.getsize(full)})
    files.sort(key=lambda x: x["rel"])
    periods[d] = files

LATEST = dates[0]
print(f"扫描到 {len(dates)} 期：{', '.join(dates)}")
print(f"最新一期：{LATEST}（{len(periods[LATEST])} 个文件）")

# ---- 2) .nojekyll ------------------------------------------------------------
open(os.path.join(PUB, ".nojekyll"), "w").close()

# ---- 3) 稳定短链：每期 <date>/index.html + 根 latest/ ------------------------
#   目标（用户要求「推送到 GitHub 时也附带能直接打开的稳定短链」）：
#     <BASE>/<date>/    —— 该期看板副本 ⇒ 历史任意一期都可直开、可长期分享
#     <BASE>/latest/    —— 最新一期副本 ⇒ 永远指向最新，不随期次变化
#   短链之所以「稳定」：用目录式 URL，不暴露中文文件名与 URL 编码，
#   后续重跑只覆盖 index.html 内容，链接本身永远不变。
#   ⚠️ 这些 index.html 是派生副本，扫描阶段已排除，不计入交付物文件数。
BASE = (CFG._raw.get("pages_base") or "").rstrip("/")
period_board = {}                 # date -> 该期看板相对路径（None = 该期无可直开看板）
for d in dates:
    b = next((f for f in periods[d]
              if f["name"].lower().endswith(".html") and "看板" in f["name"]), None)
    period_board[d] = b["rel"] if b else None
    if b:
        shutil.copyfile(os.path.join(PUB, b["rel"]), os.path.join(PUB, d, "index.html"))
n_short = sum(1 for v in period_board.values() if v)
print(f"期次短链：{n_short} 个 → {BASE}/<date>/")

if period_board[LATEST]:
    os.makedirs(os.path.join(PUB, "latest"), exist_ok=True)
    shutil.copyfile(os.path.join(PUB, period_board[LATEST]),
                    os.path.join(PUB, "latest", "index.html"))
    print(f"latest → {period_board[LATEST]}")

# ---- 4) index.html -----------------------------------------------------------
cards = ""
for i, d in enumerate(dates):
    m = META.get(d, {"tag": "归档", "title": d, "desc": "", "report": False})
    is_latest = (i == 0)
    rows = ""
    for f in periods[d]:
        if f["name"].lower().endswith(".html"):
            icon, badge = "📊", "在线查看"
        elif f["name"].lower().endswith(".xlsx"):
            icon, badge = "📗", "Excel"
        elif f["name"].lower().endswith(".csv"):
            icon, badge = "📄", "CSV"
        else:
            icon, badge = "🗂", "数据"
        rows += (
            f'<a class="frow" href="{q(f["rel"])}" target="_blank" rel="noopener">'
            f'<span class="fi">{icon}</span>'
            f'<span class="fn">{esc(f["name"])}</span>'
            f'<span class="fb">{badge}</span>'
            f'<span class="fs">{human_size(f["size"])}</span></a>'
        )
    latest_btn = (f'<a class="cta" href="latest/" target="_blank" rel="noopener">打开最新看板 →</a>'
                  if (is_latest and m.get("report")) else "")
    shortline = (f'<div class="short">🔗 稳定短链（直接打开）'
                 f'<a href="{d}/" target="_blank" rel="noopener">{BASE}/{d}/</a></div>'
                 if period_board.get(d) else
                 '<div class="short">🗂 本期无看板（仅数据文件）</div>')
    cards += f'''
  <section class="card{' hot' if is_latest else ''}">
    <div class="chead">
      <div class="cleft">
        <span class="date">{d}</span>
        <span class="tag">{esc(m['tag'])}</span>
        {('<span class="badge-new">最新</span>' if is_latest else '')}
      </div>
      <div class="cright">{len(periods[d])} 个文件{latest_btn}</div>
    </div>
    <h3>{esc(m['title'])}</h3>
    <p class="desc">{esc(m['desc'])}</p>
    {shortline}
    <div class="files">{rows}</div>
  </section>'''

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>端游三源周报 · 归档</title>
<style>
:root{{--bg:#f4f6fb;--card:#fff;--ink:#1a2233;--dim:#5b6883;--line:#e3e8f2;
  --blue:#1e4ed8;--blue2:#4b7bff;--gold:#b7791f;--up:#d93838;--down:#1f9254}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.6 "Microsoft YaHei","PingFang SC","Hiragino Sans GB",system-ui,sans-serif}}
.wrap{{max-width:1060px;margin:0 auto;padding:28px 20px 60px}}
.hero{{background:linear-gradient(135deg,#1e4ed8,#4b7bff 55%,#6fa0ff);color:#fff;
  border-radius:16px;padding:30px 32px;box-shadow:0 10px 30px rgba(30,78,216,.22)}}
.hero h1{{margin:0 0 8px;font-size:26px;letter-spacing:.5px}}
.hero p{{margin:0;opacity:.92;font-size:13.5px}}
.chips{{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px}}
.hero-links{{margin-top:14px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:12px}}
.hero-links a{{font-family:Consolas,Menlo,monospace;font-size:11.5px;color:#fff;
  background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.38);
  border-radius:6px;padding:3px 10px;text-decoration:none;word-break:break-all}}
.hero-links a:hover{{background:rgba(255,255,255,.28)}}
.hero-links .hlt{{opacity:.82}}
.chip{{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.32);
  border-radius:999px;padding:3px 12px;font-size:12px}}
.sec-h{{margin:26px 4px 12px;font-size:14px;color:var(--dim);font-weight:700;letter-spacing:.6px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;
  padding:18px 20px;margin-bottom:14px;box-shadow:0 2px 10px rgba(26,34,51,.05)}}
.card.hot{{border-color:#bcd0ff;box-shadow:0 6px 22px rgba(30,78,216,.14)}}
.chead{{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}}
.cleft{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.date{{font-family:Consolas,Menlo,monospace;font-size:15px;font-weight:700;color:var(--blue)}}
.tag{{background:#eef3ff;color:#2b56c7;border-radius:6px;padding:2px 9px;font-size:12px}}
.badge-new{{background:linear-gradient(135deg,#d93838,#e8695f);color:#fff;border-radius:6px;
  padding:2px 9px;font-size:12px;font-weight:700}}
.cright{{display:flex;align-items:center;gap:12px;font-size:12px;color:var(--dim)}}
.cta{{background:var(--blue);color:#fff;text-decoration:none;border-radius:8px;
  padding:6px 14px;font-size:12.5px;font-weight:700;white-space:nowrap}}
.cta:hover{{background:#1740b8}}
.card h3{{margin:12px 0 4px;font-size:16px}}
.desc{{margin:0 0 12px;color:var(--dim);font-size:13px}}
.short{{margin:0 0 12px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;
  font-size:12px;color:var(--dim)}}
.short a{{font-family:Consolas,Menlo,monospace;font-size:11.5px;color:var(--blue);
  background:#eef3ff;border:1px solid #d5e0ff;border-radius:6px;padding:3px 9px;
  text-decoration:none;word-break:break-all}}
.short a:hover{{background:#e2ebff;border-color:#b9ccff}}
.files{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:6px;
  border-top:1px dashed var(--line);padding-top:12px}}
.frow{{display:flex;align-items:center;gap:9px;padding:7px 10px;border-radius:8px;
  text-decoration:none;color:var(--ink);border:1px solid transparent}}
.frow:hover{{background:#f0f4ff;border-color:#d5e0ff}}
.fi{{flex:0 0 auto}}
.fn{{flex:1 1 auto;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}}
.fb{{background:#f1f4fa;color:var(--dim);border-radius:5px;padding:1px 7px;font-size:11px;flex:0 0 auto}}
.fs{{color:#95a1b8;font-size:11.5px;flex:0 0 auto;min-width:52px;text-align:right;
  font-family:Consolas,Menlo,monospace}}
.foot{{margin-top:26px;text-align:center;color:#95a1b8;font-size:12px;line-height:1.9}}
.foot code{{background:#e9eefb;border-radius:4px;padding:1px 6px;color:#2b56c7}}
@media(max-width:640px){{.hero{{padding:22px}} .hero h1{{font-size:21px}}}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <h1>端游三源周报 · 归档</h1>
    <p>搜索（神策）× 云游戏下载（鲸云）× SteamDB 三源交叉验证 · 按产出日期归档</p>
    <div class="chips">
      <span class="chip">共 {len(dates)} 期</span>
      <span class="chip">最新 {LATEST}</span>
      <span class="chip">总 {sum(len(v) for v in periods.values())} 个交付文件</span>
    </div>
    <div class="hero-links">
      <span>稳定短链</span>
      <a href="latest/" target="_blank" rel="noopener">{BASE}/latest/</a>
      <span class="hlt">永远指向最新一期 · 历史各期短链见下方卡片</span>
    </div>
  </div>

  <div class="sec-h">各期归档（最新在前）</div>
{cards}

  <div class="foot">
    期次口径：跨期对比（本期两周 vs 上期两周）· 涨红跌绿（A 股习惯）· 看板热点固定 12 条<br>
    最新一期稳定短链：<code>latest/</code> · 本页由 <code>07_publish_github.py</code> 自动生成
  </div>
</div>
</body>
</html>
'''
with open(os.path.join(PUB, "index.html"), "w", encoding="utf-8") as fp:
    fp.write(html)
print("index.html 已生成")

# ---- 5) README.md ------------------------------------------------------------
rl = ["# 端游三源周报归档",
      "",
      "搜索（神策）× 云游戏下载（鲸云）× SteamDB 三源交叉验证的端游市场周报，按产出日期归档。",
      "",
      "## 🔗 稳定短链（直接打开）",
      "",
      f"- **最新一期（永远指向最新）**：{BASE}/latest/",
      f"- **任意一期**：`{BASE}/<日期>/` —— 如 {BASE}/{LATEST}/",
      "- 短链用目录式 URL，不暴露中文文件名与 URL 编码；重发只覆盖内容，链接本身不变",
      "",
      f"> 在线归档页：**{BASE}/**",
      "",
      "## 各期索引",
      "",
      "| 日期 | 期次 | 本期要点 | 稳定短链 | 文件数 |",
      "|---|---|---|---|---|"]
for d in dates:
    m = META.get(d, {"tag": "归档", "title": d, "desc": ""})
    note = (m.get("desc") or m["title"]).replace("|", "/")
    if len(note) > 78:                       # 索引表里只放要点摘要，全文在归档页卡片上
        note = note[:78] + "…"
    short = f"[`/{d}/`]({BASE}/{d}/)" if period_board.get(d) else "—"
    rl.append(f"| [{d}]({q(d)}/) | {m['tag']} | {note} | {short} | {len(periods[d])} |")
rl += ["", "## 目录约定", "",
       "- 以 `YYYY-MM-DD/`（产出日期）分目录，目录内保留原始交付文件名",
       "- `<YYYY-MM-DD>/index.html` = 该期看板的**稳定短链入口**（派生副本，随发布自动生成）",
       "- `latest/index.html` = 最新一期副本，用于对外分享的稳定短链",
       "- `.nojekyll` 关闭 Jekyll 处理，保证中文与特殊字符文件名正常访问",
       "", "## 数据口径", "",
       "- **搜索源**：神策搜索事件，端游词库三级匹配（精确 / 前缀扩展 ≤6 字 / 词根中断 ≥3 字），最长匹配优先",
       "- **鲸云源**：云游戏平台下载量（注：注册数据源已停用，不在归档范围内）",
       "- **Steam 源**：SteamDB 在线榜 + 近一年新游，排除网游与工具类",
       "- **环比口径**：**跨期对比（本期两周 vs 上期两周）**，非期内 W1/W2；涨红跌绿（A 股习惯）",
       "- **看板热点**：固定 12 条，末两条为「📜 版号重点」与「🎮 端游转手游独立游戏候选」",
       ""]
with open(os.path.join(PUB, "README.md"), "w", encoding="utf-8") as fp:
    fp.write("\n".join(rl))
print("README.md 已生成")
print(f"\n完成。发布目录：{PUB}")
