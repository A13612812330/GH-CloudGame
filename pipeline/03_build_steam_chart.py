# -*- coding: utf-8 -*-
# ============================================================================
# 端游周报流水线 · 步骤 03：SteamDB 在线榜 → 筛非网游 + 合并历史元数据
# 用法：python 03_build_steam_chart.py
# ----------------------------------------------------------------------------
# 每次新一周需要改的配置（见本文件顶部 CONFIG 区）：
#   1) SRC_SEARCH / SRC_DL  —— 明说输入文件名（可带日期前缀）
#   2) OUT_* / RUN_DATE     —— 输出文件名与快照日期
#   3) 03 的 CHART 数组     —— 从 steamdb.info/charts/ 重新抓取的 Top100
#   4) 04 的 PATCH          —— 新增游戏的人工补齐元数据（SteamDB 单页实抓）
# 全套顺序：00 → 01 → 02 → 03 → 04 → 05 → 06
# ============================================================================
"""SteamDB 2026-10-12 在线 Top100 → 端游筛选 + 与历史元数据合并"""
import json, sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cfg import CFG  # noqa: E402

# rank, 名称, appid, 当前在线, 24h峰值, 历史峰值
CHART = [
    (1, "Counter-Strike 2", 730, 526257, 1404227, 1862531),
    (2, "Dota 2", 570, 486956, 1034493, 1295114),
    (3, "PUBG: BATTLEGROUNDS", 578080, 255068, 713683, 3257248),
    (4, "AION 2", 3393110, 211429, 392300, 397905),
    (5, "Bongo Cat", 3419430, 154090, 186709, 194508),
    (6, "Apex Legends", 1172470, 89526, 233682, 624473),
    (7, "Deadlock", 1422450, 88434, 220575, 262145),
    (8, "FiveM", 2676230, 75979, 203101, 221685),
    (9, "Wallpaper Engine", 431960, 69263, 118092, 150375),
    (10, "WARDOGS", 1867240, 67901, 199487, 428666),
    (11, "ARC Raiders", 1808500, 63038, 185443, 481966),
    (12, "Delta Force", 2507950, 62094, 135722, 247028),
    (13, "TBH: Task Bar Hero", 3678970, 59964, 71156, 546130),
    (14, "Team Fortress 2", 440, 59717, 84627, 253997),
    (15, "Valheim", 892970, 52375, 189547, 502387),
    (16, "Rust", 252490, 49751, 122967, 262284),
    (17, "Slay the Spire 2", 2868840, 48540, 102550, 574638),
    (18, "Overwatch", 2357570, 46404, 90004, 165651),
    (19, "Warframe", 230410, 45819, 78597, 189837),
    (20, "Deskrawl: Idle ARPG", 4623570, 44291, 47728, 48222),
    (21, "VRChat", 438100, 44013, 60544, 79593),
    (22, "Stardew Valley", 413150, 39548, 105300, 236614),
    (23, "Aniimo", 4126040, 39212, 78003, 168260),
    (24, "The Witcher 3: Wild Hunt Remastered", 292030, 38101, 121041, 137724),
    (25, "Marvel Rivals", 2767030, 37045, 79953, 644269),
    (26, "Project Zomboid", 108600, 35761, 82545, 124995),
    (27, "Palworld", 1623730, 34497, 77274, 2101867),
    (28, "Tom Clancy's Rainbow Six Siege", 359550, 32996, 93174, 201933),
    (29, "Grand Theft Auto V Enhanced", 3240220, 31944, 78748, 187059),
    (30, "Grand Theft Auto V Legacy", 271590, 31333, 80147, 364548),
    (31, "War Thunder", 236390, 30884, 91100, 125430),
    (32, "Limbus Company", 1973530, 30617, 50898, 157444),
    (33, "Dead by Daylight", 381210, 30581, 70739, 170073),
    (34, "The Binding of Isaac: Rebirth", 250900, 29553, 70742, 156156),
    (35, "Total War: WARHAMMER III", 1142710, 29374, 77600, 166754),
    (36, "UBERMOSH:OMEGA", 1181000, 27604, 174886, 174886),
    (37, "Geometry Dash", 322170, 27396, 80736, 109993),
    (38, "PAYDAY 2", 218620, 26884, 34119, 247709),
    (39, "Dragon's Dogma 2", 2054970, 25950, 47583, 228585),
    (40, "Baldur's Gate 3", 1086940, 25205, 68983, 875343),
    (41, "Cyberpunk 2077", 1091500, 24959, 61902, 1054388),
    (42, "Terraria", 105600, 23698, 60831, 489886),
    (43, "NARAKA: BLADEPOINT", 1203220, 23271, 74231, 385770),
    (44, "Crosshair X", 1366800, 23041, 43505, 89033),
    (45, "Monster Hunter Wilds", 2246340, 22870, 48231, 1384608),
    (46, "HELLDIVERS 2", 553850, 22636, 60022, 458709),
    (47, "[WoG] War of Genesis: Idle Loot", 4891320, 21973, 22540, 52835),
    (48, "Hearts of Iron IV", 394360, 21775, 60610, 93196),
    (49, "Don't Starve Together", 322330, 21367, 54658, 122662),
    (50, "EA SPORTS FC 27", 4080220, 21318, 87490, 96232),
    (51, "RimWorld", 294100, 21258, 39466, 96040),
    (52, "Red Dead Redemption 2", 1174180, 21235, 53741, 99993),
    (53, "Sid Meier's Civilization VI", 289070, 21196, 46919, 162657),
    (54, "Escape from Tarkov", 3932890, 20551, 42361, 47800),
    (55, "Risk of Rain 2", 632360, 20518, 46161, 75406),
    (56, "The Elder Scrolls V: Skyrim Special Edition", 489830, 19591, 46575, 69906),
    (57, "Spacewar", 480, 18901, 61583, 138416),
    (58, "Destiny 2", 1085660, 18568, 41119, 316750),
    (59, "DayZ", 221100, 18536, 52839, 78937),
    (60, "Street Fighter 6", 1364780, 18181, 37041, 72977),
    (61, "7 Days to Die", 251570, 18174, 42965, 125419),
    (62, "The Outlast Trials", 1304930, 17925, 109006, 147955),
    (63, "ARK: Survival Ascended", 2399830, 17793, 33997, 98047),
    (64, "Left 4 Dead 2", 550, 17692, 45821, 162399),
    (65, "ELDEN RING", 1245620, 17454, 40686, 953426),
    (66, "Mount & Blade II: Bannerlord", 261550, 17293, 42781, 248216),
    (67, "ACE COMBAT 8: WINGS OF THEVE", 2288340, 16599, 29681, 52694),
    (68, "Dressmaker", 4019220, 16340, 40738, 43298),
    (69, "OBS Studio", 1905180, 15715, 31387, 34641),
    (70, "Black Desert", 582660, 15666, 21472, 60395),
    (71, "tModLoader", 1281930, 15397, 39081, 79101),
    (72, "Battlefield 6", 2807960, 14847, 45793, 747440),
    (73, "Arena Breakout: Infinite", 2073620, 14781, 40386, 66007),
    (74, "The Sims 4", 1222670, 14623, 35042, 96328),
    (75, "Football Manager 26", 3551340, 14372, 36301, 84909),
    (76, "Core Keeper", 1621690, 14248, 29132, 46465),
    (77, "Euro Truck Simulator 2", 227300, 14219, 58618, 73887),
    (78, "Crusader Kings III", 1158310, 13984, 34465, 98872),
    (79, "Farming Simulator 25", 2300320, 13644, 60380, 135970),
    (80, "Call of Duty", 1938090, 13576, 41386, 491670),
    (81, "Path of Exile 2", 2694490, 13516, 30095, 578569),
    (82, "Character House -Desktop Companion- Demo", 5166840, 13477, 19802, 29788),
    (83, "ELDEN RING NIGHTREIGN", 2622380, 13453, 30896, 313593),
    (84, "The Isle", 376210, 13392, 26429, 27965),
    (85, "EA SPORTS FC 26", 3405690, 13387, 38781, 160728),
    (86, "Diablo IV", 2344520, 13271, 28031, 64518),
    (87, "World of Warships", 552990, 13065, 21397, 411338),
    (88, "Garry's Mod", 4000, 12837, 36857, 73863),
    (89, "Yu-Gi-Oh! Master Duel", 1449850, 12545, 20938, 262689),
    (90, "Russian Fishing 4", 766570, 12418, 23908, 28073),
    (91, "Monster Hunter: World", 582010, 12292, 31399, 334684),
    (92, "Once Human", 2139460, 12235, 23004, 231668),
    (93, "Age of Empires II: Definitive Edition", 813780, 11806, 29152, 38725),
    (94, "Warhammer 40,000: Space Marine 2", 2183900, 11572, 31552, 225690),
    (95, "MONSTER HUNTER RISE", 1446780, 11539, 28289, 231360),
    (96, "MapleStory", 216150, 11381, 14038, 17750),
    (97, "Probably Stolen Demo", 4349200, 11242, 19816, 19816),
    (98, "Artifact Classic", 583950, 11236, 11255, 60646),
    (99, "Blender", 365670, 11179, 15841, 16774),
    (100, "MIR4", 1623660, 11115, 12062, 97173),
]

# 常青网游 / 服务型 / 工具 —— 排除
EXCL_NET = {
    730, 570, 578080, 2676230, 2767030, 2357570, 359550, 1172470, 1422450, 440,
    230410, 381210, 2694490, 438100, 4080220, 3405690, 2507950, 236390, 2807960,
    1938090, 39210, 2139460, 1808500, 1085660, 252950, 1449850, 1665460, 582660,
    1623660, 2073620, 3932890, 2073850, 311210, 594650, 583950, 1476970, 4356430,
    4891320, 252490,                       # Rust：多人服务型生存
    1203220,                               # NARAKA：吃鸡，网游
    1172710,                               # Dune: Awakening：持久世界生存 MMO
    2344520,                               # Diablo IV：在线 ARPG（强制联网服务型）
    5166840,                               # 角色屋桌面伙伴 Demo：App Type = Demo，非正式发行
    480, 431960, 1366800, 1905180,         # 非游戏工具（Spacewar/Wallpaper Engine/Crosshair X/OBS）
    3393110,                               # AION 2：MMORPG
    552990,                                # World of Warships：海战 MMO
    216150,                                # MapleStory：MMORPG
    365670,                                # Blender：非游戏工具
    4349200,                               # Probably Stolen Demo：App Type = Demo
}
# 新爆款多人游戏保留（市场信号价值高），但标注类型
NEW_HOT = {1867240, 4126040}

rows = []
for rk, name, appid, cur, p24, peak in CHART:
    rows.append(dict(rank=rk, name=name, appid=str(appid), cur=cur, h24=p24, peak=peak,
                     excluded=appid in EXCL_NET, newhot=appid in NEW_HOT))

dfc = pd.DataFrame(rows)
_meta_p = CFG.tmp / "steam_meta.json"
meta = json.loads(_meta_p.read_text(encoding="utf-8")) if _meta_p.is_file() else {}

missing = [r["name"] for _, r in dfc[~dfc["excluded"]].iterrows() if r["appid"] not in meta]
print(f"Top100 中端游候选 {len(dfc[~dfc['excluded']])} 款")
print(f"历史元数据缺失 {len(missing)} 款：")
for m in missing:
    print("   -", m)
dfc.to_csv(CFG.tmp / "chart.csv", index=False, encoding="utf-8-sig")
