// 工作台首页：今日任务（可增改删）+ 目标进度 + 八股速览（v1.3 撤时间轴/复盘；v1.6 撤三件事建议）
import { api } from '../api.js';
import { el, escape, toast, todayStr, confirmBox} from './kit.js';

function greeting() {
  const h = new Date().getHours();
  if (h < 6) return '夜深了';
  if (h < 9) return '早上好';
  if (h < 12) return '上午好';
  if (h < 14) return '中午好';
  if (h < 18) return '下午好';
  return '晚上好';
}

export default {
  id: 'dashboard',
  title: '工作台',
  icon: '🏠',
  async render(container, rerender) {
    let d;
    try {
      d = await api('/api/dashboard');
    } catch (e) {
      container.appendChild(el(`<div class="card"><div class="empty"><span class="icon">⚠️</span>
        <div class="title">服务未连接</div><div>请先运行 start.bat 启动服务后刷新</div></div></div>`));
      return;
    }
    const refresh = () => rerender ? rerender() : location.reload();
    container.appendChild(el(`
      <div class="page-head">
        <h1>${greeting()}，继续加油 🌱</h1>
        <p>今日任务 ${d.task_stats.done}/${d.task_stats.total} 已完成 ·
           待复习卡片 ${d.review_due ?? 0} 张${
             d.upcoming_interviews?.length ? ` · ⚠️ <b style="color:var(--amber)">${escape(d.upcoming_interviews[0].company)}面试 ${d.upcoming_interviews[0].days_left} 天后</b>` : ""}${
             d.upcoming_mocks?.length ? ` · 🗓 模考 ${d.upcoming_mocks[0].date}` : ""}</p>
      </div>`));

    const wrap = el('<div class="grid cols-2" style="align-items:start"></div>');
    container.appendChild(wrap);
    const left = el('<div style="display:flex;flex-direction:column;gap:16px;min-width:0"></div>');
    const right = el('<div style="display:flex;flex-direction:column;gap:16px;min-width:0"></div>');
    wrap.appendChild(left); wrap.appendChild(right);

    // ---- 今日任务：勾选 + 行内编辑 + 删除 ----
    const taskCard = el(`<div class="card"><div class="card-title">✅ 今日任务
      <span class="hint">随时可改：点✎改标题/优先级，点✕删除</span></div></div>`);
    const listBox = el('<div></div>');
    if (!d.tasks.length) listBox.appendChild(el('<div class="empty" style="padding:12px"><div style="font-size:13px">今天还没有任务</div></div>'));
    d.tasks.forEach(t => {
      const row = el(`<div class="check-item ${t.status === 'done' ? 'done' : ''}">
        <button class="tick ${t.status === 'done' ? 'on' : ''}">✓</button>
        <div style="flex:1;min-width:0"><div class="t view">${escape(t.title)}</div>
          <div class="edit" style="display:none"><input class="e-title" style="width:100%" value="${escape(t.title)}">
            <div class="inline-form" style="margin-top:6px">
              <select class="e-pri">
                <option value="high" ${t.priority === 'high' ? 'selected' : ''}>高</option>
                <option value="mid" ${t.priority === 'mid' || !t.priority ? 'selected' : ''}>中</option>
                <option value="low" ${t.priority === 'low' ? 'selected' : ''}>低</option>
              </select>
              <button class="btn btn-primary e-save" style="padding:3px 10px">保存</button>
            </div></div></div>
        ${t.priority === 'high' ? '<span class="badge amber">高</span>' : ''}
        <span style="color:var(--muted);font-size:12px">${t.source === 'advisor' ? '导师' : t.source === 'plan' ? '计划' : t.source === 'course' ? '作业' : ''}</span>
        <button class="btn t-edit" style="padding:2px 7px;font-size:12px">✎</button>
        <button class="btn t-del" style="padding:2px 7px;font-size:12px">✕</button>
      </div>`);
      row.querySelector('.tick').onclick = async () => {
        try {
          if (t.status !== 'done') { await api(`/api/tasks/${t.id}/complete`, { method: 'POST' }); toast('完成 +1'); }
          refresh();
        } catch (e) { toast(e.message, false); }
      };
      row.querySelector('.t-edit').onclick = () => {
        const v = row.querySelector('.view'), ed = row.querySelector('.edit');
        const editing = ed.style.display === 'none';
        v.style.display = editing ? 'none' : '';
        ed.style.display = editing ? '' : 'none';
      };
      row.querySelector('.e-save').onclick = async () => {
        const title = row.querySelector('.e-title').value.trim();
        if (!title) return toast('标题不能为空', false);
        try {
          await api(`/api/tasks/${t.id}`, { method: 'PUT',
            body: { title, priority: row.querySelector('.e-pri').value } });
          toast('已更新'); refresh();
        } catch (e) { toast(e.message, false); }
      };
      row.querySelector('.t-del').onclick = async () => {
        if (!(await confirmBox(`删除任务「${t.title}」？`))) return;
        try { await api(`/api/tasks/${t.id}`, { method: 'DELETE' }); toast('已删除'); refresh(); }
        catch (e) { toast(e.message, false); }
      };
      listBox.appendChild(row);
    });
    taskCard.appendChild(listBox);
    const addForm = el(`<div class="inline-form"><input placeholder="添加任务，回车保存" style="flex:1">
      <select><option value="mid">中</option><option value="high">高</option><option value="low">低</option></select></div>`);
    const input = addForm.querySelector('input');
    input.onkeydown = async (e) => {
      if (e.key === 'Enter' && input.value.trim()) {
        try {
          await api('/api/tasks', { method: 'POST', body: { title: input.value.trim(), plan_date: todayStr(), priority: addForm.querySelector('select').value } });
          toast('已添加'); refresh();
        } catch (err) { toast(err.message, false); }
      }
    };
    taskCard.appendChild(addForm);
    left.appendChild(taskCard);

    // ---- 目标进度 ----
    const goalCard = el(`<div class="card"><div class="card-title">🎯 目标进度</div></div>`);
    (d.goals || []).forEach(g => {
      goalCard.appendChild(el(`
        <div style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
            <span>${escape(g.title)}</span>
            <span style="color:var(--muted)">${g.days_left != null ? `剩 ${g.days_left} 天 · ` : ''}${g.progress}%</span>
          </div>
          <div class="progress"><i style="width:${g.progress}%"></i></div>
        </div>`));
    });
    if (!d.goals?.length) {
      goalCard.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">还没有目标，去「目标规划」初始化</div></div>'));
    }
    right.appendChild(goalCard);

    // ---- 八股今日速览 ----
    if (d.kb_plan?.available) {
      right.appendChild(el(`<div class="card"><div class="card-title">📖 八股进度</div>
        <div style="font-size:13px;color:var(--muted)">剩余 ${d.kb_plan.remaining} 篇未读 · 今日已读 ${d.kb_plan.today_done || 0} 篇
        <a href="#/career/bagu" style="margin-left:6px">去阅读 →</a></div></div>`));
    }
  },
};
