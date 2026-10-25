// 就业准备：五 Tab（八股学习 / 项目学习 / 实习准备 / 面经库 / 投递导航）
import { api } from '../api.js';
import { el, escape, toast, mdToHtml, confirmBox } from './kit.js';
import { renderGraph } from '../components/graph.js';
import { openArticle } from '../components/articleView.js';
import { startReviewSession } from './career/review.js';
import { renderProjects } from './career/projects.js';
import { renderIntern } from './career/intern.js';
import { renderMianjing } from './career/mianjing.js';
import { renderNavigate } from './career/navigate.js';

const TABS = [
  ["bagu", "📖 八股学习"], ["projects", "🛠 项目学习"],
  ["intern", "🏢 实习准备"], ["mianjing", "📚 面经库"],
  ["nav", "🚀 投递导航"],
];

export default {
  id: 'career',
  title: '就业准备',
  icon: '💼',
  async render(container, rerender) {
    const refresh = () => rerender ? rerender() : location.reload();

    // Tab 状态存 hash：#/career/projects
    let tab = (location.hash.split("/")[2] || "bagu");
    if (!TABS.some(([k]) => k === tab)) tab = "bagu";

    container.appendChild(el(`
      <div class="page-head"><h1>就业准备</h1>
      <p>八股知识图谱 · AI 问答卡片复习 · 项目与简历 · 投递面试跟进 · 面经库</p></div>`));

    const tabBar = el(`<div style="display:flex;gap:8px;margin-bottom:16px;border-bottom:1px solid var(--line);padding-bottom:10px"></div>`);
    TABS.forEach(([k, label]) => {
      const b = el(`<button class="btn" style="${k === tab ? "border-color:var(--accent);color:var(--accent-text);font-weight:600" : ""}">${label}</button>`);
      b.onclick = () => { location.hash = `#/career/${k}`; };
      tabBar.appendChild(b);
    });
    container.appendChild(tabBar);
    const body = el('<div></div>');
    container.appendChild(body);

    if (tab === "projects") return renderProjects(body, refresh);
    if (tab === "intern") return renderIntern(body, refresh);
    if (tab === "mianjing") return renderMianjing(body, refresh);
    if (tab === "nav") return renderNavigate(body, refresh);
    return renderBagu(body, refresh);
  },
};

// ================= Tab 1: 八股学习 =================
async function renderBagu(container, refresh) {
  const [plan, learn, graph] = await Promise.all([
    api('/api/career/kb-plan?daily=2'), api('/api/learn/cards'), api('/api/kb/graph?lib=bagu'),
  ]);

  // 顶部统计行
  const head = el(`<div class="stat-row" style="margin-bottom:14px">
    <div class="stat"><b>${plan.remaining ?? "-"}</b><span>八股待读</span></div>
    <div class="stat"><b>${learn.stats.total}</b><span>知识卡片</span></div>
    <div class="stat"><b>${learn.stats.due}</b><span>待复习卡片</span></div>
    <div class="stat"><b>${graph.edges.length}</b><span>图谱关联</span></div>
  </div>`);
  container.appendChild(head);

  const grid = el('<div class="grid cols-2" style="align-items:start"></div>');
  container.appendChild(grid);

  // ---- 左：找文章 + 今日计划 + 问答窗口 + 复习 + 卡片 ----
  const left = el('<div style="display:flex;flex-direction:column;gap:16px;min-width:0"></div>');

  // 找文章（v1.3）：关键词 + 栏目 + 已读未读
  const findCard = el(`<div class="card"><div class="card-title">🔎 找文章
    <span class="hint">不跟计划走，自己挑着读</span>
    <div class="inline-form" style="margin-top:8px">
      <input placeholder="关键词，如：MVCC / 拥塞控制" style="flex:1" class="f-q">
      <select class="f-cat"><option value="">全部栏目</option></select>
      <select class="f-status"><option value="">已读+未读</option>
        <option value="unread">未读</option><option value="read">已读</option></select>
      <button class="btn btn-primary f-go">筛选</button></div>
    <div class="f-result" style="max-height:300px;overflow:auto;margin-top:8px"></div>
  </div>`);
  const fResult = findCard.querySelector('.f-result');
  const doBrowse = async () => {
    const q = findCard.querySelector('.f-q').value.trim();
    const r = await api(`/api/career/kb-browse?q=${encodeURIComponent(q)}` +
      `&category=${encodeURIComponent(findCard.querySelector('.f-cat').value)}` +
      `&status=${findCard.querySelector('.f-status').value}`);
    fResult.innerHTML = '';
    if (!r.available) { fResult.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">知识库未挂载</div></div>')); return; }
    // 栏目选项回填（一次）
    const sel = findCard.querySelector('.f-cat');
    if (sel.options.length === 1) r.categories.forEach(c =>
      sel.appendChild(el(`<option value="${escape(c)}">${escape(c)}</option>`)));
    if (!r.items.length) { fResult.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">无匹配文章</div></div>')); return; }
    r.items.slice(0, 50).forEach(it => {
      const row = el(`<div class="check-item">
        <div style="flex:1;min-width:0"><div class="t">${escape(it.title)}</div>
        <div style="font-size:12px;color:var(--muted)">${escape(it.category || '')}${it.read ? ' · 已读' : ''}</div></div>
        ${it.read ? '' : '<button class="btn f-read" style="padding:3px 10px;font-size:12px">✔已读</button>'}
        <button class="btn f-open" style="padding:3px 10px;font-size:12px">阅读</button></div>`);
      const rd = row.querySelector('.f-read');
      if (rd) rd.onclick = async () => {
        await api('/api/career/kb-read', { method: 'POST', body: { relpath: it.relpath } });
        toast('已标记已读'); doBrowse();
      };
      row.querySelector('.f-open').onclick = () => openArticle(it.relpath, { library: "bagu" });
      fResult.appendChild(row);
    });
    if (r.total > 50) fResult.appendChild(el(`<div style="font-size:12px;color:var(--muted);padding:6px 0">共 ${r.total} 篇匹配，仅显示前 50 篇（加关键词缩小范围）</div>`));
  };
  findCard.querySelector('.f-go').onclick = doBrowse;
  findCard.querySelector('.f-q').onkeydown = (e) => { if (e.key === 'Enter') doBrowse(); };
  left.appendChild(findCard);
  doBrowse();

  const kbCard = el(`<div class="card"><div class="card-title">📅 今日八股（已完成 ${plan.today_done || 0} 篇）</div></div>`);
  if (!plan.available) {
    kbCard.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">知识库未挂载（设置页配置路径）</div></div>'));
  } else if (!plan.items.length) {
    kbCard.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">今日计划已完成 🎉</div></div>'));
  } else {
    plan.items.forEach(it => {
      const row = el(`<div class="check-item">
        <button class="tick">✓</button>
        <div style="flex:1;min-width:0"><div class="t">${escape(it.title)}</div>
        <div style="font-size:12px;color:var(--muted)">${escape(it.category)}</div></div>
        <button class="btn rd" style="padding:3px 10px;font-size:12px">阅读</button></div>`);
      row.querySelector(".tick").onclick = async () => {
        await api('/api/career/kb-read', { method: 'POST', body: { relpath: it.relpath } });
        toast("已记录，目标进度 +1"); refresh();
      };
      row.querySelector(".rd").onclick = () => openArticle(it.relpath, { library: "bagu" });
      kbCard.appendChild(row);
    });
  }
  left.appendChild(kbCard);

  // 常驻问答窗口（v1.3）：AI 回答 / 无 AI 给知识库参考回答
  const askCard = el(`<div class="card"><div class="card-title">💬 不懂就问
    <span class="hint q-hint">AI 直答；未配置时给知识库参考段落</span></div>
    <div class="q-log" style="max-height:340px;overflow:auto;display:flex;flex-direction:column;gap:10px"></div>
    <div class="inline-form" style="margin-top:10px"><input placeholder="如：为什么需要四次挥手？epoll 和 select 区别？" style="flex:1">
    <button class="btn btn-primary">提问</button></div></div>`);
  const qLog = askCard.querySelector('.q-log');
  const qInput = askCard.querySelector('input');
  const doAsk = async () => {
    const q = qInput.value.trim();
    if (!q) return;
    qInput.value = '';
    const item = el(`<div><div class="badge" style="margin-bottom:4px">我</div>
      <div style="font-size:13.5px;margin-bottom:8px">${escape(q)}</div>
      <div class="ans"><span style="color:var(--muted);font-size:13px">思考中…</span></div></div>`);
    qLog.appendChild(item);
    qLog.scrollTop = qLog.scrollHeight;
    try {
      const r = await api('/api/kb/ask', { method: 'POST', body: { q, library: "bagu" } });
      const ans = item.querySelector('.ans');
      ans.innerHTML = '';
      ans.appendChild(el(`<div><span class="badge ${r.ai_used ? 'green' : 'gray'}">${r.ai_used ? 'AI' : '参考'}</span></div>`));
      ans.appendChild(el(`<div class="md-view" style="font-size:13.5px;margin:6px 0">${mdToHtml(r.answer || '（无相关内容）')}</div>`));
      (r.sources || []).slice(0, 3).forEach(s => {
        const l = el(`<a href="#" style="display:block;font-size:12.5px;color:var(--muted)">📄 ${escape(s.title)}</a>`);
        l.onclick = (e) => { e.preventDefault(); openArticle(s.relpath, { library: "bagu" }); };
        ans.appendChild(l);
      });
      const save = el('<button class="btn" style="padding:2px 10px;font-size:12px;margin-top:6px">📌 存为复习卡片</button>');
      save.onclick = async () => {
        await api('/api/learn/cards', { method: 'POST',
          body: { title: q.slice(0, 40), q, a: r.answer || '', chapter: '八股问答' } });
        toast('已存入卡片库，明天到期复习');
      };
      ans.appendChild(save);
    } catch (e) { toast(e.message, false); }
    qLog.scrollTop = qLog.scrollHeight;
  };
  askCard.querySelector('button.btn-primary').onclick = doAsk;
  qInput.onkeydown = (e) => { if (e.key === 'Enter') doAsk(); };
  api('/api/bootstrap').then(b => {
    if (!b.ai.configured) askCard.querySelector('.q-hint').textContent = 'AI 未配置：回答=知识库参考段落（设置页接入后升级直答）';
  });
  left.appendChild(askCard);

  // 复习模式入口
  const rvCard = el(`<div class="card"><div class="card-title">🧠 复习模式
    <span class="hint">针对你问过的问题出题，Ebbinghaus 曲线调度</span></div>
    <div style="font-size:13px;color:var(--muted);margin-bottom:10px">
      到期 ${learn.stats.due} · 薄弱 ${learn.stats.weak} · 已掌握 ${learn.stats.done} / 共 ${learn.stats.total} 张</div>
    <button class="btn btn-primary rv-start">▶ 开始复习</button></div>`);
  rvCard.querySelector(".rv-start").onclick = () => {
    // 就地替换为复习界面
    const page = document.getElementById("view");
    page.innerHTML = "";
    startReviewSession(page, () => { location.hash = "#/career/bagu"; });
  };
  left.appendChild(rvCard);
  grid.appendChild(left);

  // ---- 右：知识图谱（小图 + 全屏入口） ----
  const right = el(`<div style="display:flex;flex-direction:column;gap:16px;min-width:0"></div>`);
  const graphCard = el(`<div class="card"><div class="card-title">🕸 知识图谱（${graph.nodes.length} 篇 · ${graph.edges.length} 关联）
    <span class="hint">同栏目聚簇 · 关键词共现 + [[双链]]</span>
    <div style="margin-top:8px;display:flex;gap:8px">
      <button class="btn g-full" style="padding:4px 12px;font-size:13px">⛶ 全屏大图</button>
      <button class="btn g-layer" style="padding:4px 12px;font-size:13px">🗂 分层浏览</button>
    </div></div></div>`);
  graphCard.querySelector(".g-full").onclick = () => { location.hash = "#/graph"; };
  graphCard.querySelector(".g-layer").onclick = () => { location.hash = "#/graph?mode=layered"; };
  const gbox = el('<div style="border:1px solid var(--line);border-radius:10px;overflow:hidden"></div>');
  graphCard.appendChild(gbox);
  right.appendChild(graphCard);
  grid.appendChild(right);

  // 最近问答卡片（v1.19 可删）
  const cCard = el('<div class="card"><div class="card-title">🗂 最近的知识卡片</div></div>');
  learn.cards.slice(0, 6).forEach(c => cCard.appendChild(el(`
    <div style="padding:7px 0;border-bottom:1px solid var(--line);font-size:13px">
      <span class="badge gray">${escape(c.chapter)}</span> ${escape(c.title)}
      <span style="float:right;color:var(--muted);font-size:12px">${c.a ? "有答案" : "待补答"} · ${c.due_date}
      <button class="btn c-del" style="padding:1px 7px;font-size:12px;margin-left:6px" title="删除卡片">✕</button></span></div>`)));
  cCard.querySelectorAll(".c-del").forEach((b, i) => b.onclick = async () => {
    const c = learn.cards[i];
    if (!(await confirmBox(`删除卡片「${c.title}」？其复习进度一并清除。`))) return;
    try { await api(`/api/learn/cards/${c.id}`, { method: 'DELETE' }); toast("已删除"); refresh(); }
    catch (e) { toast(e.message, false); }
  });
  if (!learn.cards.length) cCard.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">上方问答窗口提问后会自动变卡片</div></div>'));
  right.appendChild(cCard);

  // 图谱较大，延迟到下一帧渲染避免卡顿
  requestAnimationFrame(() => {
    renderGraph(gbox, graph, {
      height: 520,
      onNodeClick: (n) => openArticle(n.id, { library: "bagu" }),
    });
  });
}
