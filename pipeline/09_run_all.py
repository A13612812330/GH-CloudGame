# -*- coding: utf-8 -*-
"""09_run_all.py —— 一条命令跑完整条周报流水线（00 → 08）

用法：
    python 09_run_all.py                 # 跑 00→08（含交付门禁）
    python 09_run_all.py --publish       # 额外跑 07 发布到 GitHub 归档
    python 09_run_all.py --from 04       # 从某一步开始（前面已有产物时省时间）
    python 09_run_all.py --until 05      # 只跑到某一步（调试看板用）
    python 09_run_all.py --no-gate       # 跳过 08 门禁（不建议，仅供调试）
    python 09_run_all.py --list          # 只列出步骤，不执行

设计要点
--------
* 步骤顺序是硬约束：04b 依赖 04 的 data.json，05 依赖 04b 的 covers.json，
  06 校验 05 的产物，08 校验全链路 —— 所以这里用固定列表，不做自动发现。
* 任何一步非 0 退出立即中止，不继续跑（避免用半成品生成看板）。
* 06 是 Node 脚本，需要注入 NODE_PATH；其余是 Python。
* 08 不通过 = 交付被阻断，退出码 2，与普通失败（1）区分开。
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from _cfg import CFG

HERE = Path(__file__).resolve().parent

# (步骤名, 类型, 文件名, 说明)
STEPS = [
    ("00", "py", "00_probe_inputs.py", "探测输入表结构（sheet / 列名 / 日期粒度）"),
    ("01", "py", "01_prep_search_dl.py", "清洗两期搜索与下载 → csv，算跨期合计"),
    ("02", "py", "02_extract_steam_meta.py", "抽取 Steam 元数据（appid → 名称/价格/标签）"),
    ("03", "py", "03_build_steam_chart.py", "合并 SteamDB Top100 快照 → chart.csv"),
    ("04", "py", "04_build_report.py", "生成 5-sheet Excel 大报告 + data.json"),
    ("05a", "py", "10_draft_hotspots.py", "生成 12 条热点初稿（机器挑料 + 模板句，需 --draft-hot）"),
    ("04b", "py", "04b_make_covers.py", "抓取热点封面（Steam 主视觉 / 程序化兜底）"),
    ("05", "py", "05_gen_board.py", "生成单文件 HTML 看板"),
    ("06", "node", "06_test_board.js", "jsdom 回归测试（55 项断言）"),
    ("07", "py", "07_publish_github.py", "归档索引 + 稳定短链（需 --publish 才跑）"),
    ("08", "py", "08_preflight_check.py", "交付门禁：判「数据新、文案旧」"),
]

ORDER = [s[0] for s in STEPS]


def parse_args(argv):
    opt = {"publish": False, "no_gate": False, "list": False,
           "from": None, "until": None, "yes": False, "draft_hot": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--publish":
            opt["publish"] = True
        elif a == "--no-gate":
            opt["no_gate"] = True
        elif a in ("--list", "-l"):
            opt["list"] = True
        elif a in ("--yes", "-y"):
            opt["yes"] = True
        elif a == "--draft-hot":
            opt["draft_hot"] = True
        elif a == "--from" and i + 1 < len(argv):
            i += 1
            opt["from"] = argv[i]
        elif a == "--until" and i + 1 < len(argv):
            i += 1
            opt["until"] = argv[i]
        elif a in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        else:
            print("[参数错误] 未知参数：%s\n（--help 看用法）" % a)
            sys.exit(1)
        i += 1
    return opt


def pick_steps(opt):
    steps = list(STEPS)
    if not opt["draft_hot"]:
        # 05a 只在显式 --draft-hot 时跑；默认沿用 05 里已复核的手写热点
        steps = [s for s in steps if s[0] != "05a"]
    if not opt["publish"]:
        steps = [s for s in steps if s[0] != "07"]
    if opt["no_gate"]:
        steps = [s for s in steps if s[0] != "08"]
    if opt["from"]:
        if opt["from"] not in ORDER:
            raise SystemExit("[参数错误] --from 取值应为 %s 之一" % " / ".join(ORDER))
        start = [s[0] for s in steps].index(opt["from"]) if opt["from"] in [s[0] for s in steps] else 0
        steps = steps[start:]
    if opt["until"]:
        if opt["until"] not in ORDER:
            raise SystemExit("[参数错误] --until 取值应为 %s 之一" % " / ".join(ORDER))
        names = [s[0] for s in steps]
        if opt["until"] in names:
            steps = steps[: names.index(opt["until"]) + 1]
    return steps


def resolve_node_path() -> str:
    """找得到 jsdom 的 node_modules 目录；找不到返回空串。

    顺序：config.node_path → 仓库/技能根 node_modules → 全局 npm root。
    同事机器上通常只需在仓库根 `npm install`，这里能自动发现，不用改配置。
    """
    cands = []
    if CFG.node_path:
        cands.append(str(CFG.node_path))
    cands += [str(HERE.parent / "node_modules"), str(HERE / "node_modules")]
    npm = "npm.cmd" if os.name == "nt" else "npm"
    try:
        r = subprocess.run([npm, "root", "-g"], capture_output=True, text=True, timeout=25)
        if r.returncode == 0 and r.stdout.strip():
            cands.append(r.stdout.strip())
    except Exception:
        pass
    for c in cands:
        if c and (Path(c) / "jsdom").is_dir():
            return c
    return ""


def step_env(kind: str, node_path: str = "") -> dict:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    if kind == "node" and node_path:
        # 追加而非覆盖，避免抹掉调用方已有的 NODE_PATH
        old = env.get("NODE_PATH")
        env["NODE_PATH"] = node_path + (os.pathsep + old if old else "")
    return env


def preflight(need_node: bool):
    """开跑前把环境问题一次报全，避免跑到第 7 步才发现缺依赖。"""
    problems = []
    # Python 依赖
    try:
        import importlib
        for mod, pkg in (("pandas", "pandas"), ("openpyxl", "openpyxl"), ("PIL", "pillow")):
            try:
                importlib.import_module(mod)
            except Exception:
                problems.append("Python 缺少 %s → pip install -r requirements.txt" % pkg)
    except Exception:
        pass

    node_path = ""
    if need_node:
        exe = CFG.node
        if exe != "node" and not Path(exe).exists():
            problems.append("Node 可执行文件不存在：%s → 改 config.json 的 node 字段" % exe)
        else:
            try:
                r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20)
                if r.returncode != 0:
                    problems.append("Node 无法执行：%s" % exe)
            except Exception:
                problems.append("Node 无法执行：%s" % exe)
            node_path = resolve_node_path()
            if not node_path:
                problems.append(
                    "找不到 jsdom（06 回归测试必需）→ 在仓库根执行 `npm install`，"
                    "或在 config.json 里设 node_path 指向含 jsdom 的 node_modules")
    return problems, node_path


def run_one(name: str, kind: str, script: str, desc: str, node_path: str = "",
             extra=None) -> int:
    exe = CFG.node if kind == "node" else CFG.python
    path = HERE / script
    if not path.is_file():
        print("  ❌ 脚本不存在：%s" % path)
        return 1
    if kind == "node" and not Path(exe).exists() and exe != "node":
        print("  ❌ Node 可执行文件不存在：%s（检查 config.json 的 node 字段）" % exe)
        return 1
    print("─" * 74)
    print("▶ [%s] %s" % (name, desc))
    _extra = list(extra or [])
    print("  %s %s%s" % (Path(exe).name, script,
                         " " + " ".join(_extra) if _extra else ""))
    t0 = time.time()
    try:
        proc = subprocess.run([exe, str(path)] + _extra, cwd=str(HERE),
                              env=step_env(kind, node_path),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        print("  ❌ 找不到解释器：%s" % exe)
        return 1
    out = (proc.stdout or "").rstrip()
    # 只回显尾部，避免刷屏；出错时回显更多
    lines = out.splitlines()
    tail = lines[-12:] if proc.returncode == 0 else lines[-30:]
    noise = ("UserWarning", "warn(", "FutureWarning")
    shown = [ln for ln in tail if not any(n in ln for n in noise)]
    for ln in shown:
        print("  │ " + ln)
    dt = time.time() - t0
    if proc.returncode == 0:
        print("  ✅ %s 完成（%.1fs）" % (name, dt))
    else:
        print("  ❌ %s 失败（退出码 %d，%.1fs）" % (name, proc.returncode, dt))
        print("     完整输出末尾：")
        for ln in lines[-40:]:
            print("     " + ln)
    return proc.returncode


def main() -> int:
    opt = parse_args(sys.argv[1:])
    steps = pick_steps(opt)

    if opt["list"]:
        print("步骤顺序（固定，不可调换）：")
        for i, (n, k, f, d) in enumerate(STEPS, 1):
            mark = "●" if any(s[0] == n for s in steps) else "○"
            print("  %s %-4s %-24s %s" % (mark, n, f, d))
        print("\n● = 本次会执行   ○ = 本次跳过")
        return 0

    print("=" * 74)
    print("端游三源周报 · 全流程执行")
    print("=" * 74)
    print(CFG.summary())
    print()

    if not CFG.check_ready():
        print("\n[中止] 输入检查未通过，见上方提示。")
        return 1

    need_node = any(s[1] == "node" for s in steps)
    problems, node_path = preflight(need_node)
    if problems:
        print("\n[环境自检未通过] 共 %d 项：" % len(problems))
        for p in problems:
            print("  ✗ " + p)
        print("\n[中止] 先把上面几项装好再跑（不会动你的数据）。")
        return 1
    print("环境自检 ✅ Python 依赖齐全%s" % (
        "，jsdom 已找到：%s" % node_path if node_path else "，本次不含 Node 步骤"))

    # 换期防呆：run_date 必须与本期标签对得上
    if not CFG.run_date:
        print("\n⚠️ [配置缺失] run_date 未设置，Excel 文件名会变成「draft」。")
        print("   解决：在 config.json 里设 run_date（如 2026-10-12），")
        print("   或设环境变量 GH_RUN_DATE。")
        if not opt["yes"]:
            print("\n[中止] 加 --yes 可忽略继续。")
            return 1

    t_all = time.time()
    done = []
    _hot_json = CFG.tmp / "hot_draft.json"
    _plan_json = CFG.tmp / "covers_plan.json"
    for name, kind, script, desc in steps:
        extra = []
        if name == "04b" and _plan_json.is_file():
            # 封面计划与热点初稿同步产出；显式传 --plan，避免 04b 自行猜
            extra = ["--plan", str(_plan_json)]
            print("  封面计划: %s" % _plan_json.name)
        if name == "05":
            if _hot_json.is_file():
                # 10 的初稿存在就交给 05 校验：仍有 _needs_human 的会被 05 挡下（退出码 3）
                extra = ["--hot", str(_hot_json)]
                print("  热点来源: %s（05 会校验是否还有待人工条目）" % _hot_json.name)
            else:
                print("  热点来源: 05 脚本内手写 HOT（未发现 hot_draft.json）")
        rc = run_one(name, kind, script, desc, node_path, extra)
        if rc != 0:
            print("\n" + "=" * 74)
            print("❌ 流水线在第 [%s] 步中止。已完成的步骤：%s"
                  % (name, " → ".join(done) if done else "（无）"))
            print("=" * 74)
            if name == "05":
                print("  若 05 是被「热点待人工」挡下的（退出码 3）：编辑 %s，"
                      "去掉 _needs_human 后重跑：" % _hot_json.name)
                print("    python 09_run_all.py --from 04b")
            else:
                print("  修完该步后可从断点继续：  python 09_run_all.py --from %s" % name)
            return 1
        done.append(name)

    dt_all = time.time() - t_all
    print("\n" + "=" * 74)
    print("🎉 全流程完成（%d 步，%.1fs）" % (len(done), dt_all))
    print("=" * 74)
    try:
        print("  看板   : %s" % CFG.board_out())
        print("  大报告 : %s" % CFG.report_out())
    except SystemExit:
        pass
    print("  中间产物: %s" % CFG.tmp)

    if "08" in done:
        print("\n  门禁已通过（08 PASS）—— 产物可交付。")
    elif opt["no_gate"]:
        print("\n  ⚠️ 本次跳过了 08 门禁，产物**未经校验**，不要直接发布。")
    if "07" not in done and "08" in done:
        print("  需要归档到 GitHub：python 09_run_all.py --publish --from 07")
    return 0


if __name__ == "__main__":
    sys.exit(main())
