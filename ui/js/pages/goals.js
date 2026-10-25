// 目标规划：目标卡 + 里程碑进度 + 倒计时 + 截止日设置
import { api } from '../api.js';
import { el, escape, toast, todayStr, confirmBox} from './kit.js';

export default {
  id: 'goals',
  title: '目标规划',
  icon: '🎯',
  async render(container, rerender) {
    const refresh = () => rerender ? rerender() : location.reload();
    const { goals, archived } = await api('/api/goals');

    container.appendChild(el(`
      <div class="page-head"><h1>目标规划</h1>
      <p>目标 → 里程碑 → 进度；完成任务自动推进关联里程碑</p></div>`));

    // 空状态：一键初始化预置目标
    if (!goals.length) {
      const card = el(`<div class="card"><div class="empty">
        <span class="icon">🌱</span><div class="title">还没有目标</div>
        <div>可一键初始化四条主线目标：后端实习 / 小论文 / Agent 项目 / 雅思</div>
        <button class="btn btn-primary seed-btn" style="margin-top:14px">⚡ 一键初始化预置目标</button>
      </div></div>`);
      card.querySelector('.seed-btn').onclick = async () => {
        try { await api('/api/goals/seed', { method: 'POST' }); toast('已初始化'); refresh(); }
        catch (e) { toast(e.message, false); }
      };
      container.appendChild(card);
      return;
    }

    // 新建目标
    const add = el(`<div class="card" style="margin-bottom:16px"><div class="card-title">➕ 新建目标</div>
      <div class="inline-form">
        <input id="g-title" placeholder="目标名称" style="width:180px">
        <input id="g-ms" placeholder="里程碑（逗号分隔，如：选题, 开发, 上线）" style="flex:1">
        <input id="g-dl" type="date" style="width:150px">
        <button class="btn btn-primary" id="g-save">保存</button>
      </div></div>`);
    add.querySelector('#g-save').onclick = async () => {
      const title = add.querySelector('#g-title').value.trim();
      if (!title) return toast('请填目标名称', false);
      const ms = add.querySelector('#g-ms').value.split(/[,，]/).map(s => s.trim()).filter(Boolean)
        .map(m => [m, 1]);
      try {
        await api('/api/goals', { method: 'POST', body: { title, milestones: ms, deadline: add.querySelector('#g-dl').value || null } });
        toast('目标已创建'); refresh();
      } catch (e) { toast(e.message, false); }
    };
    container.appendChild(add);

    // 目标卡
    const grid = el('<div class="grid cols-2"></div>');
    goals.forEach(g => {
      const card = el(`<div class="card">
        <div class="card-title" style="display:flex;align-items:center;gap:6px">
          <span style="flex:1;min-width:0">${escape(g.title)}</span>
          ${g.days_left != null ? `<span class="badge ${g.days_left < 30 ? 'amber' : ''}">⏳ 剩 ${g.days_left} 天</span>` : '<span class="badge gray">无截止日</span>'}
          <button class="btn arc" style="padding:2px 8px;font-size:12px" title="做完收起，随时可恢复">📦</button>
          <button class="btn del" style="padding:2px 8px;font-size:12px">✕</button>
        </div>
        <div style="font-size:12.5px;color:var(--muted);margin-bottom:8px">${escape(g.description || '')}</div>
        <div class="progress" style="margin-bottom:6px"><i style="width:${g.progress}%"></i></div>
        <div style="font-size:12px;color:var(--muted);margin-bottom:10px">总进度 ${g.progress}%</div>
        <div class="ms-box"></div>
        <div class="inline-form"><input type="date" class="dl-input" style="width:145px">
          <button class="btn dl-btn">设置截止日</button></div>
      </div>`);
      card.querySelector(".arc").onclick = async () => {
        if (!(await confirmBox(`归档目标「${g.title}」？归档后不再出现在主列表和工作台，可随时恢复。`))) return;
        await api(`/api/goals/${g.id}/archive`, { method: 'PUT', body: { archived: true } });
        toast("已归档（见页面底部归档区）"); refresh();
      };
      card.querySelector(".del").onclick = async () => {
        if (!(await confirmBox(`彻底删除目标「${g.title}」？连同里程碑一并删除，不可恢复。`))) return;
        await api(`/api/goals/${g.id}`, { method: 'DELETE' });
        toast("已删除"); refresh();
      };
      const msBox = card.querySelector('.ms-box');
      g.milestones.forEach(m => {
        const pct = m.total ? Math.round(m.done_count / m.total * 100) : 0;
        const row = el(`
          <div style="display:flex;align-items:center;gap:8px;padding:5px 0;font-size:13px">
            <span class="dot ${pct >= 100 ? '' : 'off'}"></span>
            <span style="flex:1">${escape(m.title)}</span>
            <span style="color:var(--muted);font-size:12px">${m.done_count}/${m.total}</span>
            <button class="btn ms-dn" style="padding:1px 7px;font-size:12px">−</button>
            <button class="btn ms-up" style="padding:1px 7px;font-size:12px">＋</button>
          </div>`);
        row.querySelector(".ms-up").onclick = async () => {
          await api(`/api/goals/milestones/${m.id}/bump`, { method: 'POST', body: { delta: 1 } });
          refresh();
        };
        row.querySelector(".ms-dn").onclick = async () => {
          await api(`/api/goals/milestones/${m.id}/bump`, { method: 'POST', body: { delta: -1 } });
          refresh();
        };
        msBox.appendChild(row);
      });
      const dlInput = card.querySelector('.dl-input');
      dlInput.value = g.deadline || '';
      card.querySelector('.dl-btn').onclick = async () => {
        try {
          await api(`/api/goals/${g.id}/deadline`, { method: 'PUT', body: { deadline: dlInput.value || null } });
          toast('截止日已更新'); refresh();
        } catch (e) { toast(e.message, false); }
      };
      grid.appendChild(card);
    });
    container.appendChild(grid);

    // ---- 归档区 ----
    if (archived?.length) {
      const arc = el(`<div class="card" style="margin-top:16px"><div class="card-title">📦 目标归档区
        <span class="hint">不再推进的目标 · 可恢复或彻底删除</span></div></div>`);
      archived.forEach(g => {
        const row = el(`<div style="display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid var(--line);font-size:13px">
          <span class="badge gray">归档</span>
          <div style="flex:1;min-width:0"><b>${escape(g.title)}</b>
            <span style="color:var(--muted)"> · 最终进度 ${g.progress}% · ${g.milestones.length} 个里程碑</span></div>
          <button class="btn rst" style="padding:3px 10px;font-size:12px">↩ 恢复</button>
          <button class="btn dl" style="padding:3px 10px;font-size:12px">✕ 彻底删除</button>
        </div>`);
        row.querySelector(".rst").onclick = async () => {
          await api(`/api/goals/${g.id}/archive`, { method: 'PUT', body: { archived: false } });
          toast("已恢复"); refresh();
        };
        row.querySelector(".dl").onclick = async () => {
          if (!(await confirmBox(`彻底删除目标「${g.title}」？不可恢复。`))) return;
          await api(`/api/goals/${g.id}`, { method: 'DELETE' });
          toast("已彻底删除"); refresh();
        };
        arc.appendChild(row);
      });
      container.appendChild(arc);
    }

    // 小贴士：今天的日期供参考
    container.appendChild(el(`<p style="color:var(--muted);font-size:12.5px;margin-top:14px">今天是 ${todayStr()} · 雅思考试时间未定，默认不设倒计时</p>`));
  },
};
