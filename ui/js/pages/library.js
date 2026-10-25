// 资料库：八股搜索/阅读/问答 + 收藏夹（v1.11：知识库分库切换）
import { api } from '../api.js';
import { el, escape, toast, mdToHtml, confirmBox } from './kit.js';

const LIB_CN = { bagu: '八股库', mianjing: '面经库', grad: '研究生库' };
const LIBS = [['', '全部'], ['bagu', '八股库'], ['mianjing', '面经库'], ['grad', '研究生库']];

export default {
  id: 'library',
  title: '资料库',
  icon: '📚',
  async render(container, rerender) {
    const refresh = () => rerender ? rerender() : location.reload();
    const boot = await api('/api/bootstrap');
    container.appendChild(el(`
      <div class="page-head"><h1>资料库</h1>
      <p>${boot.kb.exists ? `八股文库已挂载 · ${boot.kb.articles} 篇` : '知识库未挂载（设置页可配置路径）'} · AI ${boot.ai.configured ? '已启用' : '未启用（问答返回相关文章）'}</p></div>`));

    // ---- 知识库切换（v1.11）：检索与提问只查所选库；"全部"跨库 ----
    let curLib = '';
    const libBar = el(`<div class="inline-form" style="margin-bottom:14px;flex-wrap:wrap">
      <span style="font-size:13px;color:var(--muted)">知识库：</span>
      ${LIBS.map(([v, l]) => `<button class="btn libbtn" data-lib="${v}">${l}</button>`).join('')}</div>`);
    const markLib = () => libBar.querySelectorAll('.libbtn').forEach(b =>
      b.style.cssText = b.dataset.lib === curLib
        ? 'border-color:var(--accent);color:var(--accent-text);font-weight:600' : '');
    libBar.querySelectorAll('.libbtn').forEach(b => b.onclick = () => {
      curLib = b.dataset.lib; markLib();
    });
    markLib();
    // 各库篇数（异步补上，不阻塞渲染）
    Promise.all(LIBS.filter(([v]) => v).map(([v]) =>
      api(`/api/kb/tree?lib=${v}`).then(r => [v, r.items.length]).catch(() => [v, 0])
    )).then(counts => counts.forEach(([v, n]) => {
      const b = libBar.querySelector(`[data-lib="${v}"]`);
      if (b) b.textContent = `${LIB_CN[v]} ${n}`;
    }));
    container.appendChild(libBar);

    // ---- 问答 ----
    const askCard = el(`<div class="card" style="margin-bottom:16px"><div class="card-title">💬 向知识库提问</div>
      <div class="inline-form"><input placeholder="如：TCP 三次握手每一步的作用？" style="flex:1">
      <button class="btn btn-primary ask-btn">提问</button></div><div class="answer"></div></div>`);
    const askInput = askCard.querySelector('input');
    const answerBox = askCard.querySelector('.answer');
    const doAsk = async () => {
      const q = askInput.value.trim();
      if (!q) return;
      answerBox.innerHTML = '<div style="color:var(--muted);padding:8px 0">检索中…</div>';
      try {
      const r = await api('/api/kb/ask', { method: 'POST', body: { q, library: curLib || null } });
      answerBox.innerHTML = '';
      if (!r.ai_used) answerBox.appendChild(el('<div style="color:var(--amber);font-size:12.5px;margin-top:6px">AI 未配置——以下为知识库参考回答（设置页接入后直接给答案）：</div>'));
      if (r.answer) {
        answerBox.appendChild(el(`<div class="md-view" style="margin-top:8px">${mdToHtml(r.answer)}</div>`));
      }
        r.sources.forEach(s => answerBox.appendChild(el(`
          <div style="padding:6px 0;border-bottom:1px solid var(--line);font-size:13px">
            <a href="#" class="src-link" data-path="${escape(s.relpath)}">📄 ${escape(s.title)}</a>
            <span style="color:var(--muted)"> — ${s.hit.replace(/【|】/g, '…')}</span>
          </div>`)));
        answerBox.querySelectorAll('.src-link').forEach(a => a.onclick = (e) => {
          e.preventDefault(); openArticle(a.dataset.path);
        });
      } catch (e) { toast(e.message, false); }
    };
    askCard.querySelector('.ask-btn').onclick = doAsk;
    askInput.onkeydown = (e) => { if (e.key === 'Enter') doAsk(); };
    container.appendChild(askCard);

    // ---- 阅读视图（覆盖层） ----
    const openArticle = async (relpath) => {
      try {
        const a = await api(`/api/kb/article?path=${encodeURIComponent(relpath)}`);
        const overlay = el(`<div style="position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:50;display:flex;justify-content:center;padding:30px 16px;overflow:auto">
          <div class="card" style="max-width:820px;width:100%;height:fit-content;max-height:calc(100vh - 60px);overflow:auto">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
              <span class="badge">${escape(a.category || '文章')}</span>
              <span style="display:flex;gap:6px">
              ${/^(custom\/|mianjing\/|grad\/)/.test(relpath) ? '<button class="btn art-del" style="color:var(--danger,#e5484d)">🗑 删除</button>' : ''}
              <button class="btn close">✕ 关闭</button></span>
            </div>
            <div class="md-view"></div>
          </div></div>`);
        overlay.querySelector('.md-view').innerHTML = mdToHtml(a.body);
        if (overlay.querySelector('.art-del')) overlay.querySelector('.art-del').onclick = async () => {
        if (!(await confirmBox(`删除文章《${a.title}》？
正文、检索与图谱关联将一并清理（磁盘文件同步删除）。`))) return;
        try { await api(`/api/kb/article?path=${encodeURIComponent(relpath)}`, { method: 'DELETE' }); toast('已删除'); overlay.remove(); }
        catch (e) { toast(e.message, false); }
      };
      overlay.querySelector('.close').onclick = () => overlay.remove();
        overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
        document.body.appendChild(overlay);
      } catch (e) { toast('打开失败：' + e.message, false); }
    };
    container._openArticle = openArticle;

    const grid = el('<div class="grid cols-2" style="align-items:start"></div>');
    container.appendChild(grid);

    // ---- 左：搜索 ----
    const left = el(`<div class="card"><div class="card-title">🔎 全文检索</div>
      <div class="inline-form"><input placeholder="关键词，如：红黑树 / MVCC / 拥塞控制" style="flex:1">
      <button class="btn search-btn">搜索</button></div><div class="results"></div></div>`);
    const sInput = left.querySelector('input');
    const resBox = left.querySelector('.results');
    const doSearch = async () => {
      const q = sInput.value.trim();
      if (!q) return;
      resBox.innerHTML = '<div style="color:var(--muted);padding:8px 0">搜索中…</div>';
      try {
        const r = await api(`/api/kb/search?q=${encodeURIComponent(q)}${curLib ? `&lib=${curLib}` : ''}`);
        resBox.innerHTML = '';
        if (!r.hits.length) { resBox.appendChild(el('<div class="empty" style="padding:14px"><div style="font-size:13px">无结果</div></div>')); return; }
        r.hits.forEach(h => resBox.appendChild(el(`
          <div style="padding:9px 0;border-bottom:1px solid var(--line)">
            <a href="#" class="hit-link" data-path="${escape(h.relpath)}">📄 ${escape(h.title)}</a>
            ${h.library ? `<span class="badge gray" style="margin-left:6px">${escape(LIB_CN[h.library] || h.library)}</span>` : ''}
            <span class="badge gray" style="margin-left:${h.library ? 0 : 6}px">${escape(h.category || '')}</span>
            <div style="color:var(--muted);font-size:12.5px;margin-top:3px">${h.hit.replace(/【|】/g, '…')}</div>
          </div>`)));
        resBox.querySelectorAll('.hit-link').forEach(a => a.onclick = (e) => {
          e.preventDefault(); openArticle(a.dataset.path);
        });
      } catch (e) { toast(e.message, false); }
    };
    left.querySelector('.search-btn').onclick = doSearch;
    sInput.onkeydown = (e) => { if (e.key === 'Enter') doSearch(); };
    grid.appendChild(left);

    // ---- 右：收藏夹 ----
    const right = el(`<div class="card"><div class="card-title">⭐ 面经收藏夹</div>
      <div class="inline-form"><input placeholder="标题" style="width:130px">
      <input placeholder="链接（可选）" style="flex:1"><button class="btn">收藏</button></div>
      <div class="clips"></div></div>`);
    const clipBox = right.querySelector('.clips');
    const loadClips = async () => {
      const r = await api('/api/kb/clips');
      clipBox.innerHTML = '';
      if (!r.items.length) { clipBox.appendChild(el('<div class="empty" style="padding:12px"><div style="font-size:13px">还没有收藏</div></div>')); return; }
      r.items.forEach(c => clipBox.appendChild(el(`
        <div style="padding:8px 0;border-bottom:1px solid var(--line);font-size:13px;display:flex;gap:8px;align-items:center">
          <div style="flex:1;min-width:0"><b>${escape(c.title)}</b>
          ${c.link ? ` · <a href="${escape(c.link)}" target="_blank" rel="noopener">链接</a>` : ''}</div>
          <button class="btn" style="padding:2px 8px;font-size:12px">✕</button>
        </div>`)));
      clipBox.querySelectorAll('button').forEach((b, i) => b.onclick = async () => {
        try { await api(`/api/kb/clips/${r.items[i].id}`, { method: 'DELETE' }); toast('已删除'); refresh(); }
        catch (e) { toast(e.message, false); }
      });
    };
    await loadClips();
    const cInputs = right.querySelectorAll('input');
    right.querySelector('.btn').onclick = async () => {
      if (!cInputs[0].value.trim()) return toast('请填标题', false);
      try {
        await api('/api/kb/clips', { method: 'POST', body: { title: cInputs[0].value.trim(), link: cInputs[1].value.trim() } });
        toast('已收藏'); refresh();
      } catch (e) { toast(e.message, false); }
    };
    grid.appendChild(right);
  },
};
