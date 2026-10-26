# samples · 最小可跑样例

两期**真实**平台导出数据（未脱敏）。本仓库为 Private，数据仅限内部使用，
**不要外发、不要转到公开仓库**。

```
samples/
├── 9.14-9.27/              上期
│   ├── 搜索9.14-9.27.xlsx
│   └── 鲸云下载.xlsx
└── 9.28-10.11/             本期
    ├── 搜索量9.28-10.11.xlsx
    └── 鲸云下载.xlsx
```

## 直接跑

```bash
cd ../pipeline
python setup.py --data-dir ../samples --out-dir ../outputs/_local \
                --cur 9.28-10.11 --prev 9.14-9.27 --run-date 2026-10-12
python 01_prep_search_dl.py && python 02_extract_steam_meta.py
python 03_build_steam_chart.py && python 04_build_report.py
python 04b_make_covers.py && python 05_gen_board.py
node 06_test_board.js && python 08_preflight_check.py
```

## 这两份表的特征

| 文件 | sheet | 关键列 | 粒度 |
|---|---|---|---|
| 搜索 | `明细数据` | 行为时间 / 搜索内容 / 总次数 | 2 个日期列（各代表一周） |
| 搜索 | `汇总数据` | 搜索内容 / 总和 | 两期合计 |
| 下载 | `明细数据` | 行为时间 / 游戏名称 / 下载开始 | **14 天逐日** |
| 下载 | `汇总数据` | 游戏名称 / 合计 | 两期合计 |

> 下载源的粒度**不固定**（也可能是 2 列周汇总）。
> 换自己的数据时，先按 [docs/02-数据口径](../docs/02-数据口径.md) 第二节做粒度自证。

## 换自己的数据

按同样的目录结构放两期即可，文件名不必一致（脚本按关键词探测）。
详见 [docs/01-快速开始](../docs/01-快速开始.md) 最后一节。
