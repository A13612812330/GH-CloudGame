# -*- coding: utf-8 -*-
# ============================================================================
# 端游周报流水线 · 步骤 04b：生成「本期游戏圈热点」的封面主视觉
# ----------------------------------------------------------------------------
# 策略：真实封面优先（Steam CDN header.jpg）→ 商店页 og:image → 均失败才程序化生成。
#   实测（2026-09-28）：**并非所有新游都 404**——Steam 会在新游上线一段时间后把
#   header.jpg 同步到老 CDN。本轮 Slay the Spire 2 / Bongo Cat / RimWorld 老 CDN 直接命中
#   （real-cdn），只有更晚的新游（战狗/伊莫/渔力全开/守墓人2/Dressmaker/符文世界/控制：共振）
#   走了商店页 og:image 的新 CDN `shared.cdn.queniuqe.com`。
#   所以**不要预先判定某款要走兜底**，一律先 fetch 再看返回来源标记。
# 产出：<TMP>/covers.json  {key: "data:image/jpeg;base64,..."}
# 用法：python 04b_make_covers.py
# ----------------------------------------------------------------------------
# 封面 key 与 HOT 的对应关系（⛔ 热点固定 12 条，见 05_gen_board.py 顶部规范）：
#   常规 10 条 → spider2 / horizon5 / howtofish / aion2 / bongocat（单图）
#                + 4 条用 vizdata / viz:"daily" 拿真实数据现画
#   第 11 条 版号重点 → license（**无 steam 字段**，纯程序化信息图）
#   第 12 条 移植候选 → sts2 / tbh / bongocat / rimworld（cover4 拼贴）
# ============================================================================
"""热点封面主视觉生成（真实抓取优先 + 程序化兜底）"""
import json, os, re, sys, base64, io, urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cfg import CFG  # noqa: E402  统一配置（路径只从 config.json 来）

TMP = str(CFG.tmp)
OUT = str(CFG.tmp / "covers.json")
W, H = 480, 270                      # 16:9（与卡片封面容器同比例，零裁切）
CDN = "https://cdn.cloudflare.steamstatic.com/steam/apps/%s/header.jpg"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

FONT_BD = "C:/Windows/Fonts/msyhbd.ttc"
FONT_RG = "C:/Windows/Fonts/msyh.ttc"
def font(size, bold=True):
    for p in ([FONT_BD] if bold else []) + [FONT_RG]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

# ---------------------------------------------------------------------------
# 封面定义：c1/c2/c3 三段渐变；glow 光斑色；tag 左上角胶囊；en/cn 主副标题；
#           big/bigsub 底部关键数字
# ---------------------------------------------------------------------------
COVERS = {
    "spider2": dict(
        steam="2651280",
        en="Marvel's Spider-Man 2", cn="漫威蜘蛛侠2 · 鲸云下载榜第 1",
        tag="下载冠军 · 跨期 +278.4%",
        big="+278.4%", bigsub="鲸云下载 8,212（第 1）· 搜索端同步 +216.4%",
        c1=(12,18,46), c2=(162,34,44), c3=(244,132,108), glow=(255,150,120)),
    "horizon5": dict(
        steam="1551360",
        en="Forza Horizon 5", cn="极限竞速：地平线5 · 拟真驾驶红利",
        tag="品类红利 · 搜索 +128.0%",
        big="+110.1%", bigsub="鲸云下载 5,014（第 4）· 同系列《地平线6》+125.6%",
        c1=(26,12,40), c2=(176,58,120), c3=(252,168,120), glow=(255,180,130)),
    "howtofish": dict(
        steam="4001890",
        en="How to Fish", cn="渔力全开 · 由双源第 1 退至下载第 3",
        tag="退潮预警 · 跑输大盘 86pp",
        big="-39.5%", bigsub="鲸云下载 5,305（大盘 +46.0%）· 已跌出在线 Top100",
        c1=(18,26,38), c2=(46,62,86), c3=(122,140,166), glow=(130,150,180)),
    "aion2": dict(
        steam="3393110",
        en="AION 2", cn="永恒之塔2 · 9/30 开服",
        tag="新品上线 · Steam 在线第 4",
        big="211,000", bigsub="当前在线（10/12）· 韩式奇幻 MMORPG",
        c1=(8,20,46), c2=(20,96,140), c3=(120,220,226), glow=(140,235,240)),
    "bongocat": dict(
        steam="3419430",
        en="Bongo Cat", cn="邦戈猫 · 桌面伴侣 / 挂机",
        tag="Steam 在线第 1 · 独立游戏",
        big="154,090", bigsub="当前在线（10/12）· 历史峰值 19.5 万",
        c1=(34,20,14), c2=(170,96,58), c3=(250,206,168), glow=(255,220,180)),
    # ---- 热点固定第 11 条：版号重点（无对应游戏，纯程序化信息图）----
    "license": dict(
        en="GAME LICENSES", cn="版号动态 · 209 款落地 / 15 款变更",
        tag="版号 · 9/30 公布",
        big="209", bigsub="9 月批次获批 · 年内累计 1,571 款（同比 +23%）",
        c1=(10,22,52), c2=(30,78,150), c3=(120,196,236), glow=(140,210,255)),
    # ---- 热点固定第 12 条：端游转手游独立游戏候选（2x2 拼贴）----
    "sts2": dict(
        steam="2868840",
        en="Slay the Spire 2", cn="杀戮尖塔2 · 卡牌构筑 Roguelike",
        tag="移植候选 · 卡牌构筑",
        big="574,638", bigsub="历史峰值在线 · 当前 48,540 / 安装 2.71GB",
        c1=(14,18,40), c2=(96,52,148), c3=(214,166,240), glow=(226,180,255)),
    "tbh": dict(
        steam="3678970",
        en="TBH: Task Bar Hero", cn="任务栏英雄 · 挂机自动战斗",
        tag="移植候选 · 挂机放置",
        big="0.55GB", bigsub="安装体积全表最轻 · 当前在线 59,964",
        c1=(28,16,10), c2=(158,84,26), c3=(246,196,120), glow=(255,206,130)),
    "rimworld": dict(
        steam="294100",
        en="RimWorld", cn="环世界 · 殖民地模拟",
        tag="移植候选 · 模拟经营",
        big="1.07GB", bigsub="安装仅 1.07GB · 当前在线 21,258",
        c1=(12,26,32), c2=(40,110,116), c3=(150,216,208), glow=(170,236,226)),
}


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def build(d):
    """程序化品牌封面：三段渐变 + 光斑 + 斜纹 + 底部暗化 + 排版"""
    img = Image.new("RGB", (W, H))
    dr = ImageDraw.Draw(img)
    c1, c2, c3 = d["c1"], d["c2"], d["c3"]
    for y in range(H):                                    # 竖向三段渐变
        t = y / (H - 1)
        c = lerp(c1, c2, t / 0.52) if t < 0.52 else lerp(c2, c3, (t - 0.52) / 0.48)
        dr.line([(0, y), (W, y)], fill=c)

    # 光斑（右上大光晕 + 左下小光晕）
    for (cx, cy, r, a) in [(int(W*0.86), int(H*0.06), int(H*1.30), 74),
                           (int(W*0.02), int(H*1.06), int(H*1.10), 44)]:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(lay).ellipse([cx-r, cy-r, cx+r, cy+r], fill=d["glow"] + (a,))
        lay = lay.filter(ImageFilter.GaussianBlur(r * 0.92))     # 大模糊 → 无硬边
        img = Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB")

    # 斜纹纹理
    tex = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(tex)
    for x in range(-H, W, max(8, int(W * 0.026))):
        td.line([(x, 0), (x + H, H)], fill=(255, 255, 255, 13), width=1)
    img = Image.alpha_composite(img.convert("RGBA"), tex).convert("RGB")

    # 底部 + 左侧暗化（保证白字可读；多叠一层避免亮色渐变吃字）
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for y in range(H):
        t = max(0.0, (y - H * 0.18) / (H * 0.82))
        od.line([(0, y), (W, y)], fill=(0, 0, 0, int(190 * t ** 1.4)))
    for x in range(int(W * 0.66)):
        t = max(0.0, 1 - x / (W * 0.66))
        od.line([(x, 0), (x, H)], fill=(0, 0, 0, int(70 * t ** 1.6)))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

    # ---- 以下坐标全部按画布比例计算，改尺寸不会错版 ----
    d2 = ImageDraw.Draw(img)
    PX = int(W * 0.043)                                    # 左右安全边距
    # 左上胶囊标签
    f_tag = font(max(10, int(H * 0.052)), True)
    tw = d2.textlength(d["tag"], font=f_tag)
    ty, ph = int(H * 0.074), int(H * 0.104)
    d2.rounded_rectangle([PX, ty, PX + tw + int(H * 0.096), ty + ph],
                         radius=ph // 2, fill=(255, 255, 255, 238))
    d2.text((PX + int(H * 0.048), ty + int(H * 0.026)), d["tag"], font=f_tag, fill=(22, 30, 46))

    # 左下：英文主标题（自动缩放防溢出）+ 中文副标题
    size = int(H * 0.148)
    while size > int(H * 0.07):
        if d2.textlength(d["en"], font=font(size, True)) <= W * 0.90:
            break
        size -= 2
    ey = int(H * 0.322)
    d2.text((PX, ey), d["en"], font=font(size, True), fill=(255, 255, 255))
    d2.text((PX + int(W * 0.005), ey + size + int(H * 0.026)), d["cn"],
            font=font(max(10, int(H * 0.055)), False), fill=(233, 239, 250))

    # 右下：关键数字（右对齐）+ 说明
    d2.text((W - PX, int(H * 0.676)), d["big"], font=font(int(H * 0.118), True),
            fill=(255, 255, 255), anchor="ra")
    d2.text((W - PX, int(H * 0.855)), d["bigsub"], font=font(max(9, int(H * 0.044)), False),
            fill=(226, 234, 246), anchor="ra")
    return img


def to_uri(img):
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=78, optimize=True, progressive=True, subsampling=1)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def fit16x9(im):
    """统一裁切为 16:9 并缩放到目标尺寸"""
    tw, th = im.size
    th9 = int(tw * 9 / 16)
    if th > th9:
        off = (th - th9) // 2
        im = im.crop((0, off, tw, off + th9))
    elif th < th9:
        tw9 = int(th * 16 / 9)
        off = (tw - tw9) // 2
        im = im.crop((off, 0, off + tw9, th))
    return im.resize((W, H), Image.LANCZOS)


def fetch_url(u, timeout=20, tries=5):
    """本环境到 Steam 的网络是**瞬时失败**（同一 URL 时而 000、时而 200），必须退避重试。
    ⚠️ 不要因为一次失败就判定某款要走程序化兜底 —— 先重试几次再下结论。"""
    import time
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception as e:
            last = e
            time.sleep(1.2 * (k + 1))
    raise last


RAW = f"{TMP}/covers_raw"
os.makedirs(RAW, exist_ok=True)


def fetch_steam(appid):
    """三级策略：老 CDN header.jpg → 商店页 og:image（新 CDN）→ None（走程序化兜底）

    本环境实测：2026 年新游在老的 cdn.cloudflare.steamstatic.com 全为 404，
    但**商店页 og:image 指向新 CDN `shared.cdn.queniuqe.com`**，可正常取到
    616x353 capsule 图。抓到的原图缓存到 .tmp_r8/covers_raw/ 以免重复抓取。
    返回 (PIL.Image, 来源标记)。
    """
    cache = f"{RAW}/{appid}.jpg"
    if os.path.exists(cache) and os.path.getsize(cache) > 4096:
        return fit16x9(Image.open(cache).convert("RGB")), "real-og"
    try:
        raw = fetch_url(CDN % appid, 12)
        Image.open(io.BytesIO(raw)).verify()
        return fit16x9(Image.open(io.BytesIO(raw)).convert("RGB")), "real-cdn"
    except Exception:
        pass
    try:
        html = fetch_url("https://store.steampowered.com/app/%s/" % appid, 25).decode("utf-8", "ignore")
        m = re.search(r'og:image"\s+content="([^"]+)"', html)
        if not m:
            return None, "none"
        raw = fetch_url(m.group(1).replace("&amp;", "&"), 25)
        open(cache, "wb").write(raw)
        return fit16x9(Image.open(io.BytesIO(raw)).convert("RGB")), "real-og"
    except Exception:
        return None, "none"


def main():
    out, stat = {}, {}
    for k, d in COVERS.items():
        real, how = None, "none"
        if d.get("steam"):                     # 无 steam 字段的（如版号信息图）直接走程序化
            real, how = fetch_steam(d["steam"])
        if real is None:
            img, how = build(d), "generated"
        else:
            img = real
        uri = to_uri(img)
        out[k] = uri
        stat[k] = (how, len(uri) // 1024)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    for k, (how, kb) in stat.items():
        print("  %-12s %-10s %4d KB(base64)" % (k, how, kb))
    real_n = sum(1 for v in stat.values() if v[0].startswith("real"))
    print("OK covers.json -> %s  (%d 张，真实 %d / 生成 %d，合计 %.0f KB)"
          % (OUT, len(out), real_n, len(out) - real_n, sum(v[1] for v in stat.values())))


if __name__ == "__main__":
    main()
