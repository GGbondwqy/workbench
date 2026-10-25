// 项目学习 Tab：项目卡 + 里程碑 + 技术栈/亮点/面试问答 + 简历版本
import { api } from '../../api.js';
import { el, escape, toast, confirmBox } from '../kit.js';

const STATUS = [["building", "开发中"], ["choosing", "选题中"], ["online", "已上线"], ["paused", "暂缓"]];

export async function renderProjects(container, refresh) {
  const { projects, archived } = await api('/api/projects');
  const { items: resumes } = await api('/api/resumes');

  const add = el(`<div class="card" style="margin-bottom:14px"><div class="inline-form" style="margin:0">
    <input placeholder="新项目名称（如 DevFlow AI / 智能运维Agent）" style="flex:1" class="p-name">
    <button class="btn btn-primary p-add">＋ 新建项目</button></div></div>`);
  add.querySelector(".p-add").onclick = async () => {
    const name = add.querySelector(".p-name").value.trim();
    if (!name) return toast("请填项目名", false);
    await api('/api/projects', { method: 'POST', body: { name } });
    toast("已创建（含 选题/开发/上线 默认里程碑）"); refresh();
  };
  container.appendChild(add);

  const grid = el('<div class="grid cols-2"></div>');
  for (const p of projects) {
    const card = el(`<div class="card">
      <div class="card-title" style="display:flex;align-items:center;gap:8px">
        <span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${escape(p.name)}">${escape(p.name)}</span>
        <select class="st" style="padding:3px 6px;font-size:12px">
          ${STATUS.map(([v, l]) => `<option value="${v}" ${p.status === v ? "selected" : ""}>${l}</option>`).join("")}
        </select>
        <button class="btn arc" style="padding:3px 8px;font-size:12px" title="做完收起，作为学习资料保留">📦 归档</button>
        <button class="btn del" style="padding:3px 8px;font-size:12px">✕</button>
      </div>
      <div class="progress" style="margin:6px 0 4px"><i style="width:${p.progress}%"></i></div>
      <div style="font-size:12px;color:var(--muted);margin-bottom:8px">${p.progress}% · ${p.milestones.map(m => `${escape(m.title)} ${m.done_count}/${m.total}`).join(" · ")}</div>
      <div class="ms-btns" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px">
        ${p.milestones.map(m => `<button class="btn" data-ms="${m.id}" style="padding:3px 10px;font-size:12px">▸ ${escape(m.title)}</button>`).join("")}
      </div>
      <div class="tabs" style="display:flex;gap:6px;margin-bottom:8px">
        ${[["stack", "技术栈"], ["highlight", "亮点"], ["qa", "面试问答"]].map(([k, l]) =>
          `<button class="btn tab" data-k="${k}" style="padding:3px 10px;font-size:12px">${l}</button>`).join("")}
      </div>
      <div class="items"></div>
      <div class="inline-form" style="margin:6px 0 0">
        <input placeholder="标题/问题" style="width:150px" class="i-title">
        <input placeholder="内容/回答" style="flex:1" class="i-content">
        <button class="btn i-add">添加</button></div>
    </div>`);
    card.querySelector(".st").onchange = async () => {
      await api(`/api/projects/${p.id}/status`, { method: 'PUT', body: { status: card.querySelector(".st").value } });
      refresh();
    };
    card.querySelector(".arc").onclick = async () => {
      if (!(await confirmBox(`归档项目「${p.name}」？归档后收进下方归档区，作为学习资料保留，可随时恢复。`))) return;
      await api(`/api/projects/${p.id}/archive`, { method: 'PUT', body: { archived: true } });
      toast("已归档（可在下方归档区查看/恢复）"); refresh();
    };
    card.querySelector(".del").onclick = async () => {
      if (!(await confirmBox(`彻底删除项目「${p.name}」？连同里程碑、技术栈、亮点、面试问答一并删除，不可恢复。`))) return;
      await api(`/api/projects/${p.id}`, { method: 'DELETE' });
      toast("已删除"); refresh();
    };
    card.querySelectorAll("[data-ms]").forEach(b => b.onclick = async () => {
      await api(`/api/projects/${p.id}/milestones/${b.dataset.ms}/bump`, { method: 'POST' });
      toast("里程碑 +1"); refresh();
    });
    let curKind = "qa";
    const itemsBox = card.querySelector(".items");
    const loadItems = async () => {
      const r = await api(`/api/projects/${p.id}/items?kind=${curKind}`);
      itemsBox.innerHTML = "";
      r.items.slice(0, 6).forEach(it => itemsBox.appendChild(el(`
        <div style="display:flex;align-items:center;gap:6px;padding:6px 0;border-bottom:1px solid var(--line);font-size:13px">
          <div style="flex:1;min-width:0"><b>${escape(it.title)}</b>
          <div style="color:var(--muted)">${escape((it.content || "").slice(0, 100))}</div></div>
          <button class="btn it-del" style="padding:1px 7px;font-size:12px" title="删除条目">✕</button>
        </div>`)));
      itemsBox.querySelectorAll(".it-del").forEach((b, i) => b.onclick = async () => {
        const it = r.items[i];
        if (!(await confirmBox(`删除条目「${it.title || it.content || ""}」？`))) return;
        try { await api(`/api/items/${it.id}`, { method: 'DELETE' }); toast("已删除"); loadItems(); }
        catch (e) { toast(e.message, false); }
      });
      card.querySelectorAll(".tab").forEach(t => t.style.borderColor = t.dataset.k === curKind ? "var(--accent)" : "var(--line)");
    };
    card.querySelectorAll(".tab").forEach(t => t.onclick = () => { curKind = t.dataset.k; loadItems(); });
    card.querySelector(".i-add").onclick = async () => {
      const title = card.querySelector(".i-title").value.trim();
      const content = card.querySelector(".i-content").value.trim();
      if (!title && !content) return;
      await api(`/api/projects/${p.id}/items`, { method: 'POST', body: { kind: curKind, title, content } });
      card.querySelector(".i-title").value = ""; card.querySelector(".i-content").value = "";
      loadItems();
    };
    loadItems();
    grid.appendChild(card);
  }
  container.appendChild(grid);

  // ---- 归档区：做完的项目作为学习资料长期保留 ----
  const arc = el(`<div class="card" style="margin-top:16px"><div class="card-title">📦 归档区
    <span class="hint">${archived.length ? "做完/搁置的项目 · 可恢复或彻底删除" : "暂无归档项目——项目卡上点『归档』收进来"}</span></div></div>`);
  archived.forEach(p => {
    const row = el(`<div style="display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid var(--line);font-size:13px">
      <span class="badge gray">${p.status_cn || "已归档"}</span>
      <div style="flex:1;min-width:0">
        <b>${escape(p.name)}</b>
        <span style="color:var(--muted)"> · 完成度 ${p.progress}% · ${p.milestones.map(m => `${escape(m.title)} ${m.done_count}/${m.total}`).join(" / ")}</span>
      </div>
      <button class="btn rst" style="padding:3px 10px;font-size:12px">↩ 恢复</button>
      <button class="btn dl" style="padding:3px 10px;font-size:12px">✕ 彻底删除</button>
    </div>`);
    row.querySelector(".rst").onclick = async () => {
      await api(`/api/projects/${p.id}/archive`, { method: 'PUT', body: { archived: false } });
      toast("已恢复到项目列表"); refresh();
    };
    row.querySelector(".dl").onclick = async () => {
      if (!(await confirmBox(`彻底删除归档项目「${p.name}」？所有资料一并删除，不可恢复。`))) return;
      await api(`/api/projects/${p.id}`, { method: 'DELETE' });
      toast("已彻底删除"); refresh();
    };
    arc.appendChild(row);
  });
  container.appendChild(arc);

  // 简历版本
  const rc = el(`<div class="card" style="margin-top:16px"><div class="card-title">📄 简历版本管理</div>
    <div class="inline-form" style="margin:0"><input placeholder="版本备注（如 v3-加Agent项目描述）" style="flex:1" class="r-note">
    <button class="btn r-add">登记新版本</button></div><div class="r-list"></div></div>`);
  rc.querySelector(".r-add").onclick = async () => {
    const note = rc.querySelector(".r-note").value.trim();
    if (!note) return;
    await api('/api/projects/0/items', { method: 'POST', body: { kind: "resume", title: `v${resumes.length + 1}`, content: note } });
    toast("已登记"); refresh();
  };
  const rl = rc.querySelector(".r-list");
  (resumes.length ? resumes : []).forEach(r => rl.appendChild(el(`
    <div style="display:flex;align-items:center;gap:6px;padding:6px 0;border-bottom:1px solid var(--line);font-size:13px">
      <div style="flex:1;min-width:0"><b>${escape(r.title)}</b> ${escape(r.content)}
        <span style="color:var(--muted)">${r.created_at}</span></div>
      <button class="btn r-del" style="padding:1px 7px;font-size:12px" title="删除版本记录">✕</button></div>`)));
  rl.querySelectorAll(".r-del").forEach((b, i) => b.onclick = async () => {
    const r = resumes[i];
    if (!(await confirmBox(`删除简历版本「${r.title} ${r.content}」？`))) return;
    try { await api(`/api/items/${r.id}`, { method: 'DELETE' }); toast("已删除"); refresh(); }
    catch (e) { toast(e.message, false); }
  });
  if (!resumes.length) rl.appendChild(el('<div class="empty" style="padding:8px"><div style="font-size:13px">还没有版本记录</div></div>'));
  container.appendChild(rc);
}
