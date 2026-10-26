# GH-CloudGame

端游云游戏「三源周报」的可复刻工程仓库 —— 脚本、词库、口径文档、AI Agent 执行契约、4 期历史产出，都在这里。

**给同事的一句话用法**：拿到自己的两份平台导出表 → 把这个仓库交给 AI Agent → 让它读 [`AGENT.md`](AGENT.md) → 跑出同款 Excel 五表 + HTML 看板。

---

## 三源是什么

| 源 | 来源 | 提供什么 |
|---|---|---|
| 搜索 | 神策（SensorsAnalytics）搜索事件导出 | 玩家在找什么、热度趋势 |
| 下载 | 鲸云平台云游戏下载报表 | 实际转化、真实需求 |
| Steam | SteamDB 在线榜 Top100 + 单页元数据 | 全球端游在线、配置要求、独立游戏标注 |

三源交叉后输出「三源关联重点表」：同时命中三源 = 真爆款；只有搜索 = 可能只是话题；只有下载 = 存量需求。

---

## 快速开始

```bash
pip install -r requirements.txt
npm i jsdom

cd pipeline
# 用仓库自带样例跑通（数据源 = ../samples，产出到 ../outputs/_local）
python setup.py --data-dir ../samples --out-dir ../outputs/_local \
                --cur 9.28-10.11 --prev 9.14-9.27 --run-date 2026-10-12
python 00_probe_inputs.py && python 01_prep_search_dl.py && python 02_extract_steam_meta.py
python 03_build_steam_chart.py && python 04_build_report.py
python 04b_make_covers.py && python 05_gen_board.py
node 06_test_board.js && python 08_preflight_check.py
```

不方便用命令行？`python setup.py` 会弹出文件夹选择框，点选数据目录即可。

> ⚠️ **跑新一期前必读** [`AGENT.md`](AGENT.md) 第 4 节：SteamDB 快照、判定文案、热点 12 条
> 这三样必须**现场重写**，脚本里固化的是 2026-10-12 那期的内容。

---

## 仓库结构

```
GH-CloudGame/
├── AGENT.md              ★ AI Agent 入口（执行契约 / 红线 / 必做清单）
├── README.md             本文件
├── config.example.json   路径配置模板（setup.py 会自动生成 config.json）
├── requirements.txt      Python 依赖
├── package.json          Node 依赖（jsdom）
├── pipeline/             流水线 00 → 08
├── assets/               端游词库 + Steam 元数据种子
├── samples/              两期真实样例数据（可直接跑通）
├── docs/                 口径 / 格式 / 看板规范 / 坑位清单
└── outputs/              4 期历史产出（看板 HTML + 大报告 Excel）
```

---

## 历史产出

| 期次 | 产出日 | 看板 | 大报告 Excel |
|---|---|---|---|
| 8.17 – 8.30 | 2026-08-31 | [看板](outputs/2026-08-31/端游三源周报看板_8.17-8.30.html) | [Excel](outputs/2026-08-31/端游三源周报_8.17-8.30.xlsx) |
| 8.31 – 9.13 | 2026-09-14 | [看板](outputs/2026-09-14/端游三源周报看板_8.31-9.13.html) | [Excel](outputs/2026-09-14/端游三源周报_大报告_2026-09-14.xlsx) |
| 9.14 – 9.27 | 2026-09-28 | [看板](outputs/2026-09-28/端游三源周报看板_9.14-9.27.html) | [Excel](outputs/2026-09-28/端游三源周报_大报告_2026-09-28.xlsx) |
| 9.28 – 10.11 | 2026-10-12 | [看板](outputs/2026-10-12/端游三源周报看板_9.28-10.11.html) | [Excel](outputs/2026-10-12/端游三源周报_大报告_2026-10-12.xlsx) |

看板为单文件 HTML（内嵌数据与封面图，零外部依赖），下载后双击即可打开。

> ⚠️ **GitHub 网页不会渲染 HTML**（点开会显示源码）。想看效果请先 `git clone` 到本地再双击，
> 或在仓库根执行 `python -m http.server 8000` 后访问 `localhost:8000/outputs/`。

---

## 关键口径（详细见 docs/02）

1. **对比的是「本期两周 vs 上期两周」**，不是本期内部 W1 vs W2。
2. **两期粒度必须先自证**：共有游戏「本期总天数 ÷ 上期总天数」比值中位数应 ≈ 1。偏离就说明两期导出方式不同，先问清楚再比。
3. **搜索源**每期含 2 个日期列（两个周一），每列 = 一周，两列相加 = 两周。
4. **下载源**粒度不固定（14 天逐日 / 2 列周汇总都出现过），必须每次探测。
5. **神策不区分端手游**：搜索异常脉冲先核实平台属性（包名、安装包体积、渠道站是否集中上架）。
6. **「云游戏注册」数据源已停用**，任何报告都不含。

---

## 流水线一览

| 步骤 | 脚本 | 输入 | 输出 | 能否自动 |
|---|---|---|---|---|
| 00 | `00_probe_inputs.py` | 两期 xlsx | 控制台结构报告 | ✅ |
| 01 | `01_prep_search_dl.py` | 两期 xlsx + 词库 | `search_agg.csv` / `dl_agg.csv` / `dl_daily.csv` | ✅ |
| 02 | `02_extract_steam_meta.py` | 种子 + 历史 Excel | `steam_meta.json` | ✅ |
| 03 | `03_build_steam_chart.py` | **SteamDB 当期 Top100** | `chart.csv` | ⚠️ 需更新快照 |
| 04 | `04_build_report.py` | 01 + 02 + 03 | 五表 Excel + `data.json` | ⚠️ 判定需撰写 |
| 04b | `04b_make_covers.py` | Steam 封面 | `covers.json` | ✅（联网） |
| 05 | `05_gen_board.py` | `data.json` + `covers.json` | HTML 看板 | ⚠️ 热点需撰写 |
| 06 | `06_test_board.js` | 看板 HTML + `data.json` | 55 项断言结果 | ✅ |
| 08 | `08_preflight_check.py` | 全部产物 | 体检报告 | ✅ **门禁** |
| 07 | `07_publish_github.py` | 产出目录 | GitHub Pages 归档 | 可选 |

---

## 配置说明

所有路径集中在 `config.json`（由 `setup.py` 生成，已被 `.gitignore` 忽略）：

```json
{
  "data_dir": "D:/端游周报数据",
  "out_dir":  "D:/周报产出",
  "tmp_dir":  "D:/周报产出/_tmp_run",
  "period": {
    "cur":  { "label": "9.28-10.11", "dir": "9.28-10.11" },
    "prev": { "label": "9.14-9.27",  "dir": "9.14-9.27"  }
  },
  "run_date": "2026-10-12"
}
```

也可用环境变量临时覆盖：`GH_DATA_DIR` / `GH_OUT_DIR` / `GH_TMP` / `GH_CUR` / `GH_PREV` / `GH_RUN_DATE`。

---

## 环境

- Python 3.10+（`pandas` / `openpyxl` / `Pillow`）
- Node 18+（`jsdom`，仅回归测试用）
- 04b 需要访问 `store.steampowered.com` 抓封面；无网络时会回落为程序化生成的封面

---

## 已知限制

- **判定文案、热点 12 条、总结**是人工撰写内容，脚本无法自动生成。08 门禁能检测「沿用了上一期」，但写得好不好仍需人判断。
- **SteamDB 无官方 API**，03 的 Top100 是手工快照。刷榜频繁时建议每周固定时点抓取。
- **词库是增量维护的**：新游戏爆火后若不补词库，它的搜索量会被漏记或误挂到相近名称上。
