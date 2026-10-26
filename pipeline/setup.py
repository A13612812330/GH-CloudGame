# -*- coding: utf-8 -*-
"""端游三源周报 · 配置向导（双击/命令行都能用）

两种模式
--------
1) 图形模式（人工用，点选文件夹）:
       python setup.py

2) 命令模式（AI Agent 用，无需 GUI）:
       python setup.py --data-dir "D:/端游周报数据" --out-dir "D:/周报产出" \
                       --cur 9.28-10.11 --prev 9.14-9.27 --run-date 2026-10-12

   不传 --cur/--prev 时，自动取数据根目录下「最近修改的两个期目录」。

3) 只体检不改配置:
       python setup.py --check

产出：与脚本同级的上一级目录下写 config.json（技能根或仓库根）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------- 公共
def scan_periods(data_dir: Path) -> list[tuple[str, Path]]:
    """数据根目录下含 xlsx 的子目录，按最近修改倒序。"""
    if not data_dir.is_dir():
        return []
    got = []
    for d in data_dir.iterdir():
        if not d.is_dir() or d.name.startswith((".", "_")):
            continue
        if any(d.glob("*.xls*")):
            got.append((d.name, d))
    got.sort(key=lambda x: x[1].stat().st_mtime, reverse=True)
    return got


def detect_pair(data_dir: Path) -> tuple[str, str]:
    ps = scan_periods(data_dir)
    if len(ps) < 2:
        raise SystemExit(
            "数据根目录下至少要有两个含 xlsx 的期目录（本期 + 上期）。\n"
            "  目录：%s\n  当前检测到：%s" % (data_dir, [p[0] for p in ps] or "无")
        )
    return ps[0][0], ps[1][0]


def config_target() -> Path:
    env = os.environ.get("GH_CONFIG")
    if env:
        return Path(env)
    for base in [HERE.parent, HERE, HERE.parent.parent]:
        p = base / "config.json"
        if p.is_file():
            return p
    return HERE.parent / "config.json"


def build_config(data_dir: str, out_dir: str, cur: str, prev: str,
                 run_date: str = "", tmp_dir: str = "") -> dict:
    base = Path(data_dir).expanduser().resolve()
    out = Path(out_dir).expanduser().resolve()
    return {
        "_说明": "端游三源周报流水线配置。改路径只改这里，脚本全部读此文件。",
        "data_dir": str(base).replace("\\", "/"),
        "out_dir": str(out).replace("\\", "/"),
        "tmp_dir": (tmp_dir or str(out / "_tmp_run")).replace("\\", "/"),
        "assets_dir": str((HERE.parent / "assets").resolve()).replace("\\", "/"),
        "python": sys.executable.replace("\\", "/"),
        "node": "node",
        "period": {
            "cur": {"label": cur, "dir": cur,
                    "search": "", "dl": ""},
            "prev": {"label": prev, "dir": prev,
                     "search": "", "dl": ""},
        },
        "run_date": run_date,
    }


def save_cfg(cfg: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def report(data_dir: str, out_dir: str, cur: str, prev: str) -> bool:
    """写完立刻用 _cfg 体检一遍。"""
    sys.path.insert(0, str(HERE))
    try:
        import importlib
        import _cfg
        importlib.reload(_cfg)
        print("\n" + _cfg.CFG.summary())
        ok = _cfg.CFG.check_ready()
        print("\n" + ("✅ 配置可用，可以开跑" if ok else "❌ 仍有问题，见上面提示"))
        return ok
    except SystemExit as e:
        print("❌ %s" % e)
        return False


# ---------------------------------------------------------------- CLI
def run_cli(args) -> int:
    data_dir = args.data_dir
    out_dir = args.out_dir
    if not data_dir or not out_dir:
        raise SystemExit("命令行模式必须同时给 --data-dir 和 --out-dir（或用图形模式：python setup.py）")
    d = Path(data_dir).expanduser()
    if not d.is_dir():
        raise SystemExit("数据根目录不存在：%s" % d)

    cur, prev = args.cur, args.prev
    if not cur or not prev:
        a, b = detect_pair(d)
        cur = cur or a
        prev = prev or b
        print("自动识别期次：本期=%s  上期=%s" % (cur, prev))

    cfg = build_config(str(d), out_dir, cur, prev, args.run_date, args.tmp_dir or "")
    path = save_cfg(cfg, Path(args.config) if args.config else config_target())
    print("✅ 已写入 %s" % path)
    ok = report(str(d), out_dir, cur, prev)
    return 0 if ok else 2


# ---------------------------------------------------------------- GUI
def run_gui() -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except Exception as e:
        raise SystemExit(
            "图形界面不可用（%s）。请改用命令行模式：\n"
            "  python setup.py --data-dir <数据根目录> --out-dir <输出目录> "
            "--cur <本期目录> --prev <上期目录>" % e
        )

    root = tk.Tk()
    root.title("端游三源周报 · 配置向导")
    root.geometry("640x330")
    root.resizable(False, False)

    v_data = tk.StringVar()
    v_out = tk.StringVar()
    v_cur = tk.StringVar()
    v_prev = tk.StringVar()

    def pick_data():
        p = filedialog.askdirectory(title="选择数据根目录（各级期目录的上一级）")
        if p:
            v_data.set(p)
            refresh()

    def pick_out():
        p = filedialog.askdirectory(title="选择产出目录（看板与 Excel 放这里）")
        if p:
            v_out.set(p)

    def refresh(*_):
        names = [n for n, _ in scan_periods(Path(v_data.get()) if v_data.get() else Path("."))]
        cb_cur["values"] = names
        cb_prev["values"] = names
        if names and not v_cur.get():
            v_cur.set(names[0])
        if len(names) > 1 and not v_prev.get():
            v_prev.set(names[1])

    pad = {"padx": 10, "pady": 6}
    row = 0
    tk.Label(root, text="数据根目录", anchor="e", width=12).grid(row=row, column=0, **pad)
    tk.Entry(root, textvariable=v_data, width=58).grid(row=row, column=1, **pad)
    tk.Button(root, text="浏览…", command=pick_data, width=8).grid(row=row, column=2, **pad)

    row += 1
    tk.Label(root, text="产出目录", anchor="e", width=12).grid(row=row, column=0, **pad)
    tk.Entry(root, textvariable=v_out, width=58).grid(row=row, column=1, **pad)
    tk.Button(root, text="浏览…", command=pick_out, width=8).grid(row=row, column=2, **pad)

    row += 1
    tk.Label(root, text="本期期目录", anchor="e", width=12).grid(row=row, column=0, **pad)
    cb_cur = ttk.Combobox(root, textvariable=v_cur, width=40)
    cb_cur.grid(row=row, column=1, sticky="w", **pad)

    row += 1
    tk.Label(root, text="上期期目录", anchor="e", width=12).grid(row=row, column=0, **pad)
    cb_prev = ttk.Combobox(root, textvariable=v_prev, width=40)
    cb_prev.grid(row=row, column=1, sticky="w", **pad)

    row += 1
    hint = tk.Label(root, text="提示：期目录下放「搜索*.xlsx」与「*下载*.xlsx / 鲸云*.xlsx」即可，文件名不用改。",
                    fg="#666", anchor="w", justify="left")
    hint.grid(row=row, column=0, columnspan=3, sticky="w", padx=10)

    def do_save():
        if not v_data.get() or not v_out.get():
            messagebox.showwarning("缺参数", "请先选择数据根目录与产出目录")
            return
        if not v_cur.get() or not v_prev.get():
            messagebox.showwarning("缺参数", "请选择本期与上期目录")
            return
        cfg = build_config(v_data.get(), v_out.get(), v_cur.get(), v_prev.get())
        path = save_cfg(cfg, config_target())
        messagebox.showinfo("已保存", "配置已写入：\n%s\n\n接下来运行 01 → 02 → 03 → 04 …" % path)
        root.destroy()

    row += 1
    bar = tk.Frame(root)
    bar.grid(row=row, column=0, columnspan=3, pady=12)
    tk.Button(bar, text="保存并校验", command=do_save, width=14, height=2).pack(side="left", padx=8)
    tk.Button(bar, text="取消", command=root.destroy, width=10, height=2).pack(side="left", padx=8)

    root.mainloop()
    return 0


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description="端游三源周报 · 配置向导")
    ap.add_argument("--data-dir", help="数据根目录（各级期目录的上一级）")
    ap.add_argument("--out-dir", help="产出目录")
    ap.add_argument("--cur", help="本期期目录名，如 9.28-10.11")
    ap.add_argument("--prev", help="上期期目录名，如 9.14-9.27")
    ap.add_argument("--run-date", default="", help="出报告日期，如 2026-10-12")
    ap.add_argument("--tmp-dir", default="", help="中间产物目录（默认 <产出>/_tmp_run）")
    ap.add_argument("--config", default="", help="写入指定配置文件路径")
    ap.add_argument("--check", action="store_true", help="只打印当前配置并体检")
    args = ap.parse_args()

    if args.check:
        return 0 if report("", "", "", "") else 2
    if args.data_dir or args.out_dir:
        return run_cli(args)
    return run_gui()


if __name__ == "__main__":
    sys.exit(main())
