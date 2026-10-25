// 面经库 Tab：同八股库架构（搜索/图谱/目录树）+ 四入口新增 + 收藏夹
import { api } from '../../api.js';
import { el, escape, toast, confirmBox } from '../kit.js';
import { renderGraph } from '../../components/graph.js';
import { openArticle } from '../../components/articleView.js';

export async function renderMianjing(container, refresh) {
  // 新增文章：四入口
  const addCard = el(`<div class="card" style="margin-bottom:14px"><div class="card-title">➕ 新增文章
    <span class="hint">粘贴 / 上传 / URL 抓取 / 文件夹自动扫描</span></div>
    <div class="inline-form" style="margin:0">
      <input placeholder="标题" style="width:130px" class="n-title">
      <input placeholder="正文粘贴区（支持 [[双链]]）" style="flex:1" class="n-content">
      <button class="btn n-paste">粘贴入库</button>
      <input type="file" accept=".md,.txt,.docx,.pdf" class="n-file" style="display:none">
      <button class="btn n-upload">上传文件</button>
      <input placeholder="或输入 URL" style="width:150px" class="n-url">
      <button class="btn n-fetch">抓取</button>
      <button class="btn n-scan">扫描文件夹</button>
    </div><div class="n-msg" style="font-size:12px;color:var(--muted);margin-top:4px"></div></div>`);
  const msg = addCard.querySelector(".n-msg");
  addCard.querySelector(".n-paste").onclick = async () => {
    const content = addCard.querySelector(".n-content").value;
    if (!content.trim()) return toast("请粘贴正文", false);
    const r = await api('/api/kb/ingest', { method: 'POST', body: { way: "paste", library: "mianjing",
      title: addCard.querySelector(".n-title").value.trim() || content.trim().split("\n")[0].slice(0, 40), content } });
    msg.textContent = `已入库：${r.title}`; toast("已入库"); refresh();
  };
  addCard.querySelector(".n-upload").onclick = () => addCard.querySelector(".n-file").click();
  addCard.querySelector(".n-file").onchange = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const buf = await f.arrayBuffer();
    const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
    const r = await api('/api/kb/ingest-file', { method: 'POST',
      body: { filename: f.name, content_b64: b64, library: "mianjing" } });
    msg.textContent = r.error || `已入库：${r.title}`; refresh();
  };
  addCard.querySelector(".n-fetch").onclick = async () => {
    const url = addCard.querySelector(".n-url").value.trim();
    if (!url) return toast("请填 URL", false);
    msg.textContent = "抓取中…";
    try { const r = await api('/api/kb/ingest', { method: 'POST', body: { way: "url", library: "mianjing", url } });
      msg.textContent = r.error || `已抓取：${r.title}`; refresh();
    } catch (err) { msg.textContent = err.message; }
  };
  addCard.querySelector(".n-scan").onclick = async () => {
    msg.textContent = "扫描中…";
    const r = await api('/api/kb/scan', { method: 'POST' });
    msg.textContent = `扫描完成：本次导入 ${r.imported} 篇，共 ${r.total} 篇`; refresh();
  };
  container.appendChild(addCard);

  // 搜索 + 目录树
  const grid = el('<div class="grid cols-2" style="align-items:start"></div>');
  const left = el(`<div class="card"><div class="card-title">🔎 全文检索</div>
    <div class="inline-form"><input placeholder="如：字节 一面 Redis" style="flex:1">
    <button class="btn">搜索</button></div><div class="results"></div></div>`);
  const doSearch = async () => {
    const q = left.querySelector("input").value.trim();
    if (!q) return;
    const r = await api(`/api/kb/search?lib=mianjing&q=${encodeURIComponent(q)}`);
    const box = left.querySelector(".results");
    box.innerHTML = "";
    if (!r.hits.length) { box.innerHTML = '<div class="empty" style="padding:10px"><div style="font-size:13px">无结果</div></div>'; return; }
    r.hits.forEach(h => box.appendChild(el(`
      <div style="padding:8px 0;border-bottom:1px solid var(--line)">
        <a href="#" class="hit">${escape(h.title)}</a>
        <div style="color:var(--muted);font-size:12.5px">${(h.hit || "").replace(/【|】/g, "…")}</div></div>`)));
    box.querySelectorAll(".hit").forEach((a, i) => a.onclick = (e) => {
      e.preventDefault(); openArticle(r.hits[i].relpath, { library: "mianjing" });
    });
  };
  left.querySelector("button").onclick = doSearch;
  left.querySelector("input").onkeydown = (e) => { if (e.key === "Enter") doSearch(); };
  grid.appendChild(left);

  const right = el(`<div class="card"><div class="card-title">🗂 目录 · 最近</div><div class="tree"></div></div>`);
  const { items } = await api('/api/kb/tree?lib=mianjing');
  const treeBox = right.querySelector(".tree");
  items.slice(0, 30).forEach(a => {
    const l = el(`<div style="display:flex;align-items:center;gap:6px;padding:5px 0;font-size:13px">
      <a href="#" style="flex:1;min-width:0">📄 ${escape(a.title)}</a>
      <span class="badge gray">${escape(a.category || "")}</span>
      <button class="btn t-del" style="padding:1px 7px;font-size:12px" title="删除文章">✕</button></div>`);
    l.querySelector("a").onclick = (e) => { e.preventDefault(); openArticle(a.relpath, { library: "mianjing", onDeleted: refresh }); };
    l.querySelector(".t-del").onclick = async () => {
      if (!(await confirmBox(`删除面经《${a.title}》？
正文、检索与图谱关联将一并清理（磁盘文件同步删除）。`))) return;
      try { await api(`/api/kb/article?path=${encodeURIComponent(a.relpath)}`, { method: 'DELETE' }); toast("已删除"); refresh(); }
      catch (e) { toast(e.message, false); }
    };
    treeBox.appendChild(l);
  });
  if (!items.length) treeBox.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">库还是空的，从上面添加第一篇</div></div>'));
  grid.appendChild(right);
  container.appendChild(grid);

  // 收藏夹
  const { items: clips } = await api('/api/kb/clips');
  const cCard = el(`<div class="card" style="margin-top:14px"><div class="card-title">⭐ 快速收藏（原文链接类）</div>
    <div class="inline-form" style="margin:0"><input placeholder="标题" style="width:130px" class="c-t">
    <input placeholder="链接" style="flex:1" class="c-l"><button class="btn c-add">收藏</button></div>
    <div class="c-list" style="margin-top:8px"></div></div>`);
  cCard.querySelector(".c-add").onclick = async () => {
    const t = cCard.querySelector(".c-t").value.trim();
    if (!t) return;
    await api('/api/kb/clips', { method: 'POST', body: { title: t, link: cCard.querySelector(".c-l").value.trim() } });
    refresh();
  };
  const cl = cCard.querySelector(".c-list");
  clips.forEach(c => {
    const row = el(`<div style="padding:5px 0;font-size:13px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:6px">
      <span style="flex:1;min-width:0"><b>${escape(c.title)}</b> ${c.link ? `<a href="${escape(c.link)}" target="_blank" rel="noopener">链接</a>` : ""}</span>
      <button class="btn c-del" style="padding:1px 7px;font-size:12px" title="删除收藏">✕</button></div>`);
    row.querySelector(".c-del").onclick = async () => {
      if (!(await confirmBox(`删除收藏「${c.title}」？`))) return;
      try { await api(`/api/kb/clips/${c.id}`, { method: 'DELETE' }); toast("已删除"); refresh(); }
      catch (e) { toast(e.message, false); }
    };
    cl.appendChild(row);
  });
  if (!clips.length) cl.appendChild(el('<div class="empty" style="padding:8px"><div style="font-size:13px">暂无</div></div>'));
  container.appendChild(cCard);
}
