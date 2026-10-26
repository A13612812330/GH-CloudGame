# -*- coding: utf-8 -*-
"""端游三源周报流水线 · 统一配置加载

优先级（高 → 低）：
  1. 环境变量   GH_DATA_DIR / GH_OUT_DIR / GH_TMP / GH_CUR / GH_PREV / GH_RUN_DATE
  2. config.json（仓库根或技能根，自动向上查找）
  3. config.example.json
  4. 内置默认值（相对当前工作目录，便于首次试跑）

用法：
    from _cfg import CFG
    CFG.data_dir            # 数据源根目录
    CFG.search_file("cur")  # 本期搜索 xlsx
    CFG.dl_file("prev")     # 上期下载 xlsx
    CFG.tmp                 # 中间产物目录
    CFG.board_out()         # 看板输出路径

设计原则
--------
* 所有路径**只在这里拼一次**，脚本里不再出现盘符。
* 期次用「目录名 + 文件名」表达，而不是绝对路径 —— 同事换机器只需改 data_dir。
* 文件名不确定时（`鲸云下载.xlsx` / `云游戏下载.xlsx` 都出现过）自动探测。
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent

# 向上最多找三层，避免误命中无关目录下的 config.json
_SEARCH_DIRS = [_HERE] + list(_HERE.parents)[:3]

_SEARCH_PAT = re.compile(r"搜索")
_DL_PAT = re.compile(r"下载|鲸云|云游戏下载")


def _find_config() -> Path | None:
    env = os.environ.get("GH_CONFIG")
    if env and Path(env).is_file():
        return Path(env)
    for base in _SEARCH_DIRS:
        for name in ("config.json", "config.example.json"):
            p = base / name
            if p.is_file():
                return p
    return None


def _abs(p: str | os.PathLike, base: Path) -> Path:
    """相对路径按 base 解析，绝对路径原样返回。"""
    q = Path(p).expanduser()
    return q if q.is_absolute() else (base / q)


class Cfg:
    def __init__(self) -> None:
        self.config_path = _find_config()
        raw: dict = {}
        if self.config_path:
            try:
                raw = json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception as e:  # 配置写坏了不要静默
                raise SystemExit(f"[配置错误] 无法解析 {self.config_path}: {e}")
        self._raw = raw
        base = self.config_path.parent if self.config_path else Path.cwd()

        self.data_dir = _abs(os.environ.get("GH_DATA_DIR") or raw.get("data_dir", "./data"), base)
        self.out_dir = _abs(os.environ.get("GH_OUT_DIR") or raw.get("out_dir", "./outputs"), base)
        self._tmp = _abs(os.environ.get("GH_TMP") or raw.get("tmp_dir", "./.tmp_run"), base)

        assets = raw.get("assets_dir")
        self.assets_dir = _abs(assets, base) if assets else (_HERE.parent / "assets")
        self.python = raw.get("python") or sys.executable
        self.node = raw.get("node") or "node"
        self.node_path = raw.get("node_path")
        self.run_date = os.environ.get("GH_RUN_DATE") or raw.get("run_date", "")

    # ---------- 期次 ----------
    def _period_raw(self, which: str) -> dict:
        assert which in ("cur", "prev"), which
        p = (self._raw.get("period") or {}).get(which) or self._raw.get(which) or {}
        return dict(p)

    def _overridable_label(self, which: str) -> str:
        env = os.environ.get("GH_CUR" if which == "cur" else "GH_PREV")
        return env or self._period_raw(which).get("label", "")

    def label(self, which: str) -> str:
        lab = self._overridable_label(which)
        if not lab:
            raise SystemExit(
                f"[配置缺失] 未指定{'本' if which == 'cur' else '上'}期目录。\n"
                f"  解决：运行  python setup.py --data-dir <数据根目录> "
                f"--cur <本期目录名> --prev <上期目录名>\n"
                f"  或设环境变量 {'GH_CUR' if which == 'cur' else 'GH_PREV'}"
            )
        return lab

    def period_dir(self, which: str) -> Path:
        p = self._period_raw(which)
        d = p.get("dir") or self.label(which)
        return _abs(d, self.data_dir)

    def _detect(self, which: str, kind: str) -> Path | None:
        """在期目录下按关键词找 xlsx。kind: search | dl"""
        d = self.period_dir(which)
        if not d.is_dir():
            return None
        pat = _SEARCH_PAT if kind == "search" else _DL_PAT
        cands = [f for f in d.glob("*.xls*")
                 if pat.search(f.name) and not f.name.startswith("~$")]
        # 搜索源要排除注册/下载类误命中
        if kind == "search":
            cands = [f for f in cands if not _DL_PAT.search(f.name) and "注册" not in f.name]
        else:
            cands = [f for f in cands if "注册" not in f.name]
        if not cands:
            return None
        # 取最近修改的（用户常重复导出）
        return max(cands, key=lambda f: f.stat().st_mtime)

    def _file(self, which: str, kind: str) -> Path:
        p = self._period_raw(which)
        name = p.get(kind)
        if name:
            cand = _abs(name, self.period_dir(which))
            if cand.is_file():
                return cand
        got = self._detect(which, kind)
        if got:
            return got
        d = self.period_dir(which)
        raise SystemExit(
            f"[输入缺失] {'本期' if which == 'cur' else '上期'}（{self.label(which)}）"
            f"找不到{'搜索' if kind == 'search' else '下载'}表。\n"
            f"  目录：{d}（{'存在' if d.is_dir() else '不存在'}）\n"
            f"  期望：目录下有名字含「{'搜索' if kind == 'search' else '下载/鲸云'}」的 .xlsx"
        )

    def search_file(self, which: str) -> Path:
        return self._file(which, "search")

    def dl_file(self, which: str) -> Path:
        return self._file(which, "dl")

    # ---------- 其它路径 ----------
    @property
    def tmp(self) -> Path:
        self._tmp.mkdir(parents=True, exist_ok=True)
        return self._tmp

    @property
    def lib(self) -> Path:
        p = self.assets_dir / "endgame_lib.json"
        if not p.is_file():
            raise SystemExit(f"[资产缺失] 词库不存在：{p}")
        return p

    def out(self, name: str) -> Path:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        return self.out_dir / name

    def board_out(self) -> Path:
        return self.out("端游三源周报看板_%s.html" % self.label("cur"))

    def report_out(self) -> Path:
        date = self.run_date or "draft"
        return self.out("端游三源周报_大报告_%s.xlsx" % date)

    # ---------- 自检 ----------
    def summary(self) -> str:
        lines = [
            "配置文件  : %s" % (self.config_path or "（未找到，使用默认值）"),
            "数据根目录: %s" % self.data_dir,
            "输出目录  : %s" % self.out_dir,
            "中间产物  : %s" % self._tmp,
            "词库      : %s" % self.lib,
            "出报告日  : %s" % (self.run_date or "（未设置）"),
        ]
        for w, cn in (("cur", "本期"), ("prev", "上期")):
            try:
                lines.append("%s      : %s → %s" % (cn, self.label(w), self.period_dir(w)))
                lines.append("            搜索 %s" % self.search_file(w).name)
                lines.append("            下载 %s" % self.dl_file(w).name)
            except SystemExit as e:
                lines.append("%s      : ⚠️ %s" % (cn, e))
        return "\n".join(lines)

    def check_ready(self) -> bool:
        ok = True
        try:
            for w in ("cur", "prev"):
                self.search_file(w)
                self.dl_file(w)
        except SystemExit as e:
            print(e)
            ok = False
        if not self.lib.is_file():
            print("[缺失] 词库 %s" % self.lib)
            ok = False
        return ok


CFG = Cfg()

if __name__ == "__main__":
    print(CFG.summary())
    sys.exit(0 if CFG.check_ready() else 1)
