// 力扣页（v1.20）：同步进度+手动打卡（自就业页迁入）/ 本地刷题文件夹 / 问 AI / AI 考我（到期复习，回写 lj.py 记忆曲线）
import { api } from '../api.js';
import { el, escape, toast } from './kit.js';

const chip = { pass: '<span class="badge">✅ 过</span>',
               fuzzy: '<span class="badge amber">🤔 含糊</span>',
               fail: '<span class="badge" style="background:var(--danger,#e5484d);color:#fff">❌ 没过</span>' };

export async function renderLeetcode(container, refresh) {
  const [st, folder, problems] = await Promise.all([
    api('/api/leetcode/status'), api('/api/leetcode/folder'), api('/api/career/problems'),
  ]);

  // ---- 力扣同步（自就业页迁入） ----
  const lcCard = el(`<div class="card" style="margin-bottom:16px"><div class="card-title">🧮 力扣同步
    <span class="hint">用户名与 Cookie 在 <a href="#/settings">设置页</a> 配置</span></div>`);
  const cached = st.cache;
  if (cached && cached.progress) {
    const p = cached.progress;
    const diffLine = `简单 ${p.easy ?? 0} · 中等 ${p.medium ?? 0} · 困难 ${p.hard ?? 0}` +
      (p.attempted != null ? ` · 尝试未过 ${p.attempted}` : '');
    lcCard.appendChild(el(`<div>
      <div class="stat-row">
      <div class="stat"><b>${p.solved ?? "?"}</b><span>已通过</span></div>
      <div class="stat"><b>${problems.stats.total}</b><span>刷题记录(含同步)</span></div>
      <div class="stat"><b>${problems.stats.topics.length}</b><span>题型覆盖</span></div></div>
      <div style="color:var(--muted);font-size:12px;margin-top:6px">${diffLine} · 上次同步 ${cached.synced_at}${cached.cookie_ok ? "" : " · ⚠️ Cookie 过期，最近提交未同步"}</div>
      </div>`));
  } else {
    lcCard.appendChild(el(`<p style="font-size:13px;color:var(--muted);margin:6px 0">
      未配置力扣同步。去 <a href="#/settings">设置页</a> 填力扣用户名+Cookie 后，这里自动展示通过数与难度分布，并把最近 AC 同步进刷题记录。</p>`));
  }
  const syncBtn = el('<button class="btn" style="margin-top:8px">🔄 立即同步</button>');
  syncBtn.onclick = async () => {
    toast("同步中…");
    try { const r = await api('/api/leetcode/sync', { method: 'POST' });
      if (r.error) toast(r.error, false); else toast(`同步完成：新导入 ${r.recent_imported} 条记录`); refresh();
    } catch (e) { toast(e.message, false); }
  };
  lcCard.appendChild(syncBtn);
  lcCard.appendChild(el(`<div class="inline-form" style="margin-top:10px">
    <input placeholder="手动记一题（题目名）" style="width:150px" class="q-title">
    <select class="q-topic">${["哈希", "链表", "二叉树", "DP", "图", "其他"].map(t => `<option>${t}</option>`).join("")}</select>
    <button class="btn q-add">打卡</button></div>`));
  lcCard.querySelector(".q-add").onclick = async () => {
    const t = lcCard.querySelector(".q-title").value.trim();
    if (!t) return;
    await api('/api/career/problems', { method: 'POST', body: { title: t, topic: lcCard.querySelector(".q-topic").value } });
    toast("已打卡"); refresh();
  };
  container.appendChild(lcCard);

  // ---- 本地刷题文件夹 ----
  const fCard = el(`<div class="card" style="margin-bottom:16px"><div class="card-title">📚 本地刷题文件夹
    <span class="hint">绑定力扣学习文件夹（learning/ 四件套），作为问答与复习的资料源</span></div>
    <div class="inline-form">
      <input placeholder="文件夹路径，如 D:\\leetcode" style="flex:1" class="f-path" value="${escape(folder.path || "")}">
      <button class="btn btn-primary f-save">保存绑定</button>
      <button class="btn f-refresh">刷新状态</button></div>
    <div class="f-status" style="font-size:13px;margin-top:8px"></div></div>`);
  const fLine = () => {
    const box = fCard.querySelector(".f-status");
    if (!folder.bound) { box.innerHTML = '<span style="color:var(--muted)">未绑定——绑定后可基于学习笔记「问 AI」与「AI 考我」</span>'; return; }
    if (!folder.exists) { box.innerHTML = '<span style="color:var(--amber)">⚠️ 路径不存在，请检查</span>'; return; }
    box.innerHTML = folder.has_learning
      ? `✅ 已绑定 <code>${escape(folder.path)}</code> · 学习笔记 <b>${folder.cards}</b> 卡 · ${folder.chapters} 章节 · <b style="color:var(--amber)">待复习 ${folder.due}</b>`
      : `已绑定 <code>${escape(folder.path)}</code> · ${folder.files} 个可读文件 · 未发现 learning/ 学习体系（问 AI 可用，AI 考我不可用）`;
  };
  fLine();
  fCard.querySelector(".f-save").onclick = async () => {
    const path = fCard.querySelector(".f-path").value.trim();
    try {
      await api('/api/config', { method: 'PUT', body: { leetcode: { folder: path } } });
      toast("已保存"); refresh();
    } catch (e) { toast(e.message, false); }
  };
  fCard.querySelector(".f-refresh").onclick = refresh;
  container.appendChild(fCard);

  container.appendChild(renderAskCard());
  container.appendChild(renderQuizCard());
}

// ---- 💬 问 AI（F31）：基于本地学习笔记与文件夹资料作答 ----
function renderAskCard() {
  const card = el(`<div class="card" style="margin-bottom:16px"><div class="card-title">💬 问 AI
    <span class="hint">基于本地学习笔记与文件夹资料作答；资料不足时 AI 用自身知识补充</span></div>
    <div class="qa-log" style="max-height:420px;overflow:auto">
      <div class="empty" style="padding:10px"><div style="font-size:13px">刷题卡壳当场问，如：3Sum 的去重为什么要放在 j 上？</div></div>
    </div>
    <div class="inline-form" style="margin-top:8px">
      <input placeholder="输入问题回车发送" style="flex:1" class="qa-q">
      <button class="btn btn-primary qa-send">发送</button></div></div>`);
  const log = card.querySelector('.qa-log');
  const input = card.querySelector('.qa-q');
  const send = card.querySelector('.qa-send');
  const ask = async () => {
    const q = input.value.trim();
    if (!q) return toast('请输入问题', false);
    const empty = log.querySelector('.empty');
    if (empty) empty.remove();
    log.appendChild(el(`<div style="text-align:right;margin:8px 0 4px"><span class="badge" style="background:var(--accent);color:var(--accent-text)">${escape(q)}</span></div>`));
    input.value = '';
    const pending = el('<div style="color:var(--muted);font-size:12.5px;margin:4px 0">思考中…</div>');
    log.appendChild(pending);
    log.scrollTop = log.scrollHeight;
    send.disabled = true;
    try {
      const r = await api('/api/leetcode/ask', { method: 'POST', body: { question: q } });
      pending.remove();
      const srcs = (r.sources || []).slice(0, 8).map(s =>
        s.card ? `<span class="badge gray">🃏 ${escape(s.card)}</span>`
               : `<span class="badge gray">📎 ${escape(s.name)}</span>`).join(' ');
      log.appendChild(el(`<div style="margin:4px 0 12px;font-size:13.5px;line-height:1.65;white-space:pre-wrap">${escape(r.answer)}
        <div style="margin-top:5px">${srcs}${srcs ? ' ' : ''}${r.ai_used ? '' : '<span class="badge amber">AI 未配置·资料参考</span>'}</div></div>`));
      log.scrollTop = log.scrollHeight;
    } catch (e) { pending.remove(); toast(e.message, false); }
    send.disabled = false;
  };
  send.onclick = ask;
  input.onkeydown = (e) => { if (e.key === 'Enter') ask(); };
  return card;
}

// ---- 📝 AI 考我（F32）：lj.py 挑到期卡 → 逐题作答 → AI 判分 → 回写记忆曲线 ----
function renderQuizCard() {
  const card = el(`<div class="card" style="margin-bottom:16px"><div class="card-title">📝 AI 考我（到期复习）
    <span class="hint">从本地复习清单挑到期卡片 · 判分结果自动回写记忆曲线（答对进阶段/答错重置/含糊标薄弱）</span></div>
    <div class="q-box"></div></div>`);
  const box = card.querySelector('.q-box');
  const setup = () => {
    box.innerHTML = '';
    box.appendChild(el(`<div class="inline-form">
      <select class="q-n"><option value="3">3 张</option><option value="5" selected>5 张</option><option value="8">8 张</option></select>
      <button class="btn btn-primary q-start">挑到期卡开考</button></div>
      <div style="font-size:12px;color:var(--muted);margin-top:6px">需要已绑定含 learning/ 体系的文件夹；没有到期卡时自动从待复习池里挑</div>`));
    box.querySelector('.q-start').onclick = start;
  };
  const start = async () => {
    const n = +box.querySelector('.q-n').value;
    box.innerHTML = '<div style="color:var(--muted);font-size:12.5px;padding:6px 0">挑卡中…</div>';
    let r;
    try { r = await api('/api/leetcode/review/pick', { method: 'POST', body: { n } }); }
    catch (e) { toast(e.message, false); return setup(); }
    if (!r.cards || !r.cards.length) {
      toast(r.msg || '没有可复习的卡片', false);
      return setup();
    }
    run(r.cards);
  };
  const run = (cards) => {
    box.innerHTML = '';
    let i = 0;
    const cnt = { pass: 0, fuzzy: 0, fail: 0 };
    const step = () => {
      box.innerHTML = '';
      if (i >= cards.length) {
        box.appendChild(el(`<div class="empty" style="padding:14px"><span class="icon">✅</span>
          <div class="title">本轮完成（结果已回写复习清单）</div>
          <div style="margin-top:4px">✅ 过 ${cnt.pass} · 🤔 含糊 ${cnt.fuzzy} · ❌ 没过 ${cnt.fail}</div>
          <button class="btn btn-primary q-again" style="margin-top:10px">🔄 再来一轮</button></div>`));
        box.querySelector('.q-again').onclick = setup;
        return;
      }
      const c = cards[i];
      box.appendChild(el(`<div style="display:flex;justify-content:space-between;color:var(--muted);font-size:12px">
        <span>第 ${i + 1} / ${cards.length} 张 · ${escape(c.chapter)} · ${escape(c.id)}</span>
        <span>${c.due ? `到期 ${escape(c.due)}` : ''}</span></div>
        <div style="font-size:16px;padding:10px 0;line-height:1.6">${escape(c.q)}</div>
        ${c.a ? `<details style="margin:6px 0"><summary style="font-size:12px;color:var(--muted);cursor:pointer">先作答再看答案</summary>
          <div style="font-size:12.5px;color:var(--muted);white-space:pre-wrap;max-height:220px;overflow:auto;border:1px solid var(--line);border-radius:6px;padding:8px;margin-top:4px">${escape(c.a)}</div></details>` : ''}
        <textarea rows="4" class="q-ans" placeholder="写下你的回答（对照卡片要点，答完提交判分）…" style="width:100%"></textarea>
        <div style="text-align:right;margin-top:6px"><button class="btn btn-primary q-submit">提交判分</button></div>
        <div class="q-res"></div>`));
      const ta = box.querySelector('.q-ans');
      ta.focus();
      box.querySelector('.q-submit').onclick = async () => {
        const ans = ta.value.trim();
        if (!ans) return toast('先写点回答', false);
        const res = box.querySelector('.q-res');
        res.innerHTML = '<div style="color:var(--muted);font-size:12.5px">判分中…</div>';
        let g;
        try {
          g = await api('/api/leetcode/review/grade', { method: 'POST',
            body: { question: c.q, answer: ans, ref: c.ref || '' } });
        } catch (e) { toast(e.message, false); res.innerHTML = ''; return; }
        if (g.verdict) return markAndNext(g, { pass: 'pass', fuzzy: 'partial', fail: 'fail' }[g.verdict], 'AI 判分');
        selfGrade(res, ta);
      };
      const markAndNext = (g, result, label) => {
        const res = box.querySelector('.q-res');
        let markMsg = '';
        api('/api/leetcode/review/mark', { method: 'POST', body: { id: c.id, result } })
          .then(m => { markMsg = m.msg || '已回写'; paint(); })
          .catch(e => { markMsg = `⚠️ 回写失败：${e.message}`; paint(); });
        const paint = () => {
          const sub = box.querySelector('.q-submit');
          if (sub) sub.style.display = 'none';
          const ta2 = box.querySelector('.q-ans');
          if (ta2) ta2.disabled = true;
          cnt[result === 'pass' ? 'pass' : result === 'partial' ? 'fuzzy' : 'fail']++;
          res.innerHTML = `<div style="margin-top:8px;font-size:13.5px">${chip[result === 'pass' ? 'pass' : result === 'partial' ? 'fuzzy' : 'fail']}
            ${g.comment ? `<span style="margin-left:6px">${escape(g.comment)}</span>` : ''}
            <span class="badge gray" style="margin-left:6px">📌 ${escape(label)} · ${escape(markMsg || '回写中…')}</span></div>
            <div style="text-align:right;margin-top:8px"><button class="btn btn-primary q-next">下一张 →</button></div>`;
          res.querySelector('.q-next').onclick = () => { i++; step(); };
        };
        paint();
      };
      const selfGrade = (res, ta2) => {
        const sub = box.querySelector('.q-submit');
        if (sub) sub.style.display = 'none';
        if (ta2) ta2.disabled = true;
        res.innerHTML = `<div style="margin-top:8px;font-size:13px">AI 未配置——对照卡片自评：
          <button class="btn sg-pass">✅ 过</button>
          <button class="btn sg-fuzzy">🤔 含糊</button>
          <button class="btn sg-fail">❌ 没过</button></div>`;
        const bind = (sel, result) => res.querySelector(sel).onclick = () => markAndNext({}, result, '自评');
        bind('.sg-pass', 'pass'); bind('.sg-fuzzy', 'partial'); bind('.sg-fail', 'fail');
      };
    };
    step();
  };
  setup();
  return card;
}

export default {
  id: 'leetcode',
  title: '力扣',
  icon: '🧮',
  render: renderLeetcode,
};
