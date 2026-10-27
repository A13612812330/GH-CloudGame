// ============================================================================
// 端游周报流水线 · 步骤 06：jsdom 渲染回归测试
// 运行：NODE_PATH="<含 jsdom 的 node_modules>" node 06_test_board.js
// ----------------------------------------------------------------------------
// 作用：无头渲染 05 产出的 HTML，检查各区块是否真的渲染出来（行数）、
//       可见文本有没有 undefined / NaN / [object，以及有没有 JS 运行时错误。
// 用法：可用 BOARD 环境变量指定待测 HTML，默认测最新一期。
// ⚠️ 本文件是 .js，注释只能用 // 或 /* */；不要写 Python 风格的 # 注释（会导致 SyntaxError）。
// 说明：选择器与「浅色优雅风」样式基线（05_gen_board.py）配套；
//       若改了 DOM 结构（#kpis / #topChart / #cmpChart / #hotGrid / #tbl-s4 / #tbl-s* / #rail …）
//       需同步更新下方 checks。
// ============================================================================
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');

// 路径默认从 config.json 派生（与 Python 脚本同一份配置），也可用环境变量覆盖：
//   BOARD=<html>  TMP=<中间产物目录>
function loadCfg() {
  let dir = __dirname;
  for (let i = 0; i < 4; i++) {
    for (const name of ['config.json', 'config.example.json']) {
      const f = path.join(dir, name);
      if (fs.existsSync(f)) {
        return { dir, cfg: JSON.parse(fs.readFileSync(f, 'utf8')) };
      }
    }
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  return { dir: process.cwd(), cfg: {} };
}
const { dir: CFG_DIR, cfg } = loadCfg();
const abs = p => (path.isAbsolute(p) ? p : path.join(CFG_DIR, p));
const pick = (env, val, dft) => process.env[env] || val || dft;

const cur = (cfg.period && cfg.period.cur) || cfg.cur || {};
const curLabel = process.env.GH_CUR || cur.label || '';
const outDir = abs(pick('GH_OUT_DIR', cfg.out_dir, '.'));
// ⚠️ 不要用 TMP 作为变量名：Windows 上 TMP/TEMP 是系统保留变量（指向 Temp 目录），会被误读。
//    中间产物目录请用 GH_TMP 覆盖。
const tmpDir = abs(pick('GH_TMP', cfg.tmp_dir, path.join(outDir, '_tmp_run')));

const p = process.env.BOARD || path.join(outDir, `端游三源周报看板_${curLabel}.html`);
if (!fs.existsSync(p)) {
  console.error(`[06] 找不到看板：${p}\n     请先跑 05_gen_board.py，或用 BOARD=<html> 指定。`);
  process.exit(2);
}
const html = fs.readFileSync(p, 'utf8');
// 期望值从当期 data.json 派生，避免每换一期就手改数字
const TMP = tmpDir;
const DD = JSON.parse(fs.readFileSync(path.join(TMP, 'data.json'), 'utf8'));
const L = a => (a || []).length;

const errs = [];
const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  pretendToBeVisual: true,
  virtualConsole: new VirtualConsole().on('jsdomError', e => errs.push(e.message)),
});
const d = dom.window.document;
const txt = s => (d.querySelector(s) || {}).textContent || '';
const n = s => d.querySelectorAll(s).length;

const checks = [
  ['顶部徽章', n('#chips .chip'), 5],
  ['KPI 卡片', n('#kpis .kpi'), 6],
  ['搜索量排行行', n('#topChart .rrow'), 15],
  ['跨期对比行(搜索)', n('#cmpChart .crow'), 12],
  ['鲸云下载排行行', n('#dlChart .rrow'), 12],
  ['鲸云逐日趋势 SVG', n('#dailyChart svg'), 1],
  ['鲸云趋势数据点(按 data.json 粒度派生)', n('#dailyChart circle'), (DD.daily && DD.daily.labels ? DD.daily.labels.length : 0)],
  ['Steam 热度行', n('#stChart .rrow'), 15],
  ['品类环形扇区', n('#catChart .cat-ring path'), 8],
  ['品类排行行', n('#catChart .cat-row'), 8],
  ['品类环形中心数', txt('#catChart .cat-ring .mid .n') ? 1 : 0, 1],
  ['三源共振指标卡', n('#hotCard div[style*="rgba(224,62,62,.28)"]'), 9],
  ['热点卡片(固定12条)', n('#hotGrid .hot-item'), 12],
  ['热点封面容器', n('#hotGrid .cov'), 12],
  ['单图封面条目数', n('#hotGrid .cov > img'), null],     // >0：本期的单图条数随选题变化
  ['拼贴封面恒为1条', n('#hotGrid .cov4'), 1],            // 结构不变量：只有第12条「移植候选」用拼贴
  ['拼贴恒为4图(2x2)', n('#hotGrid .cov4 img'), 4],
  ['热点数据封面数', n('#hotGrid .hot-viz'), null],       // >0：大盘/构成类用现画图表
  ['滚动条条目', n('#ticker span'), 24],
  ['右侧定位条项', n('#rail a'), 6],
  ['定位条圆点', n('#rail .dt'), 7],                     // 6 项 + 1 表头
  ['定位条文字标签', n('#rail .lb'), 7],
  ['定位条为 fixed 悬浮', /\.rail\{position:fixed/.test(html) ? 1 : 0, 1],
  ['旧的独立重点表区块已移除', n('#focus'), 0],          // 防回归：重点表已并入 Tab1
  ['旧的顶部吸顶导航已移除', n('#navIn'), 0],
  ['重点表行(Tab1) = data.json s4', n('#tbl-s4 tbody tr'), L(DD.s4)],
  ['全屏重点表行 = data.json s4', n('#fsTbl tbody tr'), L(DD.s4)],
  ['重点表行数下限 >= 27', L(DD.s4) >= 27 ? 1 : 0, 1],     // 防回归：不许悄悄缩减重点表覆盖
  ['全屏查看按钮', n('#fsBtn'), 1],
  ['Tab1 默认激活=重点表', (() => {
    const t = d.querySelector('#tabs .tab.active');
    return t && t.getAttribute('data-t') === 's4' ? 1 : 0;
  })(), 1],
  ['重点表 pane 默认展开', n('#p-s4.active'), 1],
  ['Tab1 标题含「三源关联重点表」', /三源关联重点表/.test(txt('#tabs .tab')) ? 1 : 0, 1],
  ['品类环形路径合法', (() => {                       // 环形必须是外径100/内径63的正规扇环
    const ps = d.querySelectorAll('#catChart .cat-ring path');
    const re = /^M-?[\d.]+ -?[\d.]+ A100 100 0 [01] 1 -?[\d.]+ -?[\d.]+ L-?[\d.]+ -?[\d.]+ A63 63 0 [01] 0 -?[\d.]+ -?[\d.]+ Z$/;
    return ps.length && [].every.call(ps, p => re.test(p.getAttribute('d') || '')) ? 1 : 0;
  })(), 1],
  ['首条热点=数据封面', n('#hotGrid .hot-item:nth-child(1) .hot-viz'), 1],
  ['第11条=版号重点', /版号/.test(txt('#hotGrid .hot-item:nth-child(11) .badge')) &&
                      /版号/.test(txt('#hotGrid .hot-item:nth-child(11) .tt')) ? 1 : 0, 1],
  ['第12条=移植候选', /移植候选/.test(txt('#hotGrid .hot-item:nth-child(12) .badge')) &&
                      /端游转手游/.test(txt('#hotGrid .hot-item:nth-child(12) .tt')) ? 1 : 0, 1],
  ['第12条为2x2拼贴', n('#hotGrid .hot-item:nth-child(12) .cov4 img'), 4],
  ['12条热点各有主视觉', (() => {                       // 不允许出现纯渐变空封面
    const cs = d.querySelectorAll('#hotGrid .cov');
    return cs.length === 12 && [].every.call(cs, c => c.querySelector('img, .hot-viz')) ? 1 : 0;
  })(), 1],
  ['热点标题标注12条', /12 条/.test(txt('#hot h2')) ? 1 : 0, 1],
  ['重点表截断单元格 = 2 x s4', n('#tbl-s4 td.clip'), L(DD.s4) * 2],
  ['热点封面为内嵌图', (() => {
    const im = d.querySelectorAll('#hotGrid .cov img');
    return im.length && [].every.call(im, i => /^data:image\/jpeg;base64,/.test(i.getAttribute('src') || '')) ? 1 : 0;
  })(), 1],
  ['明细表-Tabs', n('#tabs .tab'), 4],
  ['明细表-s1 行 = data.json s1', n('#tbl-s1 tbody tr'), L(DD.s1)],
  ['明细表-s2 行 = data.json s2', n('#tbl-s2 tbody tr'), L(DD.s2)],
  ['明细表-s3 行 = data.json s3', n('#tbl-s3 tbody tr'), L(DD.s3)],
  ['页脚命中款数 = kpi.games_s', txt('#f4'), String(DD.kpi.games_s)],
  ['总结段落', n('#sum p'), 8],
  ['页脚填充', txt('#f4') ? 1 : 0, 1],
];
let bad = 0;
for (const [name, got, want] of checks) {
  const ok = want === null ? got > 0 : got === want;
  if (!ok) bad++;
  console.log(`${ok ? '✅' : '❌'} ${name}: ${got}${want !== null ? ' / 期望 ' + want : ''}`);
}

// ---- 行为断言（改变 DOM 状态，故放在静态断言之后）----
function clickTab(t) {
  d.querySelector(`#tabs .tab[data-t="${t}"]`).dispatchEvent(new dom.window.Event('click'));
}
const beh = [];
// ① Tab1 过滤重点表：输入「渔力」应真的筛掉其它行
const before = n('#tbl-s4 tbody tr');
const inp = d.querySelector('#tq');
inp.value = '渔力'; inp.dispatchEvent(new dom.window.Event('input'));
const filtered = n('#tbl-s4 tbody tr');
inp.value = ''; inp.dispatchEvent(new dom.window.Event('input'));
const restored = n('#tbl-s4 tbody tr');
beh.push(['Tab1 过滤生效', (filtered > 0 && filtered < before && restored === before) ? 1 : 0, 1]);
// ② 切到 s1：全屏按钮应隐藏、s1 pane 应展开
clickTab('s1');
beh.push(['切到 s1 后全屏按钮隐藏', d.querySelector('#fsBtn').style.display === 'none' ? 1 : 0, 1]);
beh.push(['切到 s1 后 pane 切换', n('#p-s1.active'), 1]);
beh.push(['切到 s1 时 s4 pane 收起', n('#p-s4.active'), 0]);
// ③ 切回重点表：全屏按钮恢复
clickTab('s4');
beh.push(['切回重点表后全屏按钮恢复', d.querySelector('#fsBtn').style.display === '' ? 1 : 0, 1]);

for (const [name, got, want] of beh) {
  const ok = got === want;
  if (!ok) bad++;
  console.log(`${ok ? '✅' : '❌'} ${name}: ${got}${want !== null ? ' / 期望 ' + want : ''}`);
}
console.log('\nKPI 首卡:', txt('#kpis .kpi .val'), '|', txt('#kpis .kpi .note'));
console.log('重点表首行(Tab1):', txt('#tbl-s4 tbody tr').slice(0, 80));
console.log('明细表首行:', txt('#tbl-s1 tbody tr').slice(0, 80));
console.log('总结首段:', txt('#sum p').slice(0, 80));

const visible = (() => {
  const c = d.body.cloneNode(true);
  c.querySelectorAll('script,style').forEach(e => e.remove());
  return c.textContent;
})();
const dirty = /undefined|NaN|\[object/.test(visible);
console.log('\n未定义字样检查:', dirty ? '❌ 可见文本中发现 undefined/NaN' : '✅ 可见文本无 undefined/NaN');
console.log('JS 运行时错误:', errs.length ? errs.slice(0, 3) : '无');
if (dirty) bad++;
console.log('\n' + (bad === 0 ? '🎉 全部通过 (' + p.split('/').pop() + ')' : `⚠️ ${bad} 项异常`));
