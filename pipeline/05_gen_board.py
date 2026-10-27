# -*- coding: utf-8 -*-
# ============================================================================
# 端游周报流水线 · 步骤 05：生成 HTML 看板（读 data.json）
# 用法：python 05_gen_board.py [--hot <hot_draft.json>] [--allow-draft]
# ----------------------------------------------------------------------------
# 【样式基线】用户指定：看板视觉必须沿用「端游三源周报看板_8.17-8.30.html」这一版
#   浅色优雅风（--bg:#f4f6fb / --accent:#1e4ed8 / 6 列 KPI / 2 列 chart-card /
#   热点 ticker + hot-grid / Tabs 明细表 / 渐变 sum-card / 深浅主题切换）。
#   ⛔ 不要再用 05_gen_board_newstyle.py（深色霓虹风），已归档到 _deprecated/。
# ----------------------------------------------------------------------------
# 每次新一周需要改的配置：
#   1) OUT              —— 输出 HTML 文件名
#   2) HOT / SUMMARY    —— 本周联网热点与总结文案（人工撰写）
#   3) KW / 表头/列名   —— 若输入表列名变化需同步
# 全套顺序：00 → 01 → 02 → 03 → 04 → 04b → 05 → 06
# ----------------------------------------------------------------------------
# 【HOT 固定 12 条】用户指定：本期游戏圈热点数量固定为 12，不足须补足、不随意增减。
#   12 条中必须保留以下两类固定栏目（位置固定在末尾两条）：
#     第 11 条「📜 版号重点」—— 当期/最近一批版号 + 审批变更（尤其「补客户端」类），
#        取材：国家新闻出版署公布名单 + 竞核等行业统计；封面用程序化 license 信息图
#     第 12 条「🎮 移植候选」—— 端游转手游的独立游戏候选，
#        取材：data.json 的 s3 表中「独立游戏 == 是」筛选（约 25 款），
#        再按「适配触屏 / 体量小 / 人气在线 / 尚无成功手游版」四条标准挑 4 款做 cover4 拼贴
#   其余 10 条为常规热点（大盘 / 退潮 / 新品 / 品类 / 竞品动作等）。
# ============================================================================
"""端游三源周报看板生成 · 浅色优雅风（8.17-8.30 样式基线）"""
import json, os, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cfg import CFG  # noqa: E402  统一配置（路径只从 config.json 来）

TMP = str(CFG.tmp)
OUT = str(CFG.board_out())

data = json.load(open(f"{TMP}/data.json", encoding="utf-8"))
COVERS = json.load(open(f"{TMP}/covers.json", encoding="utf-8"))   # 04b 产出，热点封面

# 热点主视觉：
#   cover  -> 单图（04b 抓到的 Steam 真实封面，key 见 04b COVERS）
#   cover4 -> 2x2 拼贴（复用已有图，不额外占体积）
#   viz    -> 用真实数据实时绘制的小图表（大盘/涨跌类，无对应游戏图）
HOT = [
    {"tag": "📈 大盘爆发", "cls": "up",
     "title": "国庆假期拉动端游双源同涨：搜索 +72.9%、下载 +46.0%",
     "desc": "本期端游搜索命中 131 款 / 3,003,769 次，跨期 +72.9%（上期 1,737,746 次）；鲸云下载 104,846 次，跨期 +46.0%（上期 71,795 次）。但必须先剔除假期效应：全站搜索同期 +53.3%（888.5 万 → 1,362.2 万），端游占比由 19.56% 升至 22.05%，跑赢大盘约 19.6 个百分点 —— 这才是端游的真实超额，而不是 +72.9% 这个绝对数字。",
     "src": "神策搜索 / 鲸云下载",
     "vizdata": {"tt": "本期跨期涨跌（含国庆 10.1-10.7 加成）",
                 "rows": [{"n": "端游搜索", "v": 72.9}, {"n": "全站搜索", "v": 53.3},
                          {"n": "鲸云下载", "v": 46.0}],
                 "sub": "端游搜索跑赢全站 19.6pp，份额升至 22.05%"}},
    {"tag": "🔥 搜索榜异动", "cls": "hot",
     "title": "搜索榜第 2 的《OVERPEAK》实为国际服手游，端手数据混流",
     "desc": "《OVERPEAK》（中文名「巅峰崛起」，玩家称「祖国人模拟器」）搜索 318,165 次、跨期 +1082%，跃居端游搜索第 2、仅次于植物大战僵尸。但它并不是端游：实为国际服手游（包名 com.rusergames.overpeak，安装包约 300MB），国内 3DM / 西西 / 逗游等渠道站自 10/6 起集中铺量下载页，热度主要来自移动端与短视频导流。其搜索构成里「超人」这一单一泛词就占 99,576 次（31%），「OVER / OVE」等截断词约 2.97 万次归属在 OVERPEAK 与守望先锋之间无法完全区分。提示：神策搜索源不分端手游，跨端外溢会污染端游榜，该条不宜按端游标的排位与配资源。",
     "src": "神策搜索 / 渠道站检索",
     "vizdata": {"tt": "OVERPEAK 搜索构成（本期 318,165 次）",
                 "rows": [{"n": "「超人」泛词", "v": 31.3}, {"n": "OVER* 截断词", "v": 12.4},
                          {"n": "OVERPEAK", "v": 10.3}, {"n": "「祖国人」系", "v": 7.4},
                          {"n": "超峰时刻", "v": 6.1}],
                 "sub": "泛词 + 截断词合计过半，量级需打折看待"}},
    {"tag": "🔥 下载冠军", "cls": "hot",
     "title": "《漫威蜘蛛侠2》登顶鲸云下载榜，跨期 +278.4%",
     "desc": "本期鲸云下载第 1（8,212 次）跨期 +278.4%，搜索端同步 +216.4%（60,233 次）—— 是本期最强的双源共振单品。系列作《漫威蜘蛛侠：迈尔斯莫拉莱斯》下载 2,774 次（+148.1%）同样走高，两作齐飞。蜘蛛侠 IP 在国庆档的集中释放，建议做「蜘蛛侠系列」组合位承接电影 / 剧集热度，并从入口页直达系列合集。",
     "src": "鲸云数据 / 神策搜索", "cover": "spider2"},
    {"tag": "🔥 品类红利", "cls": "up",
     "title": "模拟驾驶成假期最大赢家：巴士模拟 +1280.8%、地平线5 搜索 +128.0%",
     "desc": "巴士模拟搜索 125,499 次（跨期 +1280.8%，上期仅 9,089），登顶涨幅榜，主体是新增的「巴士模拟2 / 巴士模拟二」词；《极限竞速：地平线5》搜索 +128.0% 且下载 +110.1%（5,014 次，第 4），同系列《地平线6》下载 1,040 次（+125.6%）同步走高；「遨游中国2（欧卡 MOD）」下载 +51.3%（4,868 次，第 5）。拟真驾驶是本期最集中的正增长品类 —— 长时段、低操作门槛，最适配云游戏资源位。",
     "src": "神策搜索 / 鲸云数据", "cover": "horizon5"},
    {"tag": "⚠️ 头号退潮", "cls": "warn",
     "title": "《渔力全开》由双源第 1 退至下载第 3，跨期 -39.5%",
     "desc": "上期还是搜索 +264%、下载第 1、Steam 销量第 1 的三源共振冠军，本期全面退潮：鲸云下载 5,305 次（第 3）跨期 -39.5%，而下载大盘 +46.0% —— 跑输约 86 个百分点；搜索 25,877 次亦 -0.8%（大盘 +72.9%）；Steam 在线已跌出 Top100，仅剩历史峰值 37.4 万作参照。热度已过峰，建议从「拉新投放」转为「存量运营 + 组合套餐」，避免继续重投资源位。",
     "src": "鲸云数据 / SteamDB", "cover": "howtofish"},
    {"tag": "📌 基本盘", "cls": "warn",
     "title": "头部常青款虽同步走高，但全部跑输假期涨幅",
     "desc": "搜索榜前列：植物大战僵尸 415,007（+31.3%）、ROBLOX 220,175（+30.1%）、我的世界 216,991（+60.6%）、GTA 侠盗猎车手 136,124（+30.3%）、绝地求生 PUBG 128,058（+42.9%）。换算成「相对大盘 +72.9% 的超额」全部为负 —— 假期的增量更多流向了新爆款与解压向新品，常青款份额被稀释。做单品判断时务必以「是否跑赢 +72.9%」为准，而非绝对涨幅。",
     "src": "神策搜索",
     "vizdata": {"tt": "头部常青款 vs 大盘 +72.9%",
                 "rows": [{"n": "我的世界", "v": 60.6}, {"n": "绝地求生 PUBG", "v": 42.9},
                          {"n": "植物大战僵尸", "v": 31.3}, {"n": "GTA 侠盗猎车手", "v": 30.3},
                          {"n": "ROBLOX", "v": 30.1}],
                 "sub": "全部低于大盘，份额被新爆款稀释"}},
    {"tag": "🆕 新品上线", "cls": "hot",
     "title": "《永恒之塔2》(AION 2) 9/30 开服，在线 21.1 万升至 Steam 第 4",
     "desc": "本期内上线的端游大作为 NCSoft《永恒之塔2》，9/30 开服后当前在线 21.1 万、列 Steam 在线榜第 4。同期新面孔还有《Deskrawl: Idle ARPG》（放置挂机，在线 4.43 万）与《UBERMOSH:OMEGA》（单日脉冲 17.5 万，已回落至 2.76 万，属限免脉冲，勿按长线热度配置）。韩国 MMORPG 端游在国区云游戏有一定承接空间，但需先确认锁区与账号体系，避免上线即不可用。",
     "src": "SteamDB / 官方公告", "cover": "aion2"},
    {"tag": "📉 两极分化", "cls": "warn",
     "title": "下载端两极分化：IP 与拟真驾驶暴涨，派对 / 沙盒退潮",
     "desc": "增长侧：漫威蜘蛛侠2 +278.4%、神力科莎 +242.8%、看门狗2 +154.1%、迈尔斯莫拉莱斯 +148.1%、王国保卫战5：联盟 +137.5%、恶魔轮盘 +127.6%。退潮侧：农场捡鸡蛋模拟器 -46.1%、渔力全开 -39.5%、朋友梭哈吧 -33.5%、落叶清理模拟器 -20.5%。建议把资源位从派对 / 沙盒类向「IP 大作 + 拟真驾驶 + 解压短时长」三条线迁移。",
     "src": "鲸云数据",
     "vizdata": {"tt": "下载端涨跌两极（跨期）",
                 "rows": [{"n": "漫威蜘蛛侠2", "v": 278.4}, {"n": "神力科莎", "v": 242.8},
                          {"n": "看门狗2", "v": 154.1}, {"n": "迈尔斯莫拉莱斯", "v": 148.1},
                          {"n": "恶魔轮盘", "v": 127.6}],
                 "sub": "增长集中在 IP 与拟真驾驶，退潮集中在派对 / 沙盒"}},
    {"tag": "🟦 Steam 观察", "cls": "warn",
     "title": "桌面伴侣 / 挂机类仍是最稳的长在线品类，但已过爆发期",
     "desc": "Steam 当前在线前三：邦戈猫 154,090（历史峰值 19.5 万）、战狗 WARDOGS 67,901（峰值 42.9 万）、任务栏英雄 59,964（峰值 54.6 万），三者均较峰值明显回落。以「当前 / 峰值」比看，英灵神殿（5.24 万 / 50.2 万）与杀戮尖塔2（4.85 万 / 57.5 万）相对强度最高，属仍在上行或刚过峰的标的。桌面伴侣 / 挂机这条线仍是 2026 年云游戏最稳的「长在线」来源。",
     "src": "SteamDB", "cover": "bongocat"},
    {"tag": "📈 假期节奏", "cls": "up",
     "title": "下载逐日曲线：连续 5 天破万，节后回落至 3,000 量级",
     "desc": "假期极值出现在 10/2（11,934），10/1~10/5 连续五天破万；节后迅速回落，10/9 仅 3,171；10/11 周末又冲高至 10,464。日均与工作日相差 3~4 倍，说明鲸云的下载需求高度依赖「整块闲暇时间」。容量规划应按「假期 / 周末峰值」而非日均配置 —— 节后一周反而是最容易被低估的容量空窗。",
     "src": "鲸云下载数据", "viz": "daily"},
    {"tag": "📜 版号重点", "cls": "hot",
     "title": "9 月版号 9/30 落地：209 款获批（国产 206 + 进口 3），15 款变更",
     "desc": "9 月批次于 9/30 公布，正好落在本期内：合计 209 款（国产 206、进口 3），年内累计 1,571 款（国产 1,525 + 进口 46），前三季度同比 +23%。重点产品：米哈游《源初之结》（UE5 写实奇幻 ARPG，多人合作、角色不抽卡）、祖龙《诡秘之主：愚者》、恺英《龙之谷：觉醒》（国产）与《热血江湖：重启》（进口）、四三九九《火线精英：突围》、游卡《三国杀：天命棋局》、电魂《我叫MT：荣耀之战》。品类结构：移动 110 + 移动休闲益智 75 + 移动与客户端双端 16 + 纯客户端 2 + 三端 2 + 主机 1，端游相关合计 21 款。15 条变更中，《绒爪行动》更名《绒雪行动》并新增客户端、《潜水员戴夫》新增 PS5 版本 —— 「手游补端」仍是云游戏可提前锁定的标的来源。",
     "src": "国家新闻出版署 / 上证报·证券时报", "cover": "license"},
    {"tag": "🎮 移植候选", "cls": "up",
     "title": "端游转手游：本期 4 款独立游戏最值得谈",
     "desc": "从本期 57 款 Steam 端游里筛出 20 款独立游戏，按「玩法适配触屏 + 体量小 + 人气在线 + 尚无成功手游版」四条标准，优先标的：杀戮尖塔2（卡牌构筑，在线 4.85 万、峰值 57.5 万，安装 2.71GB）、任务栏英雄（挂机自动战斗，仅 0.55GB，在线 6.0 万、峰值 54.6 万）、邦戈猫（超休闲桌面伴侣，在线 15.4 万，独立游戏在线第 1）、环世界（殖民地模拟，仅 1.07GB，在线 2.13 万）。四款云化成本都极低，卡牌 / 挂机 / 模拟三条线在手游市场的变现模型最成熟。",
     "src": "Steam 在线 / 神策搜索 / 鲸云下载",
     "cover4": ["sts2", "tbh", "bongocat", "rimworld"]},
]

SUMMARY = [
    ("本期大盘", "**假期效应消退，两源同步回落**：端游搜索 223.17 万次 vs 上期 300.38 万次（**-25.7%**；全站 -20.7%，端游占比 22.05% → **20.65%**，跑输大盘约 5.0pp）；鲸云下载 83,907 次 vs 上期 104,846 次（**-20.0%**）。上期含国庆 10.1-10.7、本期为纯工作日，**回落首先是假期结束，不是需求萎缩**。"),
    ("口径说明", "对比基准为**上期两周（9.28-10.11）**，非本期内部 W1 vs W2。两期粒度不同但跨度等效：搜索两期各含 2 个周一列（10/12 与 10/19 / 9/28 与 10/5），**每列代表一周**；下载**本期为 2 列周汇总、上期为 14 天逐日**，两者均覆盖 14 天，可直接比。"),
    ("假期效应是双向的", "上期端游搜索 **+72.9%、跑赢全站 19.6pp**；本期 **-25.7%、跑输全站 5.0pp** —— 同一批用户在假期被放大、假期后又回吐，且端游的放大与回吐幅度都大于全站。判断端游景气度只看**相对全站的超额**，不看绝对环比。"),
    ("逆势主线：拟真驾驶", "下载大盘 -20.0% 的背景下，**极限竞速：地平线5** 下载 7,212（第 1）**+43.8%**、地平线6 1,572（**+51.2%**）、地平线4 458（+19.6%）、欧卡2 1,396（+1.4%）、俄罗斯钓鱼4 777（**+89.1%**）—— 本期**唯一整条线集体逆势**的品类。"),
    ("本期黑马：月球清洁队", "10/23 上线即 **44,301 在线（Steam 第 64）**、24h 峰值 51,686；2 人团队 DragDrop Games 的 16 人合作清洁模拟，首周末同接破 3.6 万、好评率约 76%，最低配置仅 **GTX 1650 / 8GB**。同窗口新品：《最终幻想：共鸣》（10/23 Steam，2.44 万）、《雾锁王国》正式版（10/15，5.25 万）。"),
    ("上期爆款集体腰斩", "**OVERPEAK** 搜索 -81.8%（318,165 → 57,991，且本就不是端游）、**软体汽车** -68.8%、**渔力全开** -57.9%（下载 -71.4%）、**漫威蜘蛛侠2** -57.1%（下载 -33.5%）—— 上期四个头条本期全部腰斩，**脉冲型热度的半衰期约 2 周**，按爆款配的资源位应全部降级。"),
    ("抗跌基本盘", "我的世界 -12.6%、GTA -7.2%、NBA2K -8.4%、三角洲行动 -10.1%、ROBLOX -15.9%、植物大战僵尸 -25.0% —— 常青款跌幅普遍小于大盘 10~18pp，是资源位的稳定底盘，**不宜随大盘下行而缩减**。"),
    ("补充说明", "①搜索两期各含 2 个周一列，每列代表一周；②下载本期 2 列周汇总 / 上期 14 天逐日，均覆盖 14 天；③Steam 源改用**官方接口**取榜（SteamDB 已对自动化 403），快照 **2026-10-27**，筛出非网游/非工具端游 **59 款**；**新进榜标的的历史峰值以本期 24h 峰值为下限**，真实值可能更高；④**不含鲸云注册数据源**。"),
]


# ---------------------------------------------------------------- 热点来源（半自动）
# 默认用上面手写的 HOT。要让 10_draft_hotspots.py 的初稿生效，传 --hot <json> 或设 GH_HOT。
_HOT_FILE, _ALLOW_DRAFT, _need = None, False, []
_argv = list(sys.argv[1:])
if "--allow-draft" in _argv:
    _ALLOW_DRAFT = True
    _argv.remove("--allow-draft")
if "--hot" in _argv:
    _i = _argv.index("--hot")
    if _i + 1 >= len(_argv):
        sys.exit("[中止] --hot 后面要跟 JSON 路径")
    _HOT_FILE = Path(_argv[_i + 1])
elif os.environ.get("GH_HOT"):
    _HOT_FILE = Path(os.environ["GH_HOT"])

HOT_SRC = "手写（脚本内）"
if _HOT_FILE is not None:
    if not _HOT_FILE.is_file():
        sys.exit("[中止] 找不到热点文件：%s" % _HOT_FILE)
    try:
        _h = json.loads(_HOT_FILE.read_text(encoding="utf-8"))
    except Exception as _e:
        sys.exit("[中止] 热点文件解析失败：%s" % _e)
    if not isinstance(_h, list) or len(_h) != 12:
        sys.exit("[中止] 热点必须正好 12 条，当前 %s 条"
                 % (len(_h) if isinstance(_h, list) else "不是数组"))
    for _i, _x in enumerate(_h, 1):
        for _req in ("tag", "title", "desc", "src"):
            if not _x.get(_req):
                sys.exit("[中止] 第 %d 条缺字段 %s" % (_i, _req))
    _need = [_i for _i, _x in enumerate(_h, 1) if _x.get("_needs_human")]
    if _need and not _ALLOW_DRAFT:
        print("[拒绝出看板] 第 %s 条热点仍标 _needs_human —— 这些要查外部公告或做判断，"
              "脚本给不了。" % "、".join(map(str, _need)))
        print("  ① 改好 %s，把这些条目的 _needs_human 去掉（或置 false）；" % _HOT_FILE.name)
        print("  ② 只想先看版式可加 --allow-draft（会打草稿水印，08 门禁照样拦）。")
        sys.exit(3)
    # 下划线开头的是给人/脚本看的元信息，不进页面
    HOT = [{k: v for k, v in _x.items() if not str(k).startswith("_")} for _x in _h]
    HOT_SRC = "%s（%s）" % (_HOT_FILE.name, "草稿" if _need else "已复核")
    print("[热点] 载入 %s，共 12 条" % HOT_SRC)

KW = {
    "s1": ["端游名称", "本期搜索", "上期搜索", "两期合计", "环比", "关键词数", "品类", "代表性搜索词"],
    "s2": ["游戏名称", "本期下载", "上期下载", "两期合计", "环比"],
    "s3": ["中文名称", "游戏名称(原名)", "appid", "开发者", "玩法标签", "发行日期", "近一年内上线",
           "类型", "安装大小", "当前在线(10/12)", "24h峰值", "历史峰值", "独立游戏", "备注"],
}
# 列名带快照日期（当前在线(10/12)），必须从 data.json 派生 —— 否则换期表头与数据错位
_online_k = next((k for k in list((data.get("s3") or [{}])[0]) if str(k).startswith("当前在线")), None)
if _online_k:
    KW["s3"] = [_online_k if str(k).startswith("当前在线") else k for k in KW["s3"]]

# 热点实际引用到的图片才注入（去重，避免 base64 重复膨胀）
_used = []
for _h in HOT:
    for _k in ([_h["cover"]] if _h.get("cover") else []) + list(_h.get("cover4") or []):
        if _k not in _used:
            _used.append(_k)
COVERS = {k: v for k, v in COVERS.items() if k in _used}

# 标题与副标题从 data.json 的 meta 派生，换期不用手改
_meta = data.get("meta") or {}
_range = str(_meta.get("range") or "")
_prev_lab = str(_meta.get("prev") or "")
_snap = str(_meta.get("snapshot") or "")
_snap_md = (_snap[5:7].lstrip("0") + "/" + _snap[8:10].lstrip("0")) if len(_snap) >= 10 else _snap
TITLE = "端游三源周报 · " + _range.replace(" ~ ", "~")
SUB = ("搜索 × 鲸云 × SteamDB 三源交叉验证 · 本期 {} "
       "<b>对比上期 {}</b> · 数据截止 {}").format(_range, _prev_lab, _snap_md)

# 下载源粒度每期不同（可能 14 天逐日、也可能 2 列周汇总）——文案必须跟着变，不能写死
DAILY_N = len(((data.get("daily") or {}).get("labels")) or [])
DL_SPAN = "14 天逐日" if DAILY_N >= 7 else "%d 个周汇总" % DAILY_N
DAILY_TITLE = ("📉 鲸云下载 14 天逐日趋势" if DAILY_N >= 7
               else "📉 鲸云下载分期走势（本期 %d 个周汇总）" % DAILY_N)
DAILY_SUB = ("本期 %s 每日下载总量，假期与周末双高峰" % _range
             if DAILY_N >= 7 else
             "本期导出仅含 %d 个周汇总列、无逐日明细；单点代表一周合计" % DAILY_N)
FOOT_SRC = ("数据来源：%s（神策·搜索事件，本期两个周一快照）· %s（神策·云游戏，%s）· "
            "Steam 官方接口 %s 快照 · 热点为 %s 联网检索"
            % (CFG.search_file("cur").stem, CFG.dl_file("cur").stem, DL_SPAN, _snap, _snap_md))
FOOT_GEN = "生成于 %s" % _snap

payload = json.dumps({**data, "KW": KW}, ensure_ascii=False)
hot_json = json.dumps(HOT, ensure_ascii=False)
sum_json = json.dumps(SUMMARY, ensure_ascii=False)
cov_json = json.dumps(COVERS, ensure_ascii=False)

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<style>
:root{
  --bg:#f4f6fb; --card:#ffffff; --txt:#1c2333; --sub:#667085; --line:#e4e8f0;
  --accent:#1e4ed8; --accent2:#3b82f6; --up:#e03e3e; --down:#12a150;
  --hdr:#1e3a6e; --hdr-txt:#fff; --hover:#f0f4ff; --shadow:0 2px 10px rgba(20,40,90,.06);
  --grad:linear-gradient(135deg,#1e3a6e,#2563eb 55%,#38bdf8);
}
[data-theme="dark"]{
  --bg:#0d1117; --card:#161d29; --txt:#e6edf3; --sub:#8b98a9; --line:#273244;
  --accent:#3b82f6; --accent2:#60a5fa; --up:#f87171; --down:#4ade80;
  --hdr:#1f2d45; --hdr-txt:#e6edf3; --hover:#1c2940; --shadow:0 2px 10px rgba(0,0,0,.35);
  --grad:linear-gradient(135deg,#132238,#1e3a5f 55%,#1f4e79);
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--txt);font-family:"Microsoft YaHei","PingFang SC",sans-serif;font-size:14px;transition:background .3s,color .3s}
.wrap{max-width:1320px;margin:0 auto;padding:0 24px 60px}
/* 顶部渐变横幅 */
.hero{border-radius:0 0 22px 22px;padding:28px 30px 26px;color:#fff;position:relative;overflow:hidden;margin-bottom:18px;
  background-image:
    repeating-linear-gradient(90deg,rgba(255,255,255,.05) 0 1px,transparent 1px 44px),
    repeating-linear-gradient(0deg,rgba(255,255,255,.05) 0 1px,transparent 1px 44px),
    var(--grad)}
.hero::after{content:"";position:absolute;right:-60px;top:-60px;width:260px;height:260px;border-radius:50%;background:rgba(255,255,255,.07)}
.hero::before{content:"";position:absolute;right:80px;bottom:-100px;width:200px;height:200px;border-radius:50%;background:rgba(255,255,255,.05)}
.hero h1{font-size:26px;font-weight:800;letter-spacing:.5px;display:flex;align-items:center;gap:10px}
.hero .sub{opacity:.85;font-size:13px;margin-top:6px}
.hero .chips{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.chip{background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.25);padding:4px 12px;border-radius:16px;font-size:12px;backdrop-filter:blur(4px)}
.theme-btn{position:absolute;top:20px;right:24px;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);color:#fff;padding:7px 16px;border-radius:10px;cursor:pointer;font-size:13px;backdrop-filter:blur(4px);transition:.2s}
.theme-btn:hover{background:rgba(255,255,255,.28)}
/* 热点滚动条 */
.hot-ticker{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin-bottom:18px;box-shadow:var(--shadow);display:flex;align-items:center}
.hot-ticker .hot-label{background:linear-gradient(135deg,#e03e3e,#f97316);color:#fff;font-size:12px;font-weight:700;padding:10px 14px;white-space:nowrap;flex-shrink:0;display:flex;align-items:center;gap:5px}
.hot-ticker .track{overflow:hidden;flex:1;position:relative}
.hot-ticker .track-inner{display:inline-flex;gap:44px;padding:11px 16px;white-space:nowrap;animation:scroll 46s linear infinite;font-size:12.5px}
.hot-ticker .track-inner span{color:var(--txt);opacity:.92}
.hot-ticker .track-inner b{color:var(--up)}
@keyframes scroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
/* KPI */
.kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:18px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 15px;box-shadow:var(--shadow);position:relative;overflow:hidden;transition:transform .2s,box-shadow .2s}
.kpi:hover{transform:translateY(-3px);box-shadow:0 6px 18px rgba(20,40,90,.12)}
.kpi .lbl{color:var(--sub);font-size:12px;margin-bottom:5px}
.kpi .val{font-size:21px;font-weight:800;font-variant-numeric:tabular-nums}
.kpi .val small{font-size:11px;color:var(--sub);font-weight:400}
.kpi .note{font-size:11px;color:var(--sub);margin-top:3px}
.kpi.up{border-top:3px solid var(--up)} .kpi.blue{border-top:3px solid var(--accent2)}
.kpi .hot{position:absolute;top:9px;right:11px;font-size:17px}
@media(max-width:900px){.kpis{grid-template-columns:repeat(3,1fr)}}
@media(max-width:560px){.kpis{grid-template-columns:repeat(2,1fr)}}
/* 区块 */
.sec{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin-bottom:16px;box-shadow:var(--shadow)}
.sec h2{font-size:15.5px;font-weight:800;margin-bottom:4px;display:flex;align-items:center;gap:8px}
.sec .desc{color:var(--sub);font-size:12px;margin-bottom:14px}
.sec .tag{background:rgba(37,99,235,.1);color:var(--accent2);font-size:11px;padding:2px 9px;border-radius:12px;font-weight:700}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.chart-card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:var(--shadow);transition:transform .2s}
.chart-card:hover{transform:translateY(-2px)}
.chart-card h3{font-size:14.5px;font-weight:800;margin-bottom:3px}
.chart-card .sub{color:var(--sub);font-size:11.5px;margin-bottom:12px}
@media(max-width:900px){.charts{grid-template-columns:1fr}}
/* 表格 */
.tbl-wrap{overflow-x:auto;max-height:520px;overflow-y:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:var(--hdr);color:var(--hdr-txt);padding:9px 11px;text-align:left;white-space:nowrap;cursor:pointer;user-select:none;position:sticky;top:0;z-index:2;font-weight:700}
th:hover{opacity:.92}
td{padding:8px 11px;border-bottom:1px solid var(--line);white-space:nowrap}
tr:hover td{background:var(--hover)}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.up-t{color:var(--up);font-weight:700}.down-t{color:var(--down);font-weight:700}
tr.key-row td{background:rgba(255,193,7,.08)}
tr.key-row:hover td{background:rgba(255,193,7,.14)}
.pill{display:inline-block;padding:1px 9px;border-radius:10px;font-size:11px;font-weight:700}
.pill.ok{background:rgba(18,161,80,.12);color:var(--down)}
.pill.no{background:rgba(120,130,150,.14);color:var(--sub)}
/* tabs */
.tabs{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.tab{padding:7px 16px;border-radius:9px;cursor:pointer;border:1px solid var(--line);background:var(--card);color:var(--txt);font-size:13px;font-weight:600;transition:.2s}
.tab.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.tab:hover:not(.active){background:var(--hover)}
.toolbar{display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap;align-items:center}
.toolbar input{flex:1;min-width:180px;padding:8px 13px;border:1px solid var(--line);border-radius:9px;background:var(--bg);color:var(--txt);font-size:13px;outline:none;transition:border .2s}
.toolbar input:focus{border-color:var(--accent2)}
.pane{display:none}.pane.active{display:block}
.cnt{color:var(--sub);font-size:12px;margin-top:8px}
/* 图表通用 */
svg text{font-family:"Microsoft YaHei",sans-serif}
.legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px;font-size:12px;color:var(--sub)}
.legend span{display:inline-flex;align-items:center;gap:5px}
.dot{width:10px;height:10px;border-radius:50%;display:inline-block}
/* 总结 */
.sum-card{background:var(--grad);border-radius:16px;padding:24px 26px;color:#fff;margin-top:4px}
.sum-card h3{font-size:17px;font-weight:800;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.sum-body p{font-size:13.5px;line-height:2;opacity:.96;margin-bottom:4px}
.sum-body b{color:#ffd166}
.footer{color:var(--sub);font-size:11px;text-align:center;margin-top:18px;line-height:1.9}
/* 热点区块（详细列表） */
.hot-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.hot-item{background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:13px 15px;transition:transform .2s,box-shadow .2s}
.hot-item:hover{transform:translateY(-2px);box-shadow:var(--shadow)}
.hot-item .ht{display:flex;align-items:center;gap:7px;margin-bottom:7px}
.hot-item .ht .tg{font-size:11px;font-weight:800;color:var(--accent2);background:rgba(37,99,235,.1);padding:2px 8px;border-radius:10px}
.hot-item .tt{font-size:13px;font-weight:800;margin-bottom:6px;line-height:1.55}
.hot-item .tx{font-size:12.5px;line-height:1.7;color:var(--sub)}
.hot-item .src{font-size:11px;color:var(--sub);opacity:.75;margin-top:7px}
@media(max-width:900px){.hot-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:600px){.hot-grid{grid-template-columns:1fr}}
/* 条形排行行 */
.rrow{display:grid;gap:8px;align-items:center;margin-bottom:7px;font-size:12px}
.rrow .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rrow .bar{height:15px;background:var(--bg);border-radius:3px;position:relative;overflow:hidden}
.rrow .bar > i{display:block;height:15px;border-radius:3px;transition:width .8s ease}
.rrow .vl{text-align:right;font-size:11.5px;color:var(--sub);font-variant-numeric:tabular-nums}

/* ===== 右侧悬浮定位条（收起=圆点 / 悬停=展开文字） ===== */
.rail{position:fixed;right:18px;top:50%;transform:translateY(-50%);z-index:40;
  width:34px;overflow:hidden;padding:9px 7px;border-radius:14px;
  background:color-mix(in srgb,var(--card) 90%,transparent);backdrop-filter:blur(14px);
  border:1px solid var(--line);box-shadow:0 6px 22px rgba(20,40,90,.14);
  display:flex;flex-direction:column;gap:2px;
  transition:width .3s cubic-bezier(.2,.7,.3,1),box-shadow .25s}
.rail:hover{width:198px;box-shadow:0 10px 30px rgba(20,40,90,.2)}
.rail a{display:flex;align-items:center;justify-content:flex-end;gap:9px;width:100%;
  padding:5px 4px;border-radius:9px;text-decoration:none;transition:background .18s}
.rail a:hover{background:var(--hover)}
.rail .lb{font-size:11.5px;font-weight:700;color:var(--sub);white-space:nowrap;
  opacity:0;transition:opacity .2s .05s,color .18s}
.rail:hover .lb{opacity:1}
.rail a:hover .lb,.rail a.on .lb{color:var(--accent2)}
.rail .dt{width:8px;height:8px;border-radius:50%;background:var(--line);flex-shrink:0;
  transition:background .2s,transform .2s}
.rail a:hover .dt{background:var(--accent2);transform:scale(1.25)}
.rail a.on .dt{background:var(--accent);transform:scale(1.55)}
/* 定位条进度：顶部读数 */
.rail .rail-hd{display:flex;align-items:center;justify-content:flex-end;gap:8px;
  padding:0 4px 6px;margin-bottom:5px;border-bottom:1px solid var(--line)}
.rail .rail-hd .lb{font-size:10.5px;letter-spacing:.6px;color:var(--sub);font-weight:800;opacity:0}
.rail:hover .rail-hd .lb{opacity:.8}
.rail .rail-hd .dt{background:var(--accent2);transform:scale(1.1)}
@media(max-width:1380px){.rail{right:10px}}
@media(max-width:1180px){.rail:hover{width:180px}}
@media(max-width:860px){.rail{display:none}}

/* ===== 区块标题装饰 ===== */
.sec h2::before{content:"";width:4px;height:15px;border-radius:2px;background:var(--accent)}
.chart-card h3{display:flex;align-items:center;gap:8px}
.chart-card h3::before{content:"";width:3px;height:14px;border-radius:2px;
  background:linear-gradient(180deg,var(--accent2),#38bdf8)}

/* ===== 热点卡（带封面主视觉） ===== */
.hot-grid{grid-template-columns:repeat(3,1fr)}
.hot-item{padding:0;overflow:hidden;display:flex;flex-direction:column;background:var(--card)}
.hot-item .cov{position:relative;aspect-ratio:16/9;overflow:hidden;background:var(--bg)}
.hot-item .cov img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .55s cubic-bezier(.2,.7,.3,1)}
.hot-item:hover .cov img{transform:scale(1.05)}
.hot-item .cov::after{content:"";position:absolute;inset:auto 0 0 0;height:46%;
  background:linear-gradient(180deg,transparent,rgba(8,12,22,.55))}
.hot-item .cov .badge{position:absolute;top:10px;left:10px;z-index:2;color:#fff;font-size:11px;
  font-weight:800;padding:3px 10px;border-radius:11px;backdrop-filter:blur(6px);
  background:rgba(12,18,32,.6)}
.hot-item .cov .badge.warn{background:rgba(224,62,62,.88)}
.hot-item .cov .badge.up{background:rgba(14,150,74,.88)}
.hot-item .cov .badge.hot{background:linear-gradient(135deg,#e03e3e,#f97316)}
.hot-item .cov4{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:2px;
  position:absolute;inset:0}
.hot-item .cov4 img{width:100%;height:100%;object-fit:cover}
.hot-item .bd{padding:13px 15px 15px;display:flex;flex-direction:column;flex:1}
.hot-item .tt{margin-top:0}
.hot-item .tx{flex:1}
.hot-item .src{margin-top:auto;padding-top:8px}
/* 数据类封面（无对应游戏图时，用真实数据现画） */
.hot-viz{position:absolute;inset:0;padding:14px 16px;display:flex;flex-direction:column;
  justify-content:center;gap:7px;background:linear-gradient(150deg,#111a2e,#1e3a6e 60%,#2563eb)}
.hot-viz .vt{font-size:11px;font-weight:800;color:rgba(255,255,255,.72);letter-spacing:.6px}
.hot-viz .vrow{display:grid;grid-template-columns:118px 1fr 62px;gap:9px;align-items:center;
  font-size:11.5px;color:#e8eefc}
.hot-viz .vrow .vb{height:8px;border-radius:5px;background:rgba(255,255,255,.16);overflow:hidden}
.hot-viz .vrow .vb i{display:block;height:8px;border-radius:5px;background:#ffd166}
.hot-viz .vbig{font-size:26px;font-weight:800;color:#fff;line-height:1.1}
.hot-viz .vsub{font-size:11px;color:rgba(255,255,255,.66)}

/* ===== 品类分布（环形图 + 联动排行） ===== */
.cat-wrap{display:flex;gap:20px;align-items:center;flex-wrap:wrap}
.cat-ring{width:212px;height:212px;flex-shrink:0;position:relative}
.cat-ring svg{width:212px;height:212px;display:block;overflow:visible}
.cat-ring path{cursor:pointer;transition:opacity .18s,transform .18s;transform-origin:106px 106px}
.cat-ring path.dim{opacity:.3}
.cat-ring path:hover{transform:scale(1.035)}
.cat-ring .mid{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;
  justify-content:center;pointer-events:none;text-align:center}
.cat-ring .mid .n{font-size:27px;font-weight:800;font-variant-numeric:tabular-nums}
.cat-ring .mid .l{font-size:11px;color:var(--sub);margin-top:1px}
.cat-list{flex:1;min-width:250px}
.cat-row{display:grid;grid-template-columns:12px 96px 1fr 92px 46px;gap:9px;align-items:center;
  padding:5px 8px;border-radius:8px;font-size:12.5px;transition:background .18s;cursor:default}
.cat-row:hover,.cat-row.on{background:var(--hover)}
.cat-row .cbar{height:8px;border-radius:4px;background:var(--bg);overflow:hidden}
.cat-row .cbar i{display:block;height:8px;border-radius:4px;transition:width .8s ease}
.cat-row .cv{text-align:right;color:var(--sub);font-variant-numeric:tabular-nums;font-size:11.5px}
.cat-row .cp{text-align:right;font-weight:800;font-size:11.5px;color:var(--accent2);font-variant-numeric:tabular-nums}
.cat-row .cn{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* ===== 三源重点表（现已并入明细表 Tab1：紧凑 + 一屏可览） ===== */
/* 锚点偏移：定位条已改为右侧悬浮，不再占用顶部空间 */
#kpis,#charts,#reson,#hot,#detail,#sumwrap{scroll-margin-top:16px}
.btn{background:var(--accent);color:#fff;border:0;border-radius:9px;padding:7px 14px;font-size:12.5px;
  font-weight:700;cursor:pointer;font-family:inherit;transition:.2s}
.btn:hover{filter:brightness(1.1)}
.btn.ghost{background:var(--card);color:var(--txt);border:1px solid var(--line)}
.btn.ghost:hover{background:var(--hover);filter:none}
.focus-stat{font-size:11.5px;color:var(--sub);display:flex;gap:12px;flex-wrap:wrap;align-items:center}
.focus-stat b{color:var(--up)}
.tbl-compact{overflow-x:auto;overflow-y:visible;max-height:none}
.tbl-compact table{font-size:11.5px}
.tbl-compact th{padding:5px 8px;font-size:11px;letter-spacing:.2px}
.tbl-compact td{padding:3px 8px;line-height:1.3}          /* 行高约 21px → 27 行≈570px */
.tbl-compact td.clip{max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tbl-compact tr.key-row td{background:rgba(255,152,0,.11)}
.tbl-compact tr.key-row:hover td{background:rgba(255,152,0,.17)}
.tbl-compact tbody td:first-child{position:sticky;left:0;background:var(--card);z-index:1;
  border-right:1px solid var(--line)}
.tbl-compact tbody tr.key-row td:first-child{background:#fff7e8}
[data-theme="dark"] .tbl-compact tbody tr.key-row td:first-child{background:#241d10}
.tbl-compact tbody tr:hover td:first-child{background:var(--hover)}
/* 全屏查看 */
.fs-ov{position:fixed;inset:0;z-index:80;display:none;flex-direction:column;background:var(--bg)}
.fs-ov.on{display:flex}
.fs-ov .hd{display:flex;align-items:center;gap:12px;padding:11px 22px;background:var(--card);
  border-bottom:1px solid var(--line);flex-shrink:0}
.fs-ov .hd h3{font-size:14.5px;font-weight:800}
.fs-ov .hd .sp{margin-left:auto;font-size:11.5px;color:var(--sub)}
.fs-ov .bd{flex:1;overflow:auto;padding:12px 22px 22px}
.fs-ov table{font-size:12px}
.fs-ov th{top:0}
.fs-ov td{padding:5px 9px}
.fs-ov tbody td:first-child{position:sticky;left:0;background:var(--card);z-index:1}
</style>
</head>
<body data-theme="light">
<div class="wrap">
  <!-- 顶部横幅 -->
  <div class="hero">
    <button class="theme-btn" id="themeBtn">🌓 深色</button>
    <h1>🎮 端游三源周报</h1>
    <div class="sub">__SUB__</div>
    <div class="chips" id="chips"></div>
  </div>

  <!-- 右侧悬浮定位条（收起为圆点，悬停展开文字） -->
  <!-- ⚠️ 顺序必须与页面区块顺序一致，否则滚动高亮(offsetTop 单调性)会错乱 -->
  <nav class="rail" id="rail">
    <div class="rail-hd"><span class="lb">定位</span><i class="dt"></i></div>
    <a href="#kpis"><span class="lb">📊 核心指标</span><i class="dt"></i></a>
    <a href="#charts"><span class="lb">📈 数据图表</span><i class="dt"></i></a>
    <a href="#reson"><span class="lb">🔥 三源共振</span><i class="dt"></i></a>
    <a href="#hot"><span class="lb">🌐 游戏圈热点</span><i class="dt"></i></a>
    <a href="#detail"><span class="lb">📑 三源明细 · 重点表</span><i class="dt"></i></a>
    <a href="#sumwrap"><span class="lb">📌 本期总结</span><i class="dt"></i></a>
  </nav>

  <!-- 热点滚动条 -->
  <div class="hot-ticker">
    <div class="hot-label">🔥 热点速递</div>
    <div class="track"><div class="track-inner" id="ticker"></div></div>
  </div>

  <!-- KPI -->
  <div class="kpis" id="kpis"></div>

  <!-- 图表区 -->
  <div class="charts" id="charts">
    <div class="chart-card">
      <h3>📈 搜索量排行</h3>
      <div class="sub">端游聚合 Top 15（本期 9.28-10.11），右列为跨期环比</div>
      <div id="topChart"></div>
    </div>
    <div class="chart-card">
      <h3>📊 跨期对比（搜索）</h3>
      <div class="sub">Top 12 端游：本期 9.28-10.11 vs 上期 9.14-9.27，▲红涨 ▼绿跌</div>
      <div id="cmpChart"></div>
    </div>
  </div>

  <div class="charts" style="margin-top:16px">
    <div class="chart-card">
      <h3>🐳 鲸云下载排行</h3>
      <div class="sub">云游戏下载 Top 12（本期 __RANGE__ 合计，__DLSPAN__），右列为跨期环比</div>
      <div id="dlChart"></div>
    </div>
    <div class="chart-card">
      <h3>__DAILY_TITLE__</h3>
      <div class="sub">__DAILY_SUB__</div>
      <div id="dailyChart"></div>
    </div>
  </div>

  <div class="charts" style="margin-top:16px">
    <div class="chart-card">
      <h3>🟦 Steam 热度</h3>
      <div class="sub">当前在线 Top 15（10/12 快照），灰条为历史峰值参照</div>
      <div id="stChart"></div>
    </div>
    <div class="chart-card">
      <h3>🧩 端游品类分布</h3>
      <div class="sub">本期命中端游按品类聚合（款数 / 搜索量）</div>
      <div id="catChart"></div>
    </div>
  </div>

  <div class="charts" style="margin-top:16px" id="reson">
    <div class="chart-card" style="grid-column:1/-1">
      <h3>⭐ 本期三源共振速览</h3>
      <div class="sub">搜索 / 鲸云 / Steam 全维度命中的重点游戏</div>
      <div id="hotCard"></div>
    </div>
  </div>

  <!-- 联网热点 -->
  <div class="sec" id="hot">
    <h2>🌐 本期游戏圈热点 <span class="tag">联网实时 · 12 条</span></h2>
    <div class="desc" id="hotDesc"></div>
    <div class="hot-grid" id="hotGrid"></div>
  </div>

  <!-- 三源明细表（表一 = 三源关联重点表） -->
  <div class="sec" id="detail">
    <h2>📑 三源明细表 <span class="tag">核心</span></h2>
    <div class="desc">表一为三源关联重点表（搜索端跨期环比 × 鲸云下载排名 × Steam 热度交叉验证，高亮行为重点爆款）· 点击表头排序 · 输入框过滤 · 涨跌按国内习惯（红涨绿跌）</div>
    <div class="tabs" id="tabs"></div>
    <div class="toolbar">
      <input id="tq" placeholder="🔍 过滤当前表...">
      <button class="btn" id="fsBtn">⤢ 全屏查看</button>
      <div class="focus-stat" id="fsStat"></div>
    </div>
    <div class="pane active" id="p-s4"><div class="tbl-wrap tbl-compact" id="tbl-s4"></div></div>
    <div class="pane" id="p-s1"><div class="tbl-wrap" id="tbl-s1"></div></div>
    <div class="pane" id="p-s2"><div class="tbl-wrap" id="tbl-s2"></div></div>
    <div class="pane" id="p-s3"><div class="tbl-wrap" id="tbl-s3"></div></div>
  </div>

  <!-- 本期总结 -->
  <div class="sum-card" id="sumwrap">
    <h3>📌 本期总结（9.28 - 10.11）</h3>
    <div class="sum-body" id="sum"></div>
  </div>

  <div class="footer">
    __FOOT_SRC__<br>
    端游命中 <span id="f1"></span> 词 / <span id="f2"></span> 次，占搜索总量 <span id="f3"></span>%，覆盖 <span id="f4"></span> 款 · __FOOT_GEN__
  </div>
</div>

<!-- 重点表全屏查看 -->
<div class="fs-ov" id="fsOv">
  <div class="hd">
    <h3>⭐ 三源关联重点表</h3>
    <span class="sp" id="fsSp"></span>
    <button class="btn ghost" id="fsClose">✕ 关闭（Esc）</button>
  </div>
  <div class="bd"><div id="fsTbl"></div></div>
</div>

<script>
const DATA = __DATA__;
const DAILY_N = __DAILY_N__;
const HOT = __HOT__;
const SUM = __SUM__;
const COVERS = __COVERS__;
const $ = id => document.getElementById(id);
const fmt = n => (n==null||n==="") ? "—" : Number(n).toLocaleString();
const esc = s => String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
const md = s => esc(s).replace(/\*\*(.+?)\*\*/g,"<b>$1</b>");

/* ---- 顶部徽章 ---- */
(function(){
  const K = DATA.kpi;
  $("chips").innerHTML = [
    "📊 端游搜索 " + fmt(K.search_hit) + " 次 · " + (K.s_chg>0?"+":"") + K.s_chg + "%",
    "🐳 鲸云下载 " + fmt(K.dl_total) + " 次 · " + (K.dl_chg>0?"+":"") + K.dl_chg + "%",
    "🟦 Steam " + K.games_st + " 款采集",
    "🔥 端游占比 " + K.ratio + "%（上期 " + K.ratio_prev + "%）",
    "⚖️ 对比基准：上期 9.14-9.27",
  ].map(t=>'<span class="chip">'+t+'</span>').join("");
})();

/* ---- 主题 ---- */
$("themeBtn").onclick = () => {
  const d = document.body.dataset.theme === "light" ? "dark" : "light";
  document.body.dataset.theme = d;
  $("themeBtn").textContent = d === "dark" ? "☀️ 浅色" : "🌓 深色";
  drawRank(); drawCmp(); drawDl(); drawDaily(); drawSteam(); drawCat();
};

/* ---- KPI ---- */
function countUp(el, target, dur, suffix){
  const final = fmt(target) + (suffix||"");
  el.innerHTML = final;                       // 先落定，保证 rAF 不执行时也正确
  if(typeof requestAnimationFrame !== "function") return;
  const t0 = performance.now();
  function tick(t){
    const p = Math.min((t-t0)/dur, 1);
    el.innerHTML = Math.round(target * (1-Math.pow(1-p,3))).toLocaleString() + (suffix||"");
    if(p<1) requestAnimationFrame(tick); else el.innerHTML = final;
  }
  requestAnimationFrame(tick);
}
(function(){
  const K = DATA.kpi;
  const sg = (v)=> (v>0?"+":"") + v + "%";
  const cards = [
    {l:"本期搜索总量", v:K.search_total, s:" 次", c:"blue", note:"全站大盘（上期 " + fmt(K.search_total_prev) + "）"},
    {l:"端游相关搜索", v:K.search_hit, s:" 次", c:"blue", note:"占全站 " + K.ratio + "% · 跨期 " + sg(K.s_chg)},
    {l:"覆盖端游", v:K.games_s, s:" 款", c:"blue", note:"上期 " + K.games_s_prev + " 款"},
    {l:"鲸云在架", v:K.games_dl, s:" 款", c:"blue", note:"下载 " + fmt(K.dl_total) + " 次 · 跨期 " + sg(K.dl_chg)},
    {l:"Steam 采集", v:K.games_st, s:" 款", c:"blue", note:"在线 Top100 筛非网游/Demo"},
    {l:"本期黑马", txt:"战狗", c:"up", hot:"🔥", note:"WARDOGS · 峰值 42.9 万在线"},
  ];
  $("kpis").innerHTML = cards.map(c=>
    '<div class="kpi ' + c.c + '">' + (c.hot?'<span class="hot">'+c.hot+'</span>':'') +
    '<div class="lbl">' + c.l + '</div>' +
    '<div class="val" id="kv-' + c.l + '">' + (c.txt ? c.txt + ' <small>WARDOGS</small>' : '0' + (c.s||"")) + '</div>' +
    (c.note ? '<div class="note">' + c.note + '</div>' : '') + '</div>').join("");
  cards.forEach(c=>{ if(!c.txt){ countUp(document.getElementById("kv-"+c.l), c.v, 900, '<small>'+ (c.s||"") +'</small>'); } });
})();

/* ---- 热点滚动条 ---- */
(function(){
  const items = HOT.map(h=>'<span><b>'+esc(h.tag)+'</b>｜'+esc(h.title)+'</span>').join("");
  $("ticker").innerHTML = items + items;
})();

/* ---- 热点卡片（带封面主视觉：真实 Steam 主图 / 数据现画） ---- */
/* 无对应游戏图的热点，用真实数据现画一张「数据封面」，不塞空洞占位图 */
function vizDaily(){
  const D = DATA.daily, V = D.values, mx = Math.max.apply(null, V);
  return '<div class="hot-viz"><div class="vt">'+(DAILY_N>=7?'14 天逐日下载 · 周末效应':DAILY_N+' 期下载量对比')+'</div>' +
    '<div style="display:flex;align-items:flex-end;gap:3px;height:52px">' +
      V.map((v,i)=>'<i title="'+esc(D.labels[i])+' '+fmt(v)+'" style="flex:1;display:block;border-radius:2px 2px 0 0;height:'+
        Math.max(10,Math.round(v/mx*100))+'%;background:'+(v===mx?'#ffd166':'rgba(255,255,255,.5)')+'"></i>').join("") +
    '</div>' +
    '<div style="display:flex;justify-content:space-between;font-size:10px;color:rgba(255,255,255,.55)">' +
      '<span>'+esc(D.labels[0])+'</span><span>'+esc(D.labels[D.labels.length-1])+'</span></div>' +
    '<div style="display:flex;gap:12px;font-size:11.5px;color:#e8eefc">' +
      '<span>合计 <b>'+fmt(DATA.kpi.dl_total)+'</b></span>' +
      '<span>峰值 <b>'+fmt(mx)+'</b></span>' +
      '<span style="color:#ffd166">高点全在周末</span></div></div>';
}
function vizBars(v){
  const mx = Math.max.apply(null, v.rows.map(r=>Math.abs(r.v)));
  return '<div class="hot-viz"><div class="vt">'+esc(v.tt)+'</div>' +
    v.rows.map(r=>{
      const up = r.v >= 0;
      return '<div class="vrow"><span>'+esc(r.n)+'</span>' +
        '<div class="vb"><i style="width:'+Math.max(5,Math.round(Math.abs(r.v)/mx*100))+'%;background:'+
          (up?'#ffd166':'#8fa3c4')+'"></i></div>' +
        '<span style="text-align:right;font-weight:800;color:'+(up?'#ffd166':'#a9b8d0')+'">'+
          (up?'▲':'▼')+Math.abs(r.v)+'%</span></div>';
    }).join("") +
    (v.sub?'<div class="vsub">'+esc(v.sub)+'</div>':'') + '</div>';
}
(function(){
  function vizCover(h){
    const badge = '<span class="badge '+(h.cls||"")+'">'+esc(h.tag)+'</span>';
    if(h.cover4 && h.cover4.length){
      return '<div class="cov">' + badge + '<div class="cov4">' +
        h.cover4.map(k=>'<img alt="" src="'+(COVERS[k]||"")+'">').join("") + '</div></div>';
    }
    if(h.cover) return '<div class="cov">'+badge+'<img alt="" src="'+(COVERS[h.cover]||"")+'"></div>';
    if(h.viz === "daily") return '<div class="cov">'+badge+vizDaily()+'</div>';
    if(h.vizdata) return '<div class="cov">'+badge+vizBars(h.vizdata)+'</div>';
    return '<div class="cov" style="background:var(--grad)">'+badge+'</div>';
  }
  $("hotGrid").innerHTML = HOT.map(h=>
    '<div class="hot-item">' + vizCover(h) +
    '<div class="bd"><div class="tt">'+esc(h.title)+'</div>' +
    '<div class="tx">'+esc(h.desc)+'</div>' +
    '<div class="src">来源：'+esc(h.src)+'</div></div></div>').join("");
  $("hotDesc").textContent = "__SNAP__ 联网检索：Steam 畅销榜 / 新游发售 / 版本节点 / 品类退潮 / 版号审批 / 行业事件（近 14 天） · 固定 12 条 · 末两条为「版号重点」与「端游转手游独立游戏候选」 · 封面为 Steam 商店主视觉";
})();

/* ---- 细分颜色 ---- */
const PAL = ["#2563eb","#e03e3e","#12a150","#f59e0b","#8e44ad","#0891b2","#e74c3c","#0f766e"];
function chgTag(v){
  if(v==null || isNaN(v)) return '<span style="color:var(--sub)">新增</span>';
  const up = v>=0;
  return '<span class="' + (up?'up-t':'down-t') + '">' + (up?'▲':'▼') + Math.abs(v) + '%</span>';
}
function rankRows(rows, nameW, colorOf){
  const mx = Math.max.apply(null, rows.map(r=>r.v));
  return rows.map((r,i)=>{
    const w = Math.max(2, Math.round(r.v/mx*100));
    return '<div class="rrow" style="grid-template-columns:' + nameW + ' 1fr 62px 54px">' +
      '<span class="nm" title="' + esc(r.n) + '">' + (i+1) + '. ' + esc(r.n) + '</span>' +
      '<div class="bar"><i style="width:' + w + '%;background:' + colorOf(i) + '" title="' + esc(r.n) + ' ' + fmt(r.v) + '"></i></div>' +
      '<span class="vl">' + fmt(r.v) + '</span>' +
      '<span style="text-align:right;font-size:11.5px">' + chgTag(r.chg) + '</span></div>';
  }).join("");
}

/* 搜索量排行 */
function drawRank(){ $("topChart").innerHTML = rankRows(DATA.top_search, "104px", i=>PAL[i%8]); }
/* 鲸云下载排行 */
function drawDl(){ $("dlChart").innerHTML = rankRows(DATA.top_dl.slice(0,12), "128px", i=>PAL[(i+3)%8]); }

/* Steam 热度（当前在线 + 历史峰值参照） */
function drawSteam(){
  const d = DATA.top_steam, mx = Math.max.apply(null, d.map(r=>r.v));
  let h = "";
  d.forEach((r,i)=>{
    const pw = Math.max(2, Math.round(r.p/mx*100));
    const cw = Math.max(2, Math.round(r.v/mx*100));
    h += '<div class="rrow" style="grid-template-columns:140px 1fr 66px">' +
      '<span class="nm" title="' + esc(r.n) + ' / ' + esc(r.e) + '">' + (i+1) + '. ' + esc(r.n) + '</span>' +
      '<div class="bar">' +
        '<i style="position:absolute;top:0;left:0;background:var(--line);opacity:.9;width:' + pw + '%;z-index:1" title="历史峰值 ' + fmt(r.p) + '"></i>' +
        '<i style="position:absolute;top:0;left:0;background:#1e4ed8;width:' + cw + '%;z-index:2" title="当前在线 ' + fmt(r.v) + '"></i>' +
      '</div>' +
      '<span class="vl">' + fmt(r.v) + '</span></div>';
  });
  $("stChart").innerHTML = h + '<div class="legend">' +
    '<span><span class="dot" style="background:#1e4ed8"></span>当前在线（10/12）</span>' +
    '<span><span class="dot" style="background:var(--line)"></span>历史峰值</span></div>';
}

/* 跨期对比柱状图：底条=上期(9.14-9.27)，覆盖条=本期(9.28-10.11) */
function drawCmp(){
  const d = DATA.cmp, dk = document.body.dataset.theme === "dark";
  const bg = dk ? "#161d29" : "#ffffff", txtC = dk ? "#8b98a9" : "#8a94a6";
  const mx = Math.max.apply(null, d.map(r=>Math.max(r.w1,r.w2)));
  let h = "";
  d.forEach(r=>{
    const up = r.chg >= 0;
    const b1 = Math.round(r.w1/mx*100), b2 = Math.round(r.w2/mx*100);
    const c1 = dk ? "#3b4a63" : "#a8c0e0", c2 = up ? "#e03e3e" : "#12a150";
    h += '<div class="crow" style="display:grid;grid-template-columns:104px 1fr 1fr 76px;gap:8px;align-items:center;margin-bottom:8px;font-size:12px">' +
      '<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + esc(r.n) + '">' + esc(r.n) + '</span>' +
      '<div style="position:relative;height:16px;background:' + bg + ';border-radius:3px">' +
        '<div style="width:' + b2 + '%;height:16px;background:' + c1 + ';border-radius:3px;opacity:.55" title="上期 ' + fmt(r.w2) + '"></div>' +
        '<div style="position:absolute;top:0;left:0;width:' + b1 + '%;height:16px;background:' + c2 + ';border-radius:3px;opacity:.9;transition:width .8s ease" title="本期 ' + fmt(r.w1) + '"></div>' +
      '</div>' +
      '<span style="font-size:11px;color:' + txtC + '">' + fmt(r.w2) + '→' + fmt(r.w1) + '</span>' +
      '<span class="' + (up?'up-t':'down-t') + '" style="text-align:right">' + (up?'▲':'▼') + Math.abs(r.chg) + '%</span></div>';
  });
  $("cmpChart").innerHTML = h + '<div style="display:flex;gap:14px;margin-top:8px;font-size:11px;color:' + txtC + '">' +
    '<span><span class="dot" style="background:#a8c0e0"></span>上期 9.14-9.27</span>' +
    '<span><span class="dot" style="background:#e03e3e"></span>本期 9.28-10.11</span></div>';
}

/* 品类分布：真正的 SVG 环形图 + 右侧排行联动（悬停高亮对应扇区） */
const CAT_PAL = ["#2563eb","#e03e3e","#12a150","#f59e0b","#8e44ad","#0891b2","#e74c3c","#0f766e"];
function drawCat(){
  const d = DATA.cat;
  const total = d.reduce((a,b)=>a+b.s,0);
  const totN = d.reduce((a,b)=>a+b.n,0);
  const maxS = Math.max.apply(null, d.map(x=>x.s));
  const cx = 106, cy = 106, R = 100, r = 63;          // 外径 / 内径（环形）
  const pt = (a,rad) => [cx + Math.cos(a)*rad, cy + Math.sin(a)*rad];
  let a0 = -Math.PI/2, paths = "";
  d.forEach((c,i)=>{
    const frac = c.s / total;
    const a1 = a0 + frac * Math.PI * 2;
    const g = 0.016;                                   // 扇区间隙（弧度）
    const s = a0 + g/2, e = Math.max(s + 0.004, a1 - g/2);
    const large = (e - s) > Math.PI ? 1 : 0;
    const p0 = pt(s,R), p1 = pt(e,R), p2 = pt(e,r), p3 = pt(s,r);
    const dd = 'M'+p0[0].toFixed(2)+' '+p0[1].toFixed(2) +
               ' A'+R+' '+R+' 0 '+large+' 1 '+p1[0].toFixed(2)+' '+p1[1].toFixed(2) +
               ' L'+p2[0].toFixed(2)+' '+p2[1].toFixed(2) +
               ' A'+r+' '+r+' 0 '+large+' 0 '+p3[0].toFixed(2)+' '+p3[1].toFixed(2)+' Z';
    paths += '<path d="'+dd+'" fill="'+CAT_PAL[i%8]+'" data-i="'+i+'"><title>'+
             esc(c.c)+'：'+c.n+' 款 / '+fmt(c.s)+' 次（'+(frac*100).toFixed(1)+'%）</title></path>';
    a0 = a1;
  });
  const rows = d.map((c,i)=>{
    const pct = c.s/total*100;
    return '<div class="cat-row" data-i="'+i+'">' +
      '<span class="dot" style="background:'+CAT_PAL[i%8]+'"></span>' +
      '<span class="cn" title="'+esc(c.c)+'">'+esc(c.c)+'</span>' +
      '<span class="cbar"><i style="width:'+Math.max(4,Math.round(c.s/maxS*100))+'%;background:'+CAT_PAL[i%8]+'"></i></span>' +
      '<span class="cv">'+c.n+' 款 · '+fmt(c.s)+'</span>' +
      '<span class="cp">'+pct.toFixed(1)+'%</span></div>';
  }).join("");
  $("catChart").innerHTML =
    '<div class="cat-wrap">' +
      '<div class="cat-ring">' +
        '<svg viewBox="0 0 212 212">'+paths+'</svg>' +
        '<div class="mid"><div class="n">'+totN+'</div>' +
        '<div class="l">款端游 · '+fmt(total)+' 次搜索</div></div>' +
      '</div>' +
      '<div class="cat-list">'+rows+'</div>' +
    '</div>';

  // 悬停联动：环段 ↔ 排行行
  const arcs = $("catChart").querySelectorAll(".cat-ring path");
  const rws = $("catChart").querySelectorAll(".cat-row");
  function hi(i){
    for(let j=0;j<arcs.length;j++) arcs[j].classList.toggle("dim", i >= 0 && j !== i);
    for(let j=0;j<rws.length;j++) rws[j].classList.toggle("on", i >= 0 && j === i);
  }
  function bind(el, i){
    el.addEventListener("mouseenter", ()=>hi(i));
    el.addEventListener("mouseleave", ()=>hi(-1));
  }
  for(let i=0;i<arcs.length;i++) bind(arcs[i], i);
  for(let i=0;i<rws.length;i++) bind(rws[i], i);
}

/* 鲸云下载 14 天逐日趋势（SVG 折线 + 面积） */
function drawDaily(){
  const el = $("dailyChart"); if(!el) return;
  const D = DATA.daily; if(!D || !D.labels || !D.labels.length) return;
  const L = D.labels, V = D.values;
  const W = 620, H = 214, PL = 52, PR = 16, PT = 16, PB = 30;
  const mx = Math.max.apply(null, V), mn = Math.min.apply(null, V);
  const n = L.length;
  const step = n > 1 ? (W - PL - PR) / (n - 1) : 0;
  const X = i => PL + i * step;
  const Y = v => H - PB - (v / mx) * (H - PT - PB);
  const pts = V.map((v,i)=>X(i).toFixed(1) + "," + Y(v).toFixed(1)).join(" ");
  const area = "M" + X(0).toFixed(1) + "," + (H-PB) + " L" + pts.split(" ").join(" L") +
               " L" + X(n-1).toFixed(1) + "," + (H-PB) + " Z";
  let grid = "";
  for(let g=0; g<=4; g++){
    const y = PT + (H-PT-PB) * g/4, val = Math.round(mx * (1 - g/4));
    grid += '<line x1="'+PL+'" y1="'+y.toFixed(1)+'" x2="'+(W-PR)+'" y2="'+y.toFixed(1)+'" style="stroke:var(--line)" stroke-width="1"/>' +
            '<text x="'+(PL-7)+'" y="'+(y+3.5).toFixed(1)+'" text-anchor="end" font-size="10" style="fill:var(--sub)">'+fmt(val)+'</text>';
  }
  let dots = "", labs = "";
  V.forEach((v,i)=>{
    const isMax = (v===mx), isMin = (v===mn);
    dots += '<circle cx="'+X(i).toFixed(1)+'" cy="'+Y(v).toFixed(1)+'" r="'+(isMax||isMin?4:2.8)+'" fill="'+(isMax?'#e03e3e':(isMin?'#12a150':'#2563eb'))+'" stroke="#fff" stroke-width="1.5"/>';
    if(isMax||isMin) dots += '<text x="'+X(i).toFixed(1)+'" y="'+(Y(v)-9).toFixed(1)+'" text-anchor="middle" font-size="10.5" font-weight="700" fill="'+(isMax?'#e03e3e':'#12a150')+'">'+fmt(v)+'</text>';
    if(i%2===0) labs += '<text x="'+X(i).toFixed(1)+'" y="'+(H-10)+'" text-anchor="middle" font-size="10" style="fill:var(--sub)">'+esc(L[i])+'</text>';
  });
  const total = V.reduce((a,b)=>a+b,0);
  el.innerHTML =
    '<svg viewBox="0 0 '+W+' '+H+'" style="width:100%;height:auto;display:block">' +
      '<defs><linearGradient id="dg" x1="0" y1="0" x2="0" y2="1">' +
        '<stop offset="0%" stop-color="#2563eb" stop-opacity=".28"/>' +
        '<stop offset="100%" stop-color="#2563eb" stop-opacity=".02"/></linearGradient></defs>' +
      grid +
      '<path d="'+area+'" fill="url(#dg)"/>' +
      '<polyline points="'+pts+'" fill="none" stroke="#2563eb" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>' +
      dots + labs +
    '</svg>' +
    '<div style="display:flex;gap:18px;flex-wrap:wrap;margin-top:8px;font-size:11.5px;color:var(--sub)">' +
      '<span>'+(DAILY_N>=7?'14 天合计':'合计')+' <b style="color:var(--txt)">'+fmt(total)+'</b></span>' +
      '<span>'+(DAILY_N>=7?'日均':'均值')+' <b style="color:var(--txt)">'+fmt(Math.round(total/n))+'</b></span>' +
      '<span>最高 <b style="color:var(--up)">'+fmt(mx)+'</b>（'+esc(L[V.indexOf(mx)])+'）</span>' +
      '<span>最低 <b style="color:var(--down)">'+fmt(mn)+'</b>（'+esc(L[V.indexOf(mn)])+'）</span>' +
    '</div>';
}

/* 三源共振速览 */
(function(){
  function boxes(arr){
    return '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:13px">' +
      arr.map(x=>'<div style="flex:1;min-width:100px;background:rgba(224,62,62,.06);border:1px solid rgba(224,62,62,.28);border-radius:10px;padding:10px">' +
        '<div style="font-size:11px;color:var(--sub)">' + x.l + '</div>' +
        '<div style="font-size:18px;font-weight:800;color:var(--up);margin:4px 0">' + x.v + '</div>' +
        '<div style="font-size:11px;color:var(--up)">' + x.s + '</div></div>').join("") + '</div>';
  }
  $("hotCard").innerHTML =
    '<div style="font-size:12.5px;font-weight:800;margin-bottom:8px">👑 战狗 WARDOGS（appid 1867240 · 9/10 抢先体验 · 连续两周全球销量冠军）</div>' +
    boxes([
      {l:"累计销量", v:"300 万+ 套", s:"估算流水约 7000 万美元"},
      {l:"当前在线", v:"215,458", s:"Steam 实时榜第 3"},
      {l:"历史峰值", v:"428,666", s:"9/13 创下"},
    ]) +
    '<div style="font-size:12.5px;font-weight:800;margin-bottom:8px">🆕 伊莫 Aniimo（appid 4126040 · 9/16 PC 公测 · 免费捉宠 MMO）</div>' +
    boxes([
      {l:"当前在线", v:"94,009", s:"Steam 实时榜第 8"},
      {l:"上线", v:"9/16 PC", s:"移动端 9/23 · 数据互通"},
      {l:"上线方式", v:"PC + 云游戏", s:"首发即同步登陆云平台"},
    ]) +
    '<div style="font-size:12.5px;font-weight:800;margin-bottom:8px">🐟 渔力全开 How to Fish（appid 4001890 · 热度全线退潮）</div>' +
    boxes([
      {l:"当前在线", v:"9,858", s:"上周 26,223（-62%）"},
      {l:"鲸云下载", v:"8,768", s:"410 款中第 1，跨期 -57.2%"},
      {l:"历史峰值", v:"373,971", s:"8/26 创下，已跌出 Top100"},
    ]) +
    '<div style="font-size:12.5px;line-height:1.9;color:var(--sub)">🔥 <b style="color:var(--txt)">本期三核</b>：战狗（Steam 销量端最稳）、伊莫（最大变量，与鲸云同赛道）、渔力全开（云游戏存量第一但快速退潮）。其余三源共振款：遨游中国2、极限竞速地平线5、漫威蜘蛛侠2、模拟农场25、恐龙岛、黑神话悟空、人渣 SCUM。</div>';
})();

/* 三源关联重点表（紧凑单行 + 全屏一屏看全） */
const S4_COLS = ["游戏","appid","搜索端(跨期环比)","鲸云下载(排名)","Steam端(在线/峰值)","玩法标签","独立游戏","发行日期","安装大小","历史峰值","判定/说明"];
function s4Table(rows){
  return '<table><thead><tr>' + S4_COLS.map(c=>'<th>'+c+'</th>').join("") + '</tr></thead><tbody>' +
    rows.map(r=>{
      const key = String(r["判定/说明"]||"").indexOf("🔥") === 0;
      return '<tr' + (key?' class="key-row"':'') + '>' +
        S4_COLS.map(c=>{
          const v = r[c];
          if(c === "游戏") return '<td><b>'+esc(v)+'</b></td>';
          if(c === "搜索端(跨期环比)" || c === "鲸云下载(排名)"){
            const s = String(v==null?"":v);
            let cls = "";
            if(/\+/.test(s) && /\d/.test(s)) cls = "up-t";
            else if(/-/.test(s) && /\d/.test(s)) cls = "down-t";
            return '<td class="'+cls+'">'+esc(v)+'</td>';
          }
          if(c === "独立游戏" && (v==="是"||v==="否"))
            return '<td><span class="pill '+(v==="是"?"ok":"no")+'">'+esc(v)+'</span></td>';
          if(c === "判定/说明" || c === "玩法标签")          // 单行省略，悬停看全文
            return '<td class="clip" title="'+esc(v)+'">'+esc(v)+'</td>';
          return '<td>'+esc(v)+'</td>';
        }).join("") + '</tr>';
    }).join("") + '</tbody></table>';
}
function keyCount(){ return DATA.s4.filter(r=>String(r["判定/说明"]||"").indexOf("🔥")===0).length; }
/* 重点表渲染（Tab1）：清空输入框后调用 / 由 renderTable("s4") 统一入口 */
function renderS4(){
  const st = STATE.s4 || {q:""};
  let rows = DATA.s4;
  if(st.q) rows = rows.filter(r=>JSON.stringify(r).toLowerCase().indexOf(st.q.toLowerCase()) >= 0);
  // 内联表不额外加统计行（计数已在工具条 focus-stat 中），保证 27 行能压进一屏
  $("tbl-s4").innerHTML = s4Table(rows);
  $("fsTbl").innerHTML = s4Table(rows) + '<div class="cnt">共 '+rows.length+' 款 · 悬停单元格看全文</div>';
  $("fsSp").textContent = '全 ' + DATA.s4.length + ' 款 · 当前显示 ' + rows.length + ' 款';
  $("fsStat").innerHTML = '<span>共 <b>' + DATA.s4.length + '</b> 款</span>' +
    '<span>🔥 重点 <b>' + keyCount() + '</b> 款</span>' +
    (st.q ? '<span>筛出 <b>' + rows.length + '</b> 款</span>' : '');
}
/* 全屏：一屏看全 27 行 */
$("fsBtn").onclick = () => { $("fsOv").classList.add("on"); $("fsClose").focus(); };
$("fsClose").onclick = () => { $("fsOv").classList.remove("on"); };
document.addEventListener("keydown", e => { if(e.key === "Escape") $("fsOv").classList.remove("on"); });

/* 右侧悬浮定位条：滚动高亮 */
(function(){
  const links = [].slice.call(document.querySelectorAll("#rail a"));
  const secs = links.map(a=>document.querySelector(a.getAttribute("href")));
  function spy(){
    const y = (window.pageYOffset || 0) + 140;
    let cur = -1;                                   // 未进入任何区块 → 不高亮（避免顶部长亮第一项）
    secs.forEach((s,i)=>{ if(s && (s.offsetTop || 0) <= y) cur = i; });
    // 滚到底时锁定最后一项（末块高度不足时其 offsetTop 可能永远到不了）
    if((window.innerHeight + (window.pageYOffset || 0)) >= (document.documentElement.scrollHeight || 0) - 4)
      cur = links.length - 1;
    links.forEach((a,i)=>a.classList.toggle("on", i === cur));
  }
  window.addEventListener("scroll", spy, {passive:true});
  spy();
})();

/* 三源明细表（表一 = 三源关联重点表，列定义复用上方 S4_COLS） */
const TABLES = {
  s4: {cols: S4_COLS, num:[], label:"⭐ 三源关联重点表"},
  s1: {cols: DATA.KW.s1, num:[1,2,3,5], label:"① 搜索关键词源"},
  s2: {cols: DATA.KW.s2, num:[1,2,3],   label:"② 鲸云源"},
  s3: {cols: DATA.KW.s3, num:[9,10,11], label:"③ Steam源"},
};
/* 重点表不支持排序（值形如「第8(9,858)」，排序无意义），保持源次序 */
const SORT = {s4:null, s1:{k:1,d:-1}, s2:{k:1,d:-1}, s3:{k:9,d:-1}};
const STATE = {s4:{q:""}, s1:{q:""}, s2:{q:""}, s3:{q:""}};
const TAB_ORDER = ["s4","s1","s2","s3"];

$("tabs").innerHTML = TAB_ORDER.map((k,i)=>
  '<div class="tab ' + (i===0?'active':'') + '" data-t="' + k + '">' + TABLES[k].label + '（' + DATA[k].length + '）</div>').join("");

/* 全屏按钮 / 统计只在重点表 Tab 显示 */
function syncFsTools(){
  const cur = document.querySelector("#tabs .tab.active").dataset.t;
  const on = (cur === "s4");
  $("fsBtn").style.display = on ? "" : "none";
  $("fsStat").style.display = on ? "" : "none";
}

function cellRender(c, v, isNum){
  if(isNum && v!=="" && v!=null && !isNaN(parseFloat(String(v).replace(/,/g,""))))
    return '<td class="num">' + fmt(parseFloat(String(v).replace(/,/g,""))) + '</td>';
  if(c.indexOf("环比")>=0){
    const s = String(v==null?"":v);
    if(/^\+/.test(s)) return '<td class="up-t">' + esc(s) + '</td>';
    if(/^-/.test(s)) return '<td class="down-t">' + esc(s) + '</td>';
    return '<td style="color:var(--sub)">' + esc(s) + '</td>';
  }
  if((c==="独立游戏"||c==="近一年内上线") && (v==="是"||v==="否"))
    return '<td><span class="pill ' + (v==="是"?"ok":"no") + '">' + esc(v) + '</span></td>';
  if(c==="代表性搜索词"||c==="玩法标签"||c==="备注")
    return '<td style="white-space:normal;min-width:220px">' + esc(v) + '</td>';
  return '<td>' + esc(v) + '</td>';
}

function renderTable(key){
  if(key === "s4"){ renderS4(); return; }        // 重点表走专用渲染（列型特殊）
  const cfg = TABLES[key], st = STATE[key];
  let rows = DATA[key].filter(r=>!st.q || JSON.stringify(r).toLowerCase().indexOf(st.q.toLowerCase())>=0);
  if(SORT[key]) rows = rows.slice().sort((a,b)=>{
    const k = cfg.cols[SORT[key].k];
    const va = a[k], vb = b[k];
    const na = parseFloat(String(va).replace(/,/g,"")), nb = parseFloat(String(vb).replace(/,/g,""));
    if(!isNaN(na) && !isNaN(nb)) return (na-nb)*SORT[key].d;
    return String(va).localeCompare(String(vb))*SORT[key].d;
  });
  $("tbl-"+key).innerHTML = '<table><thead><tr>' + cfg.cols.map((c,i)=>
    '<th data-k="' + key + '" data-i="' + i + '">' + c + (SORT[key] && SORT[key].k===i ? (SORT[key].d<0?' ▼':' ▲') : '') + '</th>').join("") +
    '</tr></thead><tbody>' + rows.map(r=>{
      const first = String(r[cfg.cols[0]]||"");
      const rowCls = (first==="渔力全开"||first==="战狗") ? ' class="key-row"' : "";
      return '<tr' + rowCls + '>' + cfg.cols.map((c,i)=>cellRender(c, r[c], cfg.num.indexOf(i)>=0)).join("") + '</tr>';
    }).join("") + '</tbody></table><div class="cnt">共 ' + rows.length + ' 条</div>';
  bindTh();
}
function bindTh(){
  const ths = document.querySelectorAll("th[data-k]");
  for(let i=0;i<ths.length;i++){
    const th = ths[i];
    if(th.dataset.bound) continue;
    th.dataset.bound = "1";
    th.addEventListener("click", ()=>{
      const k = th.dataset.k, idx = parseInt(th.dataset.i);
      if(!SORT[k]) return;
      if(SORT[k].k===idx) SORT[k].d *= -1; else SORT[k] = {k:idx, d:-1};
      renderTable(k);
    });
  }
}
document.querySelectorAll("#tabs .tab").forEach(t=>t.onclick=()=>{
  document.querySelectorAll("#tabs .tab").forEach(x=>x.classList.remove("active"));
  t.classList.add("active");
  document.querySelectorAll(".pane").forEach(p=>p.classList.remove("active"));
  $("p-"+t.dataset.t).classList.add("active");
  $("tq").value = ""; STATE[t.dataset.t] = {q:""};
  syncFsTools();
  renderTable(t.dataset.t);
});
$("tq").oninput = e => {
  const cur = document.querySelector("#tabs .tab.active").dataset.t;
  STATE[cur].q = e.target.value.trim(); renderTable(cur);
};

/* 总结 */
(function(){
  const num = ["①","②","③","④","⑤","⑥"];
  $("sum").innerHTML = SUM.map((item,i)=>
    '<p><b>' + (num[i]||"·") + ' ' + esc(item[0]) + '：</b>' + md(item[1]) + '</p>').join("");
})();

/* 页脚 */
(function(){
  const K = DATA.kpi;
  const kw = DATA.s1.reduce((a,b)=>a+(b["关键词数"]||0),0);
  $("f1").textContent = fmt(kw); $("f2").textContent = fmt(K.search_hit);
  $("f3").textContent = K.ratio; $("f4").textContent = K.games_s;
})();

/* init */
drawRank(); drawCmp(); drawDl(); drawDaily(); drawSteam(); drawCat();
syncFsTools();
TAB_ORDER.forEach(renderTable);
</script>
</body>
</html>"""

html = (HTML.replace("__DATA__", payload).replace("__HOT__", hot_json)
            .replace("__SUM__", sum_json).replace("__COVERS__", cov_json)
            .replace("__TITLE__", TITLE).replace("__SUB__", SUB)
            .replace("__SNAP__", _snap)
            .replace("__RANGE__", _range).replace("__DLSPAN__", DL_SPAN)
            .replace("__DAILY_TITLE__", DAILY_TITLE).replace("__DAILY_SUB__", DAILY_SUB)
            .replace("__FOOT_SRC__", FOOT_SRC).replace("__FOOT_GEN__", FOOT_GEN)
            .replace("__DAILY_N__", str(DAILY_N)))
# 草稿态打标：08 门禁据此拒收，人打开源码也一眼能看出
if _need:
    html = html.replace('<body data-theme="light">',
                        '<body data-theme="light" data-draft="%d">' % len(_need), 1)
open(OUT, "w", encoding="utf-8").write(html)
print("OK HTML: %s  %.0f KB" % (OUT, len(html)/1024))
print("热门来源: %s%s" % (HOT_SRC, "  ⚠️ 草稿态（%d 条待人工）" % len(_need) if _need else ""))
