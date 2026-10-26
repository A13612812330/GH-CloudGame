# GH-CloudGame

> 📚 **本文档属于 GH 系列交接项目。** 总入口（全部 10 个仓库索引、可用性实测、可复制的 AI Agent prompt）：https://github.com/A13612812330/GH-Handover

端游云游戏「三源周报」的可复刻工程仓库 —— 脚本、词库、口径文档、AI Agent 执行契约、4 期历史产出，都在这里。

**给同事的一句话用法**：拿到自己的两份平台导出表 → 把这个仓库交给 AI Agent → 让它读 [`AGENT.md`](AGENT.md) → 跑出同款 Excel 五表 + HTML 看板。

## 接手须知（重要）

> **给接手人**：这个仓库**不含任何平台账号、密钥、Cookie 或登录态**。神策与鲸云的报表需要你自己登录平台导出 Excel，再放进 `samples/` 或指定目录。
> 仓库里自带两期真实样例数据（`samples/`），所以**不导数据也能先把流水线跑通看效果**。

> **给 AI Agent**：本仓库无任何凭据可读，**不要尝试猜测或补全平台账号**。你的任务是读
> [`AGENT.md`](AGENT.md) 的执行契约，用 `samples/` 数据跑通 `pipeline/09_run_all.py`，
> 并遵守 `08_preflight_check.py` 的交付门禁。

| 项目 | 状态 |
|---|---|
| 神策 / 鲸云 账号与密钥 | ❌ **仓库内没有**，数据由使用者自行导出 |
| `config.json`（本机路径） | ❌ **不入库**，由 `setup.py` 生成，`.gitignore` 已排除 |
| 样例数据 | ✅ `samples/9.14-9.27/`、`samples/9.28-10.11/` 两期可直接跑 |
| 历史产出 | ✅ `outputs/` 四期（Excel 大报告 + HTML 看板） |

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
npm i jsdom                 # 仅 06 回归测试需要；不装也行，09 会跳过检查并提示

cd pipeline
# 1) 配一次路径（也可直接跑 python setup.py 弹窗点选文件夹）
python setup.py --data-dir ../samples --out-dir ../outputs/_local \
                --cur 9.28-10.11 --prev 9.14-9.27 --run-date 2026-10-12

# 2) 一条命令跑完 00 → 08（含环境自检 + 回归测试 + 交付门禁）
python 09_run_all.py
```

就这两步。`09_run_all.py` 会按固定顺序执行、逐步打印、**任何一步失败立即中止**，
最后跑 08 门禁；门禁 PASS 才代表产物可交付。

常用变体：

```bash
python 09_run_all.py --list              # 只看会跑哪些步骤
python 09_run_all.py --until 05          # 只跑到看板生成（调试样式用）
python 09_run_all.py --from 06           # 从断点续跑，跳过已完成的步骤
python 09_run_all.py --publish           # 额外跑 07 归档到 GitHub Pages
python 09_run_all.py --no-gate           # 跳过 08 门禁（仅调试，产物不可交付）
```

不方便用命令行？`python setup.py` 会弹出文件夹选择框，点选数据目录即可。

> ⚠️ **跑新一期前必读** [`AGENT.md`](AGENT.md) 第 4 节：SteamDB 快照、判定文案、热点 12 条
> 这三样必须**现场重写**，脚本里固化的是 2026-10-12 那期的内容。
> 如果没重写就跑，**08 门禁会拦住**（它会用「数字指纹」认出文案还停在上期）。

---

## 仓库结构

```
GH-CloudGame/
├── AGENT.md              ★ AI Agent 入口（执行契约 / 红线 / 必做清单）
├── README.md             本文件
├── config.example.json   路径配置模板（setup.py 会自动生成 config.json）
├── requirements.txt      Python 依赖
├── package.json          Node 依赖（jsdom）
├── pipeline/             流水线 00 → 09（09 = 一键入口，其余为单步）
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
| **09** | **`09_run_all.py`** | 配置就绪即可 | 按序跑完下列全部步骤 | ✅ **一键入口** |
| 00 | `00_probe_inputs.py` | 两期 xlsx | 控制台结构报告 | ✅ |
| 01 | `01_prep_search_dl.py` | 两期 xlsx + 词库 | `search_agg.csv` / `dl_agg.csv` / `dl_daily.csv` | ✅ |
| 02 | `02_extract_steam_meta.py` | 种子 + 历史 Excel | `steam_meta.json` | ✅ |
| 03 | `03_build_steam_chart.py` | **SteamDB 当期 Top100** | `chart.csv` | ⚠️ 需更新快照 |
| 04 | `04_build_report.py` | 01 + 02 + 03 | 五表 Excel + `data.json` | ⚠️ 判定需撰写 |
| 05a | `10_draft_hotspots.py` | `data.json` | `hot_draft.json` / `covers_plan.json` / `hot_review.md` | ⚠️ **半自动**：机器挑料 + 模板句，人补归因 |
| 04b | `04b_make_covers.py` | Steam 封面（或 `--plan covers_plan.json`） | `covers.json` | ✅（联网） |
| 05 | `05_gen_board.py` | `data.json` + `covers.json`（`--hot` 可选） | HTML 看板 | ✅ 默认手写热点；带 `--hot` 用初稿 |
| 06 | `06_test_board.js` | 看板 HTML + `data.json` | 55 项断言结果 | ✅ |
| 08 | `08_preflight_check.py` | 全部产物 | 体检报告 | ✅ **门禁** |
| 07 | `07_publish_github.py` | 产出目录 | GitHub Pages 归档 | 可选 |

---

## 热点半自动（05a）

12 条热点原来全靠手写，换期容易忘改、产出「数据是新的、结论还是上期」的假报告。
`10_draft_hotspots.py` 把机械部分接过去了：**按规则挑料 + 套带真实数字的模板句**，
人只补「为什么涨」和「版号」。

12 个槽位里 **10 个自动**（大盘 / 搜索涨幅王 / 下载涨幅王 / 搜索榜首 / Steam 在线王 /
三源共振 / 新游观察 / 退潮预警 / 跨端外溢 / 独立游戏王 / 移植候选），
**1 个必须人工**（第 11 条 📜 版号重点 —— 要查国家新闻出版署当期公告，脚本拿不到）。

```bash
python 10_draft_hotspots.py --show          # 先看一眼挑了哪些标的
python 09_run_all.py --draft-hot --from 04  # 生成初稿三件套
#  → 看 <中间产物>/hot_review.md，改 hot_draft.json
python 09_run_all.py --from 04b             # 自动 --plan 抓封面、--hot 出看板
```

**三道闸**，保证半成品不会当成成品发出去：

| 闸 | 行为 |
|---|---|
| `05_gen_board.py` | 初稿里还有 `_needs_human` → **拒绝出看板**（退出码 3）；`--allow-draft` 可放行但打 `data-draft` 标记 |
| `08_preflight_check.py` | 检出 `data-draft` 或 `[待人工填写]` → **BLOCK** |
| `08_preflight_check.py` | 数字指纹：热点里一个本期数字都没命中 → **BLOCK** |

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
