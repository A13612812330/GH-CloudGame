# AGENT.md — 给 AI Agent 的执行契约

> 你被要求用这个仓库复刻「端游云游戏三源周报」。
> 本文件是**唯一权威执行说明**。开始动手前请完整读完，尤其是第 4 节的「必须你自己做」清单。
> 人类读者请先看 [README.md](README.md)。

---

## 0. 一句话说明这个仓库在做什么

把两份平台导出表变成一份能直接看的周报：

```
搜索表（神策导出）+ 下载表（鲸云导出）
        ↓  关键词清洗 + 跨期对比
    端游维度数据
        ↓  + SteamDB 在线榜
   三源交叉验证
        ↓
  Excel 五表 + 单文件 HTML 看板
```

**核心产出**：`outputs/<日期>/` 下的 看板 HTML + 大报告 Excel。

---

## 1. 仓库地图

| 路径 | 作用 | 你什么时候会用到 |
|---|---|---|
| `pipeline/_cfg.py` | 统一配置层。**所有路径只从这里来** | 不要改，除非要加新配置项 |
| `pipeline/setup.py` | 配置向导（GUI 选文件夹 / 命令行传参） | 第一步就跑它 |
| `pipeline/09_run_all.py` | **一键跑全流程**（含环境自检 / 断点续跑 / 门禁） | 配好之后就用它，别手敲单步 |
| `pipeline/00_probe_inputs.py` | 探查 xlsx 的 sheet 与列结构 | 拿到格式陌生的新表时先跑 |
| `pipeline/01_prep_search_dl.py` | 搜索与下载清洗、跨期 join | 每次必跑 |
| `pipeline/02_extract_steam_meta.py` | 汇总 Steam 元数据（appid→名称/标签/大小/峰值） | 每次必跑 |
| `pipeline/03_build_steam_chart.py` | **SteamDB Top100 快照** + 筛非网游 | ⚠️ 跑新一期必须改 `CHART` |
| `pipeline/04_build_report.py` | 出五表 Excel + `data.json` | ⚠️ 判定文案要你写 |
| `pipeline/04b_make_covers.py` | 抓 Steam 真实封面 → `covers.json` | 每次必跑（联网）；带 `--plan` 时按热点初稿抓 |
| `pipeline/10_draft_hotspots.py` | **热点半自动初稿**（12 条 + 封面计划 + 校对清单） | 见 4.3，别从零手写 |
| `pipeline/05_gen_board.py` | 生成 HTML 看板 | ✅ 带 `--hot` 用初稿；不带则用脚本内手写热点 |
| `pipeline/06_test_board.js` | jsdom 渲染回归（55 项断言） | 每次必跑 |
| `pipeline/08_preflight_check.py` | **交付前体检门禁** | ⚠️ 必须 PASS 才能交 |
| `pipeline/07_publish_github.py` | 归档到 GitHub Pages（可选） | 需要归档时 |
| `assets/endgame_lib.json` | 端游词库（195 条：游戏名→别名 + 排除词） | 发现漏词/误挂时改 |
| `assets/steam_meta_seed.json` | Steam 元数据种子（90 条） | 首次运行自动加载 |
| `samples/` | 两期真实样例数据（可直接跑通） | 验证环境 |
| `outputs/` | 4 期历史产出（看板 + Excel） | 对齐预期效果 / 参考文案风格 |
| `docs/` | 口径、格式、看板规范、坑位 | 遇到问题时查 |

---

## 2. 环境

```bash
python -c "import pandas, openpyxl, PIL"   # 缺哪个装哪个
pip install -r requirements.txt

node -e "require('jsdom')"                  # 06 依赖；没有就 npm i jsdom
```

Python 3.10+ / Node 18+。Windows 上注意：**不要用 `TMP` 作环境变量名**，它是系统保留变量。

---

## 3. 最短路径：先跑通样例

```bash
cd pipeline

# 3.1 配置（把 samples 当数据源，输出到 outputs/_local）
python setup.py --data-dir ../samples --out-dir ../outputs/_local \
                --cur 9.28-10.11 --prev 9.14-9.27 --run-date 2026-10-12

# 3.2 一条命令跑完 00 → 08（环境自检 → 逐步执行 → 06 回归 → 08 门禁）
python 09_run_all.py
```

**首选 `09_run_all.py`**，不要手敲单步：它保证顺序正确（04b 依赖 04 的 `data.json`，
05 依赖 04b 的 `covers.json`），任何一步失败立即中止并在最后提示断点续跑命令。
要单步调试时才逐个跑：

```bash
python 00_probe_inputs.py       # ① 输入结构
python 01_prep_search_dl.py     # ② 清洗 + 跨期
python 02_extract_steam_meta.py # ③ Steam 元数据
python 03_build_steam_chart.py  # ④ SteamDB 快照合并
python 04_build_report.py       # ⑤ Excel + data.json
python 04b_make_covers.py       # ⑥ 封面（联网，可能较慢）
python 05_gen_board.py          # ⑦ 看板
node 06_test_board.js           # ⑧ 回归（应「🎉 全部通过」）
python 08_preflight_check.py    # ⑨ 门禁（应 PASS）
```

产出在 `outputs/_local/`。

> **判定标准**：`09_run_all.py` 退出码 `0` 且末尾出现 `门禁已通过（08 PASS）`。
> 退出码 `1` = 某步失败或门禁拦截，**此时产物一律不许交付**。

> **第一次跑 04/05 时，产出的判定与热点是 2026-10-12 那期的文案**（脚本里固化的）。
> 这在「跑样例」场景是对的（就是复刻那一期），但**跑新一期绝不能这样** —— 见第 4 节。

---

## 4. ⚠️ 必须你自己做的事（复刻的真正难点）

流水线能自动算数，但**判断和叙述必须重写**。以下三项是硬要求（其中 4.3 已有半自动工具，
但「版号」与「归因」仍只能人来）：

### 4.1 `03_build_steam_chart.py` 的 `CHART` 数组

文件里是一个 **SteamDB Top100 快照**（含 rank / 名称 / appid / 当前在线 / 24h 峰值 / 历史峰值）。
跑新一期必须换成**当期快照**：

1. 访问 `https://steamdb.info/charts/` 取当前在线前 100
2. 按 `(rank, "游戏名", appid, 当前在线, 24h峰值, 历史峰值)` 改写 `CHART`
3. 同步改文件顶部 docstring 的日期

否则你会拿旧在线数配新搜索数，三源共振判断全错。

### 4.2 `04_build_report.py` 的 `PATCH` 与 `verdict`

- **`PATCH`**：新进榜但历史元数据缺失的游戏，人工补 appid→中文名/开发者/标签/大小/独立/峰值（可从 SteamDB 单页抓）。
- **`verdict`**：`s4` 重点表每行的「判定/说明」。必须基于**本期实际数字**写，不得引用上一期大盘值。

> ⛔ **这个文件踩过坑**：曾有两条 `if/elif label == ...` 链并存，旧链在新链之后执行，把 9 款游戏的判定**静默覆盖成旧文案**。
> 改完必须 `grep -n 'label == "<某款游戏>"' 04_build_report.py`，**命中数必须是 1**。

### 4.3 `05_gen_board.py` 的热点 12 条与 `SUMMARY`

**别从零手写 —— 先跑 `10_draft_hotspots.py`。**（4.3 是本仓库唯一有半自动工具的一项）

```bash
python 09_run_all.py --draft-hot --from 04     # 04 之后生成热点初稿
python 09_run_all.py --from 04b                # 人改完后出看板（自动带 --plan / --hot）
```

`10_draft_hotspots.py` 会从 `data.json` 按规则挑料并套模板句，产出三个文件：

| 文件 | 用途 |
|---|---|
| `hot_draft.json` | 12 条热点初稿；`05 --hot` 读取 |
| `covers_plan.json` | 配套封面计划（键名由 appid 派生）；`04b --plan` 读取 |
| `hot_review.md` | 人工校对清单，按「必改 / 建议润色 / 可用」分级 |

它固定的 12 个槽位：

| # | 槽位 | 是否自动 |
|---|---|---|
| 1 | 📈 大盘总览 | ✅ 纯数据 |
| 2 | 🚀 搜索涨幅冠军 | ✅（已过滤小基数噪音） |
| 3 | 📥 下载涨幅冠军 | ✅ |
| 4 | 🏆 搜索榜首 | ✅ |
| 5 | 🎮 Steam 在线王 | ✅ |
| 6 | 🔗 三源共振 | ✅ |
| 7 | 🆕 新游观察 | ✅（本期→近一月→近一年，逐级退让） |
| 8 | 📉 退潮预警 | ✅（带基数下限） |
| 9 | ⚠️ 跨端外溢 / 📊 品类结构 | ✅（搜索暴涨但 Steam 查无此游 → 直接标警示） |
| 10 | 🎯 独立游戏王 | ✅ |
| 11 | 📜 版号重点 | ❌ **必须人工**（外部公告，脚本拿不到） |
| 12 | 🎮 移植候选 | ✅（按触屏/体积/人气打分挑 4 款） |

**仍然必须人来做的两件事**：

1. **第 11 条版号** —— 查国家新闻出版署当期公告。初稿里它带 `_needs_human: true`，
   此时 `05` 会**直接拒绝出看板**（退出码 3）。
2. **归因** —— 模板句只陈述数字（「涨了多少」），不解释「为什么涨」。
   每条初稿的 `_hint` 字段写了该补什么，`hot_review.md` 也列成了待办表。

改完把 `_needs_human` 去掉（或置 `false`）即可。只想先预览版式可加 `--allow-draft`，
但会在 `<body>` 上打 `data-draft="N"`，**08 门禁据此一律拒收**。

`SUMMARY` 仍是手写（页面底部六段总结），无初稿工具。

> 12 条里的**第 11 条版号、第 12 条移植候选是固定栏目**：版号 `cover: "license"`（程序化信息图），
> 移植候选 `cover4: [4 个 key]`（2×2 拼贴）。这两条的槽位不能挪、不能省。

> 热点与总结最容易「沿用上一期」。**08 门禁用数字指纹检测**：热点里一个本期数字都没命中、
> 却命中了上期总量 → 直接 BLOCK。

---

## 5. 硬性红线（违反即返工）

| # | 红线 | 原因 |
|---|---|---|
| 1 | **对比口径 = 本期两周 vs 上期两周**，不是期内 W1 vs W2 | 做错过一次，得出 +39.9% 的假环比（真值 +1.5%） |
| 2 | **两期粒度必须先自证** | 下载源有时给 14 天逐日、有时给 2 列周汇总。判据：共有游戏「本期总天数 ÷ 上期总天数」比值中位数应 ≈ 1，显著偏离就找用户核对 |
| 3 | **不读「云游戏注册」文件** | 该数据源已停用 |
| 4 | **看板样式必须是浅色优雅风** | 用户明确否决过深色霓虹风。模板已固化在 `05_gen_board.py`，不要换风格 |
| 5 | **热点固定 12 条** | 3 列网格正好 4 行 |
| 6 | **端手游混流必须核实** | 神策搜索源不分端手游。搜索异常脉冲先查包名/安装包体积/渠道站，再判断是不是端游 |
| 7 | **08 必须 PASS** | 它是最后一道闸 |

---

## 6. 数据口径要点

- **期次目录**约定：`<data_dir>/<期标签>/`，如 `9.28-10.11/`。
- **文件名不固定**：`鲸云下载.xlsx` / `云游戏下载.xlsx` 都出现过；搜索表可能叫 `搜索9.14-9.27.xlsx` 或 `搜索量9.28-10.11.xlsx`。`_cfg.py` 会按关键词自动探测，也可在 config 里写死。
- **搜索源**：两期各含 2 个日期列（两个周一），**每列代表一周**，两列相加 = 两周。
- **下载源**：粒度不固定，必须先看 `明细数据` sheet 的日期个数。
- **词库三级匹配**：精确 → 前缀扩展（差 ≤6 字） → 词根中断（≥3 字）。
  - 双字泛词（"恐怖"、"我的"、"植物"、"超人"）必须放 `exclude`，否则会吃掉大量无关流量。
  - 但 `exclude` 是**全局**的：词库里加了某词、`exclude` 里也有，它就永远不命中（`甜瓜游乐场` 就是这种情况）。

详见 [docs/02-数据口径.md](docs/02-数据口径.md)。

---

## 7. 跑新一期的完整流程

```bash
cd pipeline
python setup.py --data-dir <你的数据根目录> --out-dir <产出目录> \
                --cur <本期目录名> --prev <上期目录名> --run-date <YYYY-MM-DD>

# ① 先跑前半程，确认新表结构没变、数字能对上
python 09_run_all.py --until 04        # 00→04；若 01 报错先看 docs/03

# ② 生成热点初稿（05a），此时 05 会拒绝出看板，直到人改完
python 09_run_all.py --draft-hot --from 04
#    然后看 <中间产物>/hot_review.md，改 hot_draft.json：
#    补齐第 11 条版号、给第 2~10 条补归因、去掉 _needs_human

# ③ 手动改另外两处（见 4.1 / 4.2）：03 的 CHART、04 的 PATCH/verdict

# ④ 跑完全程 + 门禁（自动带 --plan 与 --hot）
python 09_run_all.py --from 04b
```

`SUMMARY`（底部六段总结）没有初稿工具，在 `05_gen_board.py` 里手写。

如果中途失败，用 `--from <步骤号>` 断点续跑，不要从头重跑（04b 抓封面较慢）。

**顺序不可乱**：04b 依赖 04 的 `data.json`，05 依赖 04b 的 `covers.json` —— `09_run_all.py`
已把这层依赖写死在步骤表里，所以**不要自己重排**。

---

## 8. 失败处置

| 现象 | 原因 | 处置 |
|---|---|---|
| `[输入缺失] 找不到搜索表` | 目录/文件名不匹配 | 跑 `python setup.py --check` 看它找到了什么 |
| 01 报「两期粒度不等效」 | 两期导出方式不同 | **不要硬比**，先问人确认导出方式 |
| 03 输出「历史元数据缺失 N 款」 | 新游戏不在种子库 | 在 04 的 `PATCH` 里补 |
| 04b 大量 `generated` 而非 `real-og` | Steam 网络瞬时失败 | `fetch_url` 已内置 5 次退避重试，重跑一次通常就好 |
| 06 报 `ENOENT ... Temp\data.json` | 用了 `TMP` 变量名 | 改用 `GH_TMP` |
| 08 报「热点疑似沿用上期」 | `HOT` 没重写 | 按第 4.3 节重写 |
| 08 报「看板比 data.json 旧」 | 改了 04 没重跑 05 | 重跑 05 |

---

## 9. 交付前自检清单

- [ ] `08_preflight_check.py` 输出 `PASS`（0 ERROR）
- [ ] `06_test_board.js` 输出「🎉 全部通过」
- [ ] 看板里的数字与 Excel 五表一致
- [ ] `HOT` 12 条、第 11 条版号、第 12 条移植候选
- [ ] 判定文案里没有上一期的大盘值
- [ ] 若含假期/大促，总结里明确写了「需剔除假期效应」
