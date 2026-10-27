# -*- coding: utf-8 -*-
# ============================================================================
# 端游周报流水线 · 步骤 03：SteamDB 在线榜 → 筛非网游 + 合并历史元数据
# 用法：python 03_build_steam_chart.py
# ----------------------------------------------------------------------------
# 每次新一周需要改的配置（见本文件顶部 CONFIG 区）：
#   1) SRC_SEARCH / SRC_DL  —— 明说输入文件名（可带日期前缀）
#   2) OUT_* / RUN_DATE     —— 输出文件名与快照日期
#   3) 03 的 CHART 数组     —— 本期用 Steam 官方接口快照（见 .tmp_r10/_fetch_steam.py），
#                              榜单 GetMostPlayedGames + 逐款 GetNumberOfCurrentPlayers
#   4) 04 的 PATCH          —— 新增游戏的人工补齐元数据（SteamDB 单页实抓）
# 全套顺序：00 → 01 → 02 → 03 → 04 → 05 → 06
# ============================================================================
"""Steam SteamTop100 2026-10-27 快照 → 端游筛选 + 与历史元数据合并"""
import json, sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cfg import CFG  # noqa: E402

# rank, 名称, appid, 当前在线, 24h峰值, 历史峰值
CHART = [
    (1, "Counter-Strike 2", 730, 447017, 1064089, 1862531),
    (2, "Dota 2", 570, 613202, 1046553, 1295114),
    (3, "PUBG: BATTLEGROUNDS", 578080, 149859, 718899, 3257248),
    (4, "Wallpaper Engine", 431960, 54570, 110819, 150375),
    (5, "Deadlock", 1422450, 0, 227394, 262145),
    (6, "Call of Duty®", 1938090, 156237, 180256, 491670),
    (7, "Cyberpunk 2077", 1091500, 115436, 149474, 1054388),
    (8, "Apex Legends™", 1172470, 53482, 195480, 624473),
    (9, "AION 2", 3393110, 155481, 221438, 397905),
    (10, "HELLDIVERS 2", 553850, 54584, 62517, 458709),
    (11, "WARDOGS", 1867240, 107765, 152709, 428666),
    (12, "Grand Theft Auto V", 271590, 26248, 67829, 364548),
    (13, "FiveM", 2676230, 119392, 178505, 221685),
    (14, "Slay the Spire 2", 2868840, 53312, 88852, 574638),
    (15, "Geometry Dash", 322170, 38753, 57495, 109993),
    (16, "War Thunder", 236390, 32263, 78743, 125430),
    (17, "Tom Clancy's Rainbow Six Siege", 359550, 64129, 77181, 201933),
    (18, "Dead by Daylight", 381210, 43375, 60119, 170073),
    (19, "Overwatch®", 2357570, 56824, 62305, 165651),
    (20, "Warframe", 230410, 55122, 79806, 189837),
    (21, "The Binding of Isaac: Rebirth", 250900, 30010, 55530, 156156),
    (22, "Valheim", 892970, 63124, 93643, 502387),
    (23, "Stardew Valley", 413150, 39514, 81673, 236614),
    (24, "Marvel Rivals", 2767030, 55765, 62930, 644269),
    (25, "ARC Raiders", 1808500, 62253, 81903, 481966),
    (26, "Team Fortress 2", 440, 70188, 92241, 253997),
    (27, "Limbus Company", 1973530, 21583, 37503, 157444),
    (28, "Battlefield™ 6", 2807960, 27280, 39554, 747440),
    (29, "Rust", 252490, 55436, 113830, 262284),
    (30, "Terraria", 105600, 20960, 43476, 489886),
    (31, "Grand Theft Auto V Enhanced", 3240220, 27543, 61359, 187059),
    (32, "Delta Force", 2507950, 34477, 108785, 247028),
    (33, "Enshrouded", 1203620, 52508, 88034, 88034),
    (34, "The Witcher 3: Wild Hunt Remastered", 292030, 24273, 53240, 137724),
    (35, "BeamNG.drive", 284160, 19070, 36494, 47424),
    (36, "Left 4 Dead 2", 550, 30173, 36571, 162399),
    (37, "Euro Truck Simulator 2", 227300, 11266, 43781, 73887),
    (38, "Project Zomboid", 108600, 40441, 50383, 124995),
    (39, "Don't Starve Together", 322330, 17731, 59921, 122662),
    (40, "VRChat", 438100, 44413, 55095, 79593),
    (41, "EA SPORTS FC™ 27", 4080220, 29125, 64140, 96232),
    (42, "Aniimo", 4126040, 28564, 41167, 168260),
    (43, "Red Dead Redemption 2", 1174180, 21257, 38328, 99993),
    (44, "Baldur's Gate 3", 1086940, 36944, 45872, 875343),
    (45, "NARAKA: BLADEPOINT", 1203220, 9313, 61480, 385770),
    (46, "Hearts of Iron IV", 394360, 19764, 43489, 93196),
    (47, "EA SPORTS FC™ 26", 3405690, 18388, 28388, 160728),
    (48, "Rocket League®", 252950, 21357, 30448, 30448),
    (49, "Total War: WARHAMMER III", 1142710, 25003, 42809, 166754),
    (50, "Garry's Mod", 4000, 17981, 30385, 73863),
    (51, "Yu-Gi-Oh! Master Duel", 1449850, 10892, 22076, 262689),
    (52, "R.E.P.O.", 3241660, 13190, 21364, 271571),
    (53, "The Outlast Trials", 1304930, 12545, 34304, 147955),
    (54, "Palworld", 1623730, 27111, 50288, 2101867),
    (55, "Skyrim Special Edition", 489830, 26016, 32973, 69906),
    (56, "Street Fighter 6", 1364780, 10082, 36506, 72977),
    (57, "Bongo Cat", 3419430, 138727, 164010, 194508),
    (58, "Unknown 1665460 (delisted)", 1665460, 13634, 18604, 18604),
    (59, "PEAK", 3527290, 16222, 20012, 170759),
    (60, "TBH: Task Bar Hero", 3678970, 25229, 77248, 546130),
    (61, "DayZ", 221100, 30100, 56098, 78937),
    (62, "ELDEN RING", 1245620, 19287, 28711, 953426),
    (63, "THE FINALS", 2073850, 21493, 26030, 26030),
    (64, "Moon Sweepers", 5335510, 44301, 51686, 51686),
    (65, "OBS Studio", 1905180, 13128, 28925, 34641),
    (66, "Farming Simulator 25", 2300320, 14896, 48835, 135970),
    (67, "tModLoader", 1281930, 12103, 32277, 79101),
    (68, "The Sims 4", 1222670, 18801, 30435, 96328),
    (69, "Forza Horizon 6", 2483190, 7315, 15452, 302645),
    (70, "RimWorld", 294100, 25346, 38046, 96040),
    (71, "Sid Meier's Civilization VI", 289070, 20439, 35629, 162657),
    (72, "Wuthering Waves", 3513350, 6930, 13026, 13026),
    (73, "Once Human", 2139460, 23865, 36337, 231668),
    (74, "Destiny 2", 1085660, 29169, 33299, 316750),
    (75, "Dressmaker", 4019220, 22106, 24920, 43298),
    (76, "Crosshair X", 1366800, 26894, 37220, 89033),
    (77, "Monster Hunter Wilds", 2246340, 8633, 31678, 1384608),
    (78, "Arena Breakout: Infinite", 2073620, 15665, 32187, 66007),
    (79, "Phasmophobia", 739630, 12064, 16485, 16485),
    (80, "Brawlhalla", 291550, 10105, 12612, 12612),
    (81, "FINAL FANTASY RESONANCE", 3259780, 24374, 33036, 33036),
    (82, "Risk of Rain 2", 632360, 16146, 19004, 75406),
    (83, "Aimlabs", 714010, 2851, 7278, 7278),
    (84, "Age of Empires II: DE", 813780, 15802, 21546, 38725),
    (85, "Mount & Blade II: Bannerlord", 261550, 13852, 31162, 248216),
    (86, "Assetto Corsa", 244210, 6469, 12745, 12745),
    (87, "Warhammer 40,000: Space Marine 2", 2183900, 10163, 17364, 225690),
    (88, "7 Days to Die", 251570, 15525, 27634, 125419),
    (89, "Hunt: Showdown 1896", 594650, 8762, 23787, 23787),
    (90, "Zenless Zone Zero", 4162040, 7106, 10622, 10622),
    (91, "Bloons TD 6", 960090, 8786, 10932, 10932),
    (92, "Crusader Kings III", 1158310, 14176, 21814, 98872),
    (93, "雀魂麻將(MahjongSoul)", 1329410, 4144, 13800, 13800),
    (94, "Resident Evil 4", 2050650, 8360, 15458, 15458),
    (95, "How to Fish", 4001890, 5015, 12847, 341691),
    (96, "Among Us", 945360, 6179, 8575, 8575),
    (97, "Umamusume: Pretty Derby", 3224770, 7502, 10191, 10191),
    (98, "Escape from Tarkov", 3932890, 13730, 34066, 47800),
    (99, "Balatro", 2379780, 7590, 8396, 8396),
    (100, "Fallout 4", 377160, 13302, 16203, 16203),
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
    # ---- 2026-10-27 本期新增排除（均按 Steam 商店页取证，见 .tmp_r10/_new15_meta.json）----
    3513350,                               # Wuthering Waves 鸣潮：F2P 抽卡、跨端手游，GaaS
    4162040,                               # Zenless Zone Zero 绝区零：F2P 抽卡、跨端手游，GaaS
    1329410,                               # 雀魂麻將 MahjongSoul：F2P 网游，Cross-Platform
    3224770,                               # Umamusume: Pretty Derby：F2P 抽卡，DMM/手游跨端
    291550,                                # Brawlhalla：F2P 在线竞技，服务型
    714010,                                # Aimlabs：非游戏工具（练枪/瞄准训练）
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
