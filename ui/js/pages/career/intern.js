// 实习准备 Tab：面试日程（联动工作台）/ 投递看板 / 面试复盘 / Offer 对比 / 力扣
import { api } from '../../api.js';
import { el, escape, toast, todayStr, confirmBox } from '../kit.js';

const PIPE = [["applied", "已投递"], ["written", "笔试"], ["interview1", "一面"],
              ["interview2", "二面"], ["hr", "HR面"], ["offer", "Offer"], ["closed", "已结束"]];

export async function renderIntern(container, refresh) {
  const [{ items: sch }, apps, { items: reviews }, { items: offers }] = await Promise.all([
    api('/api/interviews'), api('/api/career/applications'), api('/api/interview-reviews'),
    api('/api/offers'),
  ]);

  // ---- 面试日程 ----
  const sCard = el(`<div class="card" style="margin-bottom:16px"><div class="card-title">⚠️ 面试日程
    <span class="hint">临近自动进工作台三件事</span></div><div class="s-list"></div>
    <div class="inline-form"><input type="datetime-local" class="s-at" style="width:200px">
    <input placeholder="公司" style="width:110px" class="s-co">
    <input placeholder="轮次（一面/笔试…）" style="width:130px" class="s-rd">
    <button class="btn btn-primary s-add">添加</button></div></div>`);
  const sList = sCard.querySelector(".s-list");
  if (!sch.length) sList.appendChild(el('<div class="empty" style="padding:8px"><div style="font-size:13px">暂无面试安排</div></div>'));
  sch.slice(0, 5).forEach(s => sList.appendChild(el(`
    <div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--line);font-size:13px">
      <span class="badge amber">${escape(s.meet_at)}</span>
      <b>${escape(s.company)}</b> <span style="color:var(--muted)">${escape(s.round || '')}</span>
      <span style="flex:1"></span><button class="btn s-del" style="padding:2px 8px;font-size:12px">✕</button></div>`)));
  sList.querySelectorAll(".s-del").forEach((b, i) => b.onclick = async () => {
    await api(`/api/interviews/${sch[i].id}`, { method: 'DELETE' }); refresh();
  });
  sCard.querySelector(".s-add").onclick = async () => {
    const at = sCard.querySelector(".s-at").value, co = sCard.querySelector(".s-co").value.trim();
    if (!at || !co) return toast("时间和公司必填", false);
    await api('/api/interviews', { method: 'POST', body: { meet_at: at.replace("T", " "), company: co, round: sCard.querySelector(".s-rd").value.trim() } });
    toast("已添加"); refresh();
  };
  container.appendChild(sCard);

  // ---- 力扣（v1.20 起独立页，这里留跳转） ----
  container.appendChild(el(`<div class="card" style="margin-bottom:16px"><div class="card-title">🧮 算法刷题 · 力扣</div>
    <div style="font-size:13px;color:var(--muted)">同步进度、本地刷题文件夹、问 AI 与到期复习已升级为独立页。
      <a href="#/leetcode">去力扣页 →</a></div></div>`));

  // ---- 投递看板 ----
  const bCard = el(`<div class="card" style="margin-bottom:16px"><div class="card-title">🏢 实习投递看板</div>
    <div class="inline-form"><input placeholder="公司" style="width:100px" class="a-co">
    <input placeholder="岗位" style="width:110px" class="a-pos">
    <button class="btn btn-primary a-add">新增投递</button></div></div>`);
  bCard.querySelector(".a-add").onclick = async () => {
    const co = bCard.querySelector(".a-co").value.trim(), pos = bCard.querySelector(".a-pos").value.trim();
    if (!co || !pos) return toast("公司岗位必填", false);
    await api('/api/career/applications', { method: 'POST', body: { company: co, position: pos } });
    refresh();
  };
  const board = el('<div class="board" style="margin-top:10px"></div>');
  const byStatus = {};
  apps.items.forEach(a => (byStatus[a.status] = byStatus[a.status] || []).push(a));
  PIPE.forEach(([key, label], pi) => {
    const col = el(`<div><div class="board-col-title"><span>${label}</span><span>${(byStatus[key] || []).length}</span></div></div>`);
    (byStatus[key] || []).forEach(a => {
      const c = el(`<div class="board-card"><b>${escape(a.company)}</b>${escape(a.position)}
        <div style="color:var(--muted);font-size:12px">${a.apply_date}</div>
        <div style="display:flex;gap:6px;margin-top:6px">
        ${key !== "offer" && key !== "closed" ? '<button class="btn adv" style="padding:2px 8px;font-size:12px">推进 →</button>' : ''}
        <button class="btn a-del" style="padding:2px 7px;font-size:12px" title="删除该投递">✕</button></div></div>`);
      const adv = c.querySelector(".adv");
      if (adv) adv.onclick = async () => {
        const next = PIPE[Math.min(pi + 1, 4)][0];
        await api(`/api/career/applications/${a.id}/advance`, { method: 'POST', body: { status: next } });
        refresh();
      };
      c.querySelector(".a-del").onclick = async () => {
        if (!(await confirmBox(`删除投递「${a.company} · ${a.position}」？
其推进轨迹将一并删除。`))) return;
        await api(`/api/career/applications/${a.id}`, { method: 'DELETE' });
        toast("已删除"); refresh();
      };
      col.appendChild(c);
    });
    board.appendChild(col);
  });
  bCard.appendChild(board);
  container.appendChild(bCard);

  const grid = el('<div class="grid cols-2" style="align-items:start"></div>');
  container.appendChild(grid);

  // ---- 面试复盘 ----
  const rCard = el(`<div class="card"><div class="card-title">📝 面试复盘</div>
    <div class="inline-form"><input placeholder="公司" style="width:90px" class="rv-co">
    <input placeholder="被问了什么（分号分隔）" style="flex:1" class="rv-q">
    <input placeholder="改进点" style="width:110px" class="rv-i">
    <button class="btn rv-add">记录</button></div><div class="rv-list"></div></div>`);
  rCard.querySelector(".rv-add").onclick = async () => {
    const co = rCard.querySelector(".rv-co").value.trim();
    if (!co) return toast("公司必填", false);
    await api('/api/interview-reviews', { method: 'POST', body: { date: todayStr(), company: co,
      questions: rCard.querySelector(".rv-q").value.trim(), improve: rCard.querySelector(".rv-i").value.trim() } });
    toast("已记录"); refresh();
  };
  const rvList = rCard.querySelector(".rv-list");
  if (!reviews.length) rvList.appendChild(el('<div class="empty" style="padding:8px"><div style="font-size:13px">暂无复盘</div></div>'));
  reviews.slice(0, 8).forEach(r => rvList.appendChild(el(`
    <div style="padding:7px 0;border-bottom:1px solid var(--line);font-size:13px">
      <div style="display:flex;align-items:center;gap:6px"><b style="flex:1">${escape(r.company)}</b>
        <span style="color:var(--muted)">${r.date}</span>
        <button class="btn rv-del" style="padding:1px 7px;font-size:12px">✕</button></div>
      <div>${escape((r.questions || "").slice(0, 90))}</div>
      ${r.improve ? `<div style="color:var(--amber)">▸ ${escape(r.improve)}</div>` : ""}</div>`)));
  rvList.querySelectorAll(".rv-del").forEach((b, i) => b.onclick = async () => {
    const r = reviews[i];
    if (!(await confirmBox(`删除「${r.company}」的面试复盘？`))) return;
    await api(`/api/interview-reviews/${r.id}`, { method: 'DELETE' });
    toast("已删除"); refresh();
  });
  grid.appendChild(rCard);

  // ---- Offer 对比 ----
  const oCard = el(`<div class="card"><div class="card-title">⚖️ Offer 对比器</div>
    <div class="inline-form"><input placeholder="公司" style="width:80px" class="o-co">
    <input placeholder="薪资(如 350/d)" style="width:90px" class="o-sa">
    <input placeholder="方向" style="width:80px" class="o-di">
    <select class="o-sc">${[5, 4, 3, 2, 1].map(n => `<option value="${n}" ${n === 3 ? "selected" : ""}>${n}★</option>`).join("")}</select>
    <button class="btn o-add">加入</button></div><div class="o-list"></div></div>`);
  oCard.querySelector(".o-add").onclick = async () => {
    const co = oCard.querySelector(".o-co").value.trim();
    if (!co) return;
    await api('/api/offers', { method: 'POST', body: { company: co, salary: oCard.querySelector(".o-sa").value.trim(),
      direction: oCard.querySelector(".o-di").value.trim(), score: +oCard.querySelector(".o-sc").value } });
    refresh();
  };
  const ol = oCard.querySelector(".o-list");
  if (!offers.length) ol.appendChild(el('<div class="empty" style="padding:8px"><div style="font-size:13px">暂无 offer（祝早日用上）</div></div>'));
  offers.forEach(o => ol.appendChild(el(`
    <div class="board-card" style="display:flex;gap:10px;align-items:center">
      <b style="margin:0">${escape(o.company)}</b>
      <span>${escape(o.salary || "")} ${escape(o.direction || "")}</span>
      <span class="badge amber" style="margin-left:auto">${"★".repeat(o.score)}</span>
      <button class="btn o-del" style="padding:2px 8px;font-size:12px">✕</button></div>`)));
  ol.querySelectorAll(".o-del").forEach((b, i) => b.onclick = async () => {
    await api(`/api/offers/${offers[i].id}`, { method: 'DELETE' }); refresh();
  });
  grid.appendChild(oCard);
}
