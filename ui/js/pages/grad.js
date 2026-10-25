// 研究生（v1.3 五模块；v1.6 课程详情化；v1.17 问AI/AI考我/学习助手进驻）
import { api } from '../api.js';
import { el, escape, toast, WEEK_CN, todayStr, confirmBox} from './kit.js';
import { openArticle } from '../components/articleView.js';

const TABS = [
  ["kb", "📖 知识库"], ["courses", "📅 课程学习"], ["papers", "📚 文献阅读"],
  ["advisor", "👨‍🏫 导师与组会"], ["thesis", "📄 小论文"],
];

export default {
  id: 'grad',
  title: '研究生',
  icon: '🎓',
  async render(container, rerender) {
    const refresh = () => rerender ? rerender() : location.reload();
    let tab = (location.hash.split("/")[2] || "kb");
    if (!TABS.some(([k]) => k === tab)) tab = "kb";

    container.appendChild(el(`
      <div class="page-head"><h1>研究生</h1>
      <p>研究笔记 · 课程与作业 · Zotero 文献 · 导师组会 · 小论文推进</p></div>`));
    const tabBar = el(`<div style="display:flex;gap:8px;margin-bottom:16px;border-bottom:1px solid var(--line);padding-bottom:10px;flex-wrap:wrap"></div>`);
    TABS.forEach(([k, label]) => {
      const b = el(`<button class="btn" style="${k === tab ? "border-color:var(--accent);color:var(--accent-text);font-weight:600" : ""}">${label}</button>`);
      b.onclick = () => { location.hash = `#/grad/${k}`; };
      tabBar.appendChild(b);
    });
    container.appendChild(tabBar);
    const body = el('<div></div>');
    container.appendChild(body);

    if (tab === "courses") {
      const cid = location.hash.split("/")[3];
      return cid ? renderCourseDetail(body, refresh, +cid) : renderCourses(body, refresh);
    }
    if (tab === "papers") return renderPapers(body, refresh);
    if (tab === "advisor") return renderAdvisor(body, refresh);
    if (tab === "thesis") return renderThesis(body, refresh);
    return renderKb(body, refresh);
  },
};

// ================= Tab 1: 知识库（研究笔记，第三个库实例） =================
async function renderKb(container, refresh) {
  // 新增文章：四入口
  const addCard = el(`<div class="card" style="margin-bottom:14px"><div class="card-title">➕ 新增笔记
    <span class="hint">研究领域笔记：深度学习/大模型/方向调研… 支持 [[双链]]</span>
    <div class="inline-form" style="margin:0">
      <input placeholder="标题" style="width:130px" class="n-title">
      <input placeholder="正文粘贴区（支持 [[双链]]）" style="flex:1" class="n-content">
      <button class="btn n-paste">粘贴入库</button>
      <input type="file" accept=".md,.txt,.docx,.pdf" class="n-file" style="display:none">
      <button class="btn n-upload">上传文件</button>
      <input placeholder="或输入 URL" style="width:150px" class="n-url">
      <button class="btn n-fetch">抓取</button>
    </div><div class="n-msg" style="font-size:12px;color:var(--muted);margin-top:4px"></div></div>`);
  const msg = addCard.querySelector(".n-msg");
  addCard.querySelector(".n-paste").onclick = async () => {
    const content = addCard.querySelector(".n-content").value;
    if (!content.trim()) return toast("请粘贴正文", false);
    const r = await api('/api/kb/ingest', { method: 'POST', body: { way: "paste", library: "grad",
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
      body: { filename: f.name, content_b64: b64, library: "grad" } });
    msg.textContent = r.error || `已入库：${r.title}`; refresh();
  };
  addCard.querySelector(".n-fetch").onclick = async () => {
    const url = addCard.querySelector(".n-url").value.trim();
    if (!url) return toast("请填 URL", false);
    msg.textContent = "抓取中…";
    try { const r = await api('/api/kb/ingest', { method: 'POST', body: { way: "url", library: "grad", url } });
      msg.textContent = r.error || `已抓取：${r.title}`; refresh();
    } catch (err) { msg.textContent = err.message; }
  };
  container.appendChild(addCard);

  const grid = el('<div class="grid cols-2" style="align-items:start"></div>');
  // 搜索
  const left = el(`<div class="card"><div class="card-title">🔎 全文检索</div>
    <div class="inline-form"><input placeholder="如：注意力机制 / RLHF" style="flex:1">
    <button class="btn">搜索</button></div><div class="results"></div></div>`);
  const doSearch = async () => {
    const q = left.querySelector("input").value.trim();
    if (!q) return;
    const r = await api(`/api/kb/search?lib=grad&q=${encodeURIComponent(q)}`);
    const box = left.querySelector(".results");
    box.innerHTML = "";
    if (!r.hits.length) { box.innerHTML = '<div class="empty" style="padding:10px"><div style="font-size:13px">无结果</div></div>'; return; }
    r.hits.forEach(h => box.appendChild(el(`
      <div style="padding:8px 0;border-bottom:1px solid var(--line)">
        <a href="#" class="hit">${escape(h.title)}</a>
        <div style="color:var(--muted);font-size:12.5px">${(h.hit || "").replace(/【|】/g, "…")}</div></div>`)));
    box.querySelectorAll(".hit").forEach((a, i) => a.onclick = (e) => {
      e.preventDefault(); openArticle(r.hits[i].relpath, { library: "grad" });
    });
  };
  left.querySelector("button").onclick = doSearch;
  left.querySelector("input").onkeydown = (e) => { if (e.key === "Enter") doSearch(); };
  grid.appendChild(left);

  // 目录树 + 图谱入口
  const right = el(`<div class="card"><div class="card-title">🗂 目录
    <a href="#/graph?mode=layered&lib=grad" class="btn" style="float:right;padding:2px 10px;font-size:12px">🕸 图谱</a></div>
    <div class="tree" style="max-height:420px;overflow:auto"></div></div>`);
  const { items } = await api('/api/kb/tree?lib=grad');
  const treeBox = right.querySelector(".tree");
  items.slice(0, 60).forEach(a => {
    const l = el(`<div style="display:flex;align-items:center;gap:6px;padding:5px 0;font-size:13px">
      <a href="#" style="flex:1;min-width:0">📄 ${escape(a.title)}</a>
      <span class="badge gray">${escape(a.category || "")}</span>
      <button class="btn t-del" style="padding:1px 7px;font-size:12px" title="删除文章">✕</button></div>`);
    l.querySelector("a").onclick = (e) => { e.preventDefault(); openArticle(a.relpath, { library: "grad", onDeleted: refresh }); };
    l.querySelector(".t-del").onclick = async () => {
      if (!(await confirmBox(`删除研究笔记《${a.title}》？
正文、检索与图谱关联将一并清理（磁盘文件同步删除）。`))) return;
      try { await api(`/api/kb/article?path=${encodeURIComponent(a.relpath)}`, { method: 'DELETE' }); toast("已删除"); refresh(); }
      catch (e) { toast(e.message, false); }
    };
    treeBox.appendChild(l);
  });
  if (!items.length) treeBox.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">库还是空的，从上面添加第一篇研究笔记</div></div>'));
  grid.appendChild(right);
  container.appendChild(grid);
}

// ================= Tab 2: 课程学习（v1.6：列表 → 课程详情） =================
function fileIcon(name) {
  const ext = (name.split('.').pop() || '').toLowerCase();
  if (ext.startsWith('ppt')) return '📊';
  if (ext.startsWith('doc')) return '📝';
  if (ext === 'pdf') return '📄';
  if (['xls', 'xlsx', 'csv'].includes(ext)) return '📈';
  if (['mp4', 'avi', 'mkv', 'mov'].includes(ext)) return '🎬';
  if (['zip', 'rar', '7z'].includes(ext)) return '🗜️';
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext)) return '🖼️';
  return '📎';
}

const fileName = (p) => String(p || '').split(/[\\/]/).pop();

// ===== 文件夹导航小窗（v1.7：新建课程/详情换绑共用，数据来自 /api/fs/folders） =====
function pickFolder(defaultPath = '') {
  return new Promise((resolve) => {
    const overlay = el(`<div style="position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:80;display:flex;justify-content:center;padding:24px 14px;overflow:auto">
      <div class="card" style="width:560px;max-width:100%;align-self:flex-start">
        <div class="card-title">📁 选择文件夹 <span class="hint">逐层进入，选中当前文件夹</span></div>
        <div class="inline-form">
          <input placeholder="输入路径回车可直接跳转" style="flex:1" class="p-jump">
          <button class="btn p-go">跳转</button></div>
        <div class="p-cur" style="font-size:12.5px;color:var(--muted);margin:8px 0;word-break:break-all"></div>
        <div class="p-list" style="max-height:300px;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:4px 10px"></div>
        <div style="display:flex;gap:8px;margin-top:12px;justify-content:flex-end">
          <button class="btn p-up">⬆ 上级</button>
          <button class="btn p-cancel">取消</button>
          <button class="btn btn-primary p-ok">✓ 选择此文件夹</button></div>
      </div></div>`);
    const list = overlay.querySelector('.p-list');
    const curLabel = overlay.querySelector('.p-cur');
    const okBtn = overlay.querySelector('.p-ok');
    const upBtn = overlay.querySelector('.p-up');
    const jump = overlay.querySelector('.p-jump');
    let cur = defaultPath || '';
    let parent = '';
    const close = (v) => { overlay.remove(); resolve(v); };
    const load = async (path) => {
      try {
        const r = await api(`/api/fs/folders?path=${encodeURIComponent(path)}`);
        if (r.error) return toast(r.error, false);
        cur = r.path; parent = r.parent || '';
        curLabel.textContent = cur ? `当前位置：${cur}` : '磁盘根（选择一个盘进入）';
        okBtn.disabled = !cur;
        upBtn.disabled = !parent;
        jump.value = cur;
        list.innerHTML = '';
        if (!r.folders.length) list.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">这里没有子文件夹——可以直接"选择此文件夹"</div></div>'));
        r.folders.forEach(f => {
          const row = el(`<div style="display:flex;align-items:center;gap:8px;padding:6px 2px;font-size:13px;cursor:pointer;border-bottom:1px solid var(--line)">📁 <span>${escape(f.name)}</span></div>`);
          row.onclick = () => load(f.path);
          list.appendChild(row);
        });
      } catch (e) { toast(e.message, false); }
    };
    overlay.querySelector('.p-go').onclick = () => load(jump.value.trim());
    jump.onkeydown = (e) => { if (e.key === 'Enter') load(jump.value.trim()); };
    upBtn.onclick = () => parent && load(parent);
    okBtn.onclick = () => cur && close(cur);
    overlay.querySelector('.p-cancel').onclick = () => close(null);
    overlay.onclick = (e) => { if (e.target === overlay) close(null); };
    document.body.appendChild(overlay);
    load(cur);
  });
}

// ===== 新建课程（v1.7 项目式：选文件夹 + 命名 → 直达详情） =====
function openCreateCourse() {
  const overlay = el(`<div style="position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:70;display:flex;justify-content:center;padding:24px 14px;overflow:auto">
    <div class="card" style="width:520px;max-width:100%;align-self:flex-start">
      <div class="card-title">➕ 新建课程 <span class="hint">像新建项目：选个文件夹，起个名字</span></div>
      <div style="font-size:12.5px;color:var(--muted);margin:2px 0 6px">课程文件夹（选填，可之后再绑）</div>
      <div class="inline-form">
        <input placeholder="D:\\课程\\机器学习 —— 浏览选择，或直接粘贴路径" style="flex:1" class="n-folder">
        <button class="btn n-browse">浏览…</button></div>
      <div style="font-size:12.5px;color:var(--muted);margin:10px 0 6px">课程名 *</div>
      <input placeholder="如：高等机器学习（选中文件夹后自动取名，可改）" class="n-name" style="width:100%">
      <details style="margin-top:10px">
        <summary style="font-size:12.5px;color:var(--muted);cursor:pointer">上课时间（选填，网课可不填）</summary>
        <div class="inline-form" style="margin-top:8px">
          <select class="n-day"><option value="-1">无固定时间</option>${WEEK_CN.map((w, i) => `<option value="${i}">${w}</option>`).join('')}</select>
          <input type="time" value="08:00" class="n-start"><input type="time" value="09:40" class="n-end">
          <input placeholder="地点" style="width:80px" class="n-place"></div></details>
      <div style="display:flex;gap:8px;margin-top:14px;justify-content:flex-end">
        <button class="btn n-cancel">取消</button>
        <button class="btn btn-primary n-ok">创建并进入</button></div>
    </div></div>`);
  const folderIn = overlay.querySelector('.n-folder');
  const nameIn = overlay.querySelector('.n-name');
  let nameAuto = true;
  nameIn.oninput = () => { nameAuto = false; };
  const setFolder = (p) => {
    folderIn.value = p;
    if (p && (nameAuto || !nameIn.value.trim())) {
      nameIn.value = fileName(p.replace(/[\\/]+$/, ''));
      nameAuto = true;
    }
  };
  overlay.querySelector('.n-browse').onclick = async () => {
    const p = await pickFolder(folderIn.value.trim());
    if (p) setFolder(p);
  };
  overlay.querySelector('.n-cancel').onclick = () => overlay.remove();
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
  overlay.querySelector('.n-ok').onclick = async () => {
    const name = nameIn.value.trim();
    if (!name) return toast('请给课程起个名字', false);
    const day = +overlay.querySelector('.n-day').value;
    try {
      const r = await api('/api/grad/courses', { method: 'POST', body: {
        name, folder_path: folderIn.value.trim(),
        day_of_week: day,
        start_time: day < 0 ? '' : overlay.querySelector('.n-start').value,
        end_time: day < 0 ? '' : overlay.querySelector('.n-end').value,
        place: overlay.querySelector('.n-place').value.trim(),
      } });
      toast('课程已创建'); overlay.remove();
      location.hash = `#/grad/courses/${r.id}`;
    } catch (e) { toast(e.message, false); }
  };
  document.body.appendChild(overlay);
  nameIn.focus();
}

async function renderCourses(container, refresh) {
  const coursesR = await api('/api/grad/courses');
  const cCard = el(`<div class="card"><div class="card-title">📅 我的课程
    <span class="hint">点课程进入详情：文件复习 · 作业管理</span></div></div>`);
  const cBox = el('<div></div>');
  if (!coursesR.courses.length) cBox.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">还没有课程，点下面按钮新建第一门</div></div>'));
  coursesR.courses.forEach(c => {
    const schedText = c.has_schedule
      ? `${WEEK_CN[c.day_of_week]} ${c.start_time}-${c.end_time}${c.place ? ' · ' + escape(c.place) : ''}`
      : '无固定时间';
    const row = el(`<div style="display:flex;align-items:center;gap:8px;padding:8px 4px;border-bottom:1px solid var(--line);font-size:13px;cursor:pointer">
      <span style="flex:1;min-width:0"><b>${escape(c.name)}</b>
        <span style="color:var(--muted);margin-left:6px">${schedText}</span>
        <span class="badge gray" style="margin-left:6px">📄 ${c.file_count}</span>
        ${c.folder_path ? '<span class="badge gray">📂 文件夹</span>' : ''}</span>
      ${c.open_assignments ? `<span class="badge amber">作业 ${c.open_assignments}</span>` : ''}
      <span style="color:var(--muted)">›</span>
    </div>`);
    row.onclick = () => { location.hash = `#/grad/courses/${c.id}`; };
    cBox.appendChild(row);
  });
  cCard.appendChild(cBox);
  const btnRow = el('<div style="margin-top:10px"></div>');
  const newBtn = el('<button class="btn btn-primary" style="padding:4px 14px">➕ 新建课程</button>');
  newBtn.onclick = () => openCreateCourse();
  btnRow.appendChild(newBtn);
  cCard.appendChild(btnRow);
  container.appendChild(cCard);
}

async function renderCourseDetail(container, refresh, cid) {
  let d;
  try { d = await api(`/api/grad/courses/${cid}`); }
  catch (e) {
    container.appendChild(el(`<div class="card"><div class="empty"><div class="title">课程不存在或已删除</div>
      <a class="btn" style="margin-top:10px;display:inline-block" href="#/grad/courses">← 返回课程列表</a></div></div>`));
    return;
  }
  const c = d.course;
  const schedText = c.has_schedule
    ? `${WEEK_CN[c.day_of_week]} ${c.start_time}-${c.end_time}${c.place ? ' · ' + escape(c.place) : ''}${c.weeks ? ' · ' + escape(c.weeks) : ''}`
    : '无固定时间';

  const head = el(`<div class="card"><div class="card-title">🎓 ${escape(c.name)} <span class="badge gray">${schedText}</span>
    <span style="float:right;display:flex;gap:6px">
      <a class="btn" style="padding:2px 10px;font-size:12px" href="#/grad/courses">← 返回</a>
      <button class="btn c-del" style="padding:2px 10px;font-size:12px">删除课程</button></span></div></div>`);
  head.querySelector('.c-del').onclick = async () => {
    if (!(await confirmBox(`删除课程「${c.name}」？\n其作业与文件登记将一并清理（磁盘上的文件不受影响）。`))) return;
    try { await api(`/api/grad/courses/${cid}`, { method: 'DELETE' }); toast('已删除'); location.hash = '#/grad/courses'; }
    catch (e) { toast(e.message, false); }
  };
  container.appendChild(head);

  const grid = el('<div class="grid cols-2" style="align-items:start"></div>');
  const left = el('<div></div>');
  const right = el('<div></div>');
  grid.appendChild(left); grid.appendChild(right);
  container.appendChild(grid);
  const grid2 = el('<div class="grid cols-2" style="align-items:start;margin-top:14px"></div>');
  container.appendChild(grid2);

  // ---- 左：文件与复习（F23） ----
  const fCard = el(`<div class="card"><div class="card-title">📂 文件与复习
    <span class="hint">点文件名 → 系统默认程序打开</span></div>
    <div class="inline-form">
      <input placeholder="绑定本机文件夹路径（如 D:\\课程\\机器学习）" style="flex:1" class="b-path" value="${escape(c.folder_path || '')}">
      <button class="btn b-browse">浏览</button>
      <button class="btn b-save">${c.folder_path ? '换绑' : '绑定'}</button></div>
    <div style="font-size:12px;color:var(--muted);margin:6px 0 2px">文件夹内文件自动列出（清空路径点换绑 = 解绑；原文件始终在磁盘上不动）</div>
    <div class="f-prog" style="margin:10px 0"></div>
    <div class="f-list" style="max-height:400px;overflow:auto"></div>
    <div class="inline-form" style="margin-top:10px">
      <input placeholder="零散文件：粘贴本机完整路径（如 D:\\资料\\讲义.pdf）" style="flex:1" class="f-path">
      <button class="btn f-add">登记</button></div></div>`);
  fCard.querySelector('.b-browse').onclick = async () => {
    const p = await pickFolder(fCard.querySelector('.b-path').value.trim());
    if (p) fCard.querySelector('.b-path').value = p;
  };
  fCard.querySelector('.b-save').onclick = async () => {
    const p = fCard.querySelector('.b-path').value.trim();
    try {
      await api(`/api/grad/courses/${cid}`, { method: 'PUT', body: { folder_path: p } });
      toast(p ? '文件夹已绑定' : '已解绑'); refresh();
    } catch (e) { toast(e.message, false); }
  };
  const { reviewed, total } = d.review_progress;
  fCard.querySelector('.f-prog').appendChild(el(`
    <div style="display:flex;justify-content:space-between;font-size:12.5px;color:var(--muted);margin-bottom:4px">
      <span>复习进度</span><span>${reviewed}/${total}</span></div>
    <div class="progress"><i style="width:${total ? Math.round(reviewed / total * 100) : 0}%"></i></div>`));
  const fBox = fCard.querySelector('.f-list');
  if (!d.files.length) fBox.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">暂无文件：绑定文件夹，或登记零散文件</div></div>'));
  d.files.forEach(f => {
    const row = el(`<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--line);font-size:13px">
      <span>${fileIcon(f.name)}</span>
      <a href="#" class="f-open" style="flex:1;min-width:0;${f.exists ? '' : 'color:var(--muted);text-decoration:line-through'}">${escape(f.name)}</a>
      ${f.loose ? '<span class="badge gray">零散</span>' : ''}
      ${f.reviewed ? `<span class="badge">✓ ${f.reviewed_date}</span>` : ''}
      <button class="btn f-rv" style="padding:2px 8px;font-size:12px">${f.reviewed ? '取消' : '✓ 复习了'}</button>
      ${f.loose ? '<button class="btn f-del" style="padding:2px 7px;font-size:12px">✕</button>' : ''}
    </div>`);
    row.querySelector('.f-open').onclick = async (e) => {
      e.preventDefault();
      try { await api(`/api/grad/courses/${cid}/open`, { method: 'POST', body: { path: f.path } }); }
      catch (err) { toast(err.message, false); }
    };
    row.querySelector('.f-rv').onclick = async () => {
      try { await api(`/api/grad/courses/${cid}/review`, { method: 'POST', body: { path: f.path, reviewed: !f.reviewed } }); refresh(); }
      catch (err) { toast(err.message, false); }
    };
    const del = row.querySelector('.f-del');
    if (del) del.onclick = async () => {
      if (!(await confirmBox(`移除文件登记「${f.name}」？（不删除磁盘上的文件）`))) return;
      try { await api(`/api/grad/courses/${cid}/files/${f.file_id}`, { method: 'DELETE' }); toast('已移除'); refresh(); }
      catch (err) { toast(err.message, false); }
    };
    fBox.appendChild(row);
  });
  fCard.querySelector('.f-add').onclick = async () => {
    const p = fCard.querySelector('.f-path').value.trim();
    if (!p) return toast('请填文件完整路径', false);
    try { await api(`/api/grad/courses/${cid}/files`, { method: 'POST', body: { path: p } }); toast('已登记'); refresh(); }
    catch (e) { toast(e.message, false); }
  };
  // 学习助手状态（v1.17：进驻课程文件夹，主动学习才启用）
  const skillRow = el(`<div style="margin-top:10px;padding-top:8px;border-top:1px solid var(--line);font-size:12.5px">
    🧩 学习助手 <span class="badge ${c.skill_installed ? '' : 'gray'}">${c.skill_installed ? '已安装' : '未安装'}</span>
    <button class="btn skill-btn" style="padding:2px 10px;font-size:12px;float:right">${c.skill_installed ? '重装' : '安装'}</button>
    <div style="color:var(--muted);margin-top:5px">复习提问技能装在课程文件夹里：在 ZCode 等编程助手中打开该文件夹、明确说「我要学习了 / 考考我」即开始逐题提问+记忆曲线复习；写课程报告、赶作业时它不会自动启动。学习笔记存于文件夹 learning/ 内，软件不复制、重装不覆盖。</div>
  </div>`);
  skillRow.querySelector('.skill-btn').onclick = async () => {
    try {
      const r = await api(`/api/grad/courses/${cid}/skill`, { method: 'POST' });
      toast(r.inited ? '学习助手已安装，学习目录已初始化' : '学习助手已刷新（学习笔记保留）');
      refresh();
    } catch (e) { toast(e.message, false); }
  };
  fCard.appendChild(skillRow);
  left.appendChild(fCard);

  // ---- 右：作业（F24） ----
  const aCard = el(`<div class="card"><div class="card-title">📝 作业 <span class="badge amber">未完成 ${d.open_assignments}</span>
    <span class="hint">临期黄色 · 过期红色</span></div>
    <div class="a-list" style="max-height:400px;overflow:auto"></div>
    <div class="inline-form" style="margin-top:10px">
      <input placeholder="作业标题" style="flex:1" class="a-title">
      <input type="date" class="a-due" style="width:138px">
      <button class="btn btn-primary a-add">添加</button></div>
    <div class="inline-form" style="margin-top:6px">
      <input placeholder="备注（选填）" style="flex:1" class="a-note">
      <select class="a-file" style="max-width:160px"><option value="">关联文件(选)</option></select></div></div>`);
  const fileSel = aCard.querySelector('.a-file');
  d.files.forEach(f => {
    fileSel.appendChild(el(`<option value="${escape(f.path)}">${escape(f.name.slice(0, 22))}</option>`));
  });
  const aBox = aCard.querySelector('.a-list');
  if (!d.assignments.length) aBox.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">还没有作业</div></div>'));
  d.assignments.forEach(a => {
    const dl = a.days_left;
    let dueChip = '';
    if (dl != null) {
      if (a.status === 'todo' && dl < 0) dueChip = `<span class="badge" style="background:var(--danger,#e5484d);color:#fff">过期 ${-dl} 天</span>`;
      else if (a.status === 'todo' && dl <= 3) dueChip = `<span class="badge amber">剩 ${dl} 天</span>`;
      else dueChip = `<span class="badge gray">${a.due_date}</span>`;
    }
    const row = el(`<div class="check-item ${a.status === 'done' ? 'done' : ''}">
      <button class="tick ${a.status === 'done' ? 'on' : ''}">✓</button>
      <div style="flex:1;min-width:0">
        <div class="t">${escape(a.title)} ${dueChip}</div>
        <div style="font-size:12px;color:var(--muted)">${a.note ? escape(a.note) + ' · ' : ''}${a.file_ref ? `<a href="#" class="a-flink">📎 ${escape(fileName(a.file_ref))}</a> · ` : ''}${a.converted_task_id ? '已在今日待办' : ''}</div>
      </div>
      ${a.status === 'todo' && !a.converted_task_id ? '<button class="btn a-cv" style="padding:2px 8px;font-size:12px">→ 转待办</button>' : ''}
      <button class="btn a-del" style="padding:2px 7px;font-size:12px">✕</button>
    </div>`);
    row.querySelector('.tick').onclick = async () => {
      try {
        await api(`/api/grad/assignments/${a.id}`, { method: 'PUT',
          body: { status: a.status === 'done' ? 'todo' : 'done' } });
        refresh();
      } catch (e) { toast(e.message, false); }
    };
    const cv = row.querySelector('.a-cv');
    if (cv) cv.onclick = async () => {
      try { await api(`/api/grad/assignments/${a.id}/convert`, { method: 'POST' }); toast('已加入今日待办'); refresh(); }
      catch (e) { toast(e.message, false); }
    };
    const flink = row.querySelector('.a-flink');
    if (flink) flink.onclick = async (e) => {
      e.preventDefault();
      try { await api(`/api/grad/courses/${cid}/open`, { method: 'POST', body: { path: a.file_ref } }); }
      catch (err) { toast(err.message, false); }
    };
    row.querySelector('.a-del').onclick = async () => {
      if (!(await confirmBox(`删除作业「${a.title}」？`))) return;
      try { await api(`/api/grad/assignments/${a.id}`, { method: 'DELETE' }); toast('已删除'); refresh(); }
      catch (e) { toast(e.message, false); }
    };
    aBox.appendChild(row);
  });
  aCard.querySelector('.a-add').onclick = async () => {
    const title = aCard.querySelector('.a-title').value.trim();
    if (!title) return toast('请填作业标题', false);
    try {
      await api(`/api/grad/courses/${cid}/assignments`, { method: 'POST', body: {
        title, due_date: aCard.querySelector('.a-due').value,
        note: aCard.querySelector('.a-note').value.trim(),
        file_ref: aCard.querySelector('.a-file').value } });
      toast('作业已添加'); refresh();
    } catch (e) { toast(e.message, false); }
  };
  right.appendChild(aCard);

  // ---- 第二行：问 AI / AI 考我（v1.17） ----
  grid2.appendChild(renderAskCard(cid));
  grid2.appendChild(renderQuizCard(cid));
}

// ===== 问 AI（v1.17 F27）：基于课程资料问答，标注来源，未接 AI 降级参考段落 =====
function renderAskCard(cid) {
  const card = el(`<div class="card"><div class="card-title">🤖 问 AI
    <span class="hint">基于课程文件夹里的资料作答；资料不足时 AI 用自身知识补充</span></div>
    <div class="qa-log" style="max-height:380px;overflow:auto">
      <div class="empty" style="padding:10px"><div style="font-size:13px">这门课不会的当场问，如：L1 和 L2 正则化有什么区别？</div></div>
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
      const r = await api(`/api/grad/courses/${cid}/ask`, { method: 'POST', body: { question: q } });
      pending.remove();
      const srcs = (r.sources || []).filter(s => s.name).slice(0, 6)
        .map(s => `<span class="badge gray">📎 ${escape(s.name)}</span>`).join(' ');
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

// ===== AI 考我（v1.17 F28）：出题→作答→判分，会话级不入记忆曲线 =====
function renderQuizCard(cid) {
  const card = el(`<div class="card"><div class="card-title">🎯 AI 考我
    <span class="hint">AI 基于课程资料出题判分 · 本轮即时练习，长期复习走学习助手</span></div>
    <div class="q-box"></div></div>`);
  const box = card.querySelector('.q-box');
  const setup = () => {
    box.innerHTML = '';
    box.appendChild(el(`<div class="inline-form">
      <select class="q-n"><option value="3">3 题</option><option value="5" selected>5 题</option><option value="8">8 题</option></select>
      <button class="btn btn-primary q-start">出题开考</button></div>
      <div style="font-size:12px;color:var(--muted);margin-top:6px">题目来自课程文件夹里的资料（PPT/Word 自动解析；PDF 需装可选组件 pypdf）</div>`));
    box.querySelector('.q-start').onclick = start;
  };
  const start = async () => {
    const n = +box.querySelector('.q-n').value;
    box.innerHTML = '<div style="color:var(--muted);font-size:12.5px;padding:6px 0">出题中…</div>';
    let r;
    try { r = await api(`/api/grad/courses/${cid}/quiz`, { method: 'POST', body: { n } }); }
    catch (e) { toast(e.message, false); return setup(); }
    run(r.questions || [], r.ai_used);
  };
  const run = (questions, aiUsed) => {
    box.innerHTML = '';
    if (!questions.length) { toast('没有可出的题', false); return setup(); }
    let i = 0;
    const cnt = { pass: 0, fuzzy: 0, fail: 0 };
    const step = () => {
      box.innerHTML = '';
      if (i >= questions.length) {
        box.appendChild(el(`<div class="empty" style="padding:14px"><span class="icon">✅</span>
          <div class="title">本轮完成</div>
          <div style="margin-top:4px">✅ 过 ${cnt.pass} · 🤔 含糊 ${cnt.fuzzy} · ❌ 没过 ${cnt.fail}</div>
          <button class="btn btn-primary q-again" style="margin-top:10px">🔄 再来一轮</button></div>`));
        box.querySelector('.q-again').onclick = setup;
        return;
      }
      const q = questions[i];
      const refHtml = q.ref ? `<details style="margin:6px 0"><summary style="font-size:12px;color:var(--muted);cursor:pointer">查看资料片段</summary>
        <div style="font-size:12.5px;color:var(--muted);white-space:pre-wrap;max-height:180px;overflow:auto;border:1px solid var(--line);border-radius:6px;padding:8px;margin-top:4px">${escape(q.ref)}</div></details>` : '';
      box.appendChild(el(`<div style="display:flex;justify-content:space-between;color:var(--muted);font-size:12px">
        <span>第 ${i + 1} / ${questions.length} 题</span><span>${aiUsed ? '🤖 AI 出题' : '📖 资料自测'}</span></div>
        <div style="font-size:16px;padding:10px 0;line-height:1.6">${escape(q.q)}</div>
        ${refHtml}
        <textarea rows="4" class="q-ans" placeholder="写下你的回答…" style="width:100%"></textarea>
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
          g = await api(`/api/grad/courses/${cid}/quiz/grade`, { method: 'POST',
            body: { question: q.q, answer: ans, ref: q.ref || '' } });
        } catch (e) { toast(e.message, false); res.innerHTML = ''; return; }
        renderVerdict(g, () => { i++; step(); });
      };
    };
    const renderVerdict = (g, next) => {
      const res = box.querySelector('.q-res');
      const sub = box.querySelector('.q-submit');
      if (sub) sub.style.display = 'none';
      const ta = box.querySelector('.q-ans');
      if (ta) ta.disabled = true;
      if (g.verdict) {
        cnt[g.verdict]++;
        const chip = { pass: '<span class="badge">✅ 过</span>',
                       fuzzy: '<span class="badge amber">🤔 含糊</span>',
                       fail: '<span class="badge" style="background:var(--danger,#e5484d);color:#fff">❌ 没过</span>' }[g.verdict];
        res.innerHTML = `<div style="margin-top:8px;font-size:13.5px">${chip}
          ${g.comment ? `<span style="margin-left:6px">${escape(g.comment)}</span>` : ''}</div>
          <div style="text-align:right;margin-top:8px"><button class="btn btn-primary q-next">下一题 →</button></div>`;
        res.querySelector('.q-next').onclick = next;
      } else {
        res.innerHTML = `<div style="margin-top:8px;color:var(--muted);font-size:12.5px">${escape(g.comment || 'AI 未配置——请对照资料片段自评')}</div>
          <div style="display:flex;gap:8px;margin-top:6px">
            <button class="btn q-self" data-v="pass">✅ 过</button>
            <button class="btn q-self" data-v="fuzzy">🤔 含糊</button>
            <button class="btn q-self" data-v="fail">❌ 没过</button></div>`;
        res.querySelectorAll('.q-self').forEach(b => b.onclick = () => { cnt[b.dataset.v]++; next(); });
      }
    };
    step();
  };
  setup();
  return card;
}

// ================= Tab 3: 文献阅读 =================
async function renderPapers(container, refresh) {
  const papersR = await api('/api/papers');
  const grid = el('<div class="grid cols-2" style="align-items:start"></div>');
  // Zotero 导入
  const left = el(`<div class="card"><div class="card-title">📥 Zotero 导入 <span class="hint">Better BibTeX JSON</span></div>
    <p style="color:var(--muted);font-size:12.5px;margin:0 0 6px">
      Zotero 安装 Better BibTeX → 右键集合导出格式选 "Better BibTeX JSON" → 打开文件全选复制粘贴到下面</p>
    <textarea rows="8" style="width:100%" placeholder='[{"title":"Attention Is All You Need","creators":[...],...}]'></textarea>
    <div style="margin-top:8px"><button class="btn btn-primary p-imp">导入</button>
    <span class="p-msg" style="margin-left:10px;font-size:12.5px;color:var(--muted)"></span></div></div>`);
  const pMsg = left.querySelector('.p-msg');
  left.querySelector('.p-imp').onclick = async () => {
    const text = left.querySelector('textarea').value;
    if (!text.trim()) return;
    try {
      const r = await api('/api/papers/import', { method: 'POST', body: { text } });
      if (r.error) return toast(r.error, false);
      pMsg.textContent = `新增 ${r.added} 篇，合并 ${r.merged} 篇`;
      toast('导入完成'); refresh();
    } catch (e) { toast(e.message, false); }
  };
  grid.appendChild(left);
  // 文献清单
  const right = el(`<div class="card"><div class="card-title">📚 文献清单（${papersR.papers.length}）</div>
    <div class="p-box" style="max-height:520px;overflow:auto"></div></div>`);
  const pBox = right.querySelector('.p-box');
  const ST_CN = { unread: '未读', reading: '在读', done: '读完', dropped: '放弃' };
  if (!papersR.papers.length) pBox.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">还没有文献，从左侧导入</div></div>'));
  papersR.papers.forEach(p => {
    const row = el(`<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--line);font-size:13px">
      <select style="padding:3px 6px;font-size:12px">
        ${Object.entries(ST_CN).map(([v, l]) => `<option value="${v}" ${p.status === v ? 'selected' : ''}>${l}</option>`).join('')}
      </select>
      <span style="flex:1;min-width:0">${escape(p.title)}
        <span style="color:var(--muted);font-size:12px">${escape((p.authors || '').split(';')[0] || '')} ${p.year || ''}</span></span>
    </div>`);
    row.querySelector('select').onchange = async () => {
      try { await api(`/api/papers/${p.id}/status`, { method: 'PUT', body: { status: row.querySelector('select').value } }); toast('状态已更新'); }
      catch (e) { toast(e.message, false); }
    };
    const pdel = el('<button class="btn p-del" style="padding:1px 7px;font-size:12px" title="删除文献">✕</button>');
    pdel.onclick = async () => {
      if (!(await confirmBox(`删除文献《${p.title}》？
其阅读笔记将一并删除。`))) return;
      try { await api(`/api/papers/${p.id}`, { method: 'DELETE' }); toast('已删除'); refresh(); }
      catch (e) { toast(e.message, false); }
    };
    row.appendChild(pdel);
    pBox.appendChild(row);
  });
  grid.appendChild(right);
  container.appendChild(grid);
}

// ================= Tab 4: 导师与组会 =================
async function renderAdvisor(container, refresh) {
  const [advisorR, meetingsR] = await Promise.all([
    api('/api/grad/advisor'), api('/api/grad/meetings'),
  ]);
  const grid = el('<div class="grid cols-2" style="align-items:start"></div>');

  const aCard = el(`<div class="card"><div class="card-title">👨‍🏫 导师任务池</div></div>`);
  const aBox = el('<div></div>');
  const pending = advisorR.items.filter(t => t.status === 'pending');
  const converted = advisorR.items.filter(t => t.status !== 'pending');
  if (!advisorR.items.length) aBox.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">暂无任务</div></div>'));
  const delTask = async (t) => {
    if (!(await confirmBox(`删除导师任务「${t.content}」？`))) return;
    try { await api(`/api/grad/advisor/${t.id}`, { method: 'DELETE' }); toast('已删除'); refresh(); }
    catch (e) { toast(e.message, false); }
  };
  pending.forEach(t => {
    const row = el(`<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--line);font-size:13px">
      <span class="badge amber">待处理</span><span style="flex:1">${escape(t.content)}</span>
      <button class="btn btn-primary cv" style="padding:3px 10px;font-size:12px">→ 转今日待办</button>
      <button class="btn del" style="padding:2px 7px;font-size:12px">✕</button>
    </div>`);
    row.querySelector('.cv').onclick = async () => {
      try { await api(`/api/grad/advisor/${t.id}/convert`, { method: 'POST' }); toast('已转为今日待办（高优先级）'); refresh(); }
      catch (e) { toast(e.message, false); }
    };
    row.querySelector('.del').onclick = () => delTask(t);
    aBox.appendChild(row);
  });
  converted.slice(0, 5).forEach(t => {
    const row = el(`<div style="display:flex;align-items:center;gap:8px;padding:5px 0;font-size:13px;color:var(--muted)">
      <span class="dot"></span><span style="flex:1;text-decoration:line-through">${escape(t.content)}</span>
      <button class="btn del" style="padding:1px 7px;font-size:12px">✕</button>
    </div>`);
    row.querySelector('.del').onclick = () => delTask(t);
    aBox.appendChild(row);
  });
  aCard.appendChild(aBox);
  aCard.appendChild(el(`<div class="inline-form"><input placeholder="导师布置的任务…" style="flex:1">
    <button class="btn a-reg">登记</button></div>`));
  const aInput = aCard.querySelector('input');
  aCard.querySelector('.a-reg').onclick = async () => {
    if (!aInput.value.trim()) return;
    try { await api('/api/grad/advisor', { method: 'POST', body: { content: aInput.value.trim() } }); toast('已登记'); refresh(); }
    catch (e) { toast(e.message, false); }
  };
  grid.appendChild(aCard);

  const mCard = el(`<div class="card"><div class="card-title">👥 组会记录</div></div>`);
  const mBox = el('<div style="max-height:420px;overflow:auto"></div>');
  if (!meetingsR.meetings.length) mBox.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">还没有组会记录</div></div>'));
  meetingsR.meetings.slice(0, 12).forEach(m => {
    const row = el(`<div style="display:flex;align-items:flex-start;gap:8px;padding:7px 0;border-bottom:1px solid var(--line);font-size:13px">
      <div style="flex:1;min-width:0"><b>${escape(m.meet_date)}</b> ${escape(m.title || '')}
        ${m.notes ? `<div style="color:var(--muted);font-size:12.5px;margin-top:2px">${escape(m.notes.slice(0, 100))}${m.notes.length > 100 ? '…' : ''}</div>` : ''}</div>
      <button class="btn del" style="padding:2px 7px;font-size:12px">✕</button>
    </div>`);
    row.querySelector('.del').onclick = async () => {
      if (!(await confirmBox(`删除 ${m.meet_date} 的组会记录？`))) return;
      try { await api(`/api/grad/meetings/${m.id}`, { method: 'DELETE' }); toast('已删除'); refresh(); }
      catch (e) { toast(e.message, false); }
    };
    mBox.appendChild(row);
  });
  mCard.appendChild(mBox);
  mCard.appendChild(el(`<div class="inline-form">
    <input type="date" value="${todayStr()}" class="m-date" style="width:145px">
    <input placeholder="纪要（可选）" style="flex:1" class="m-notes">
    <button class="btn m-rec">记录</button></div>`));
  mCard.querySelector('.m-rec').onclick = async () => {
    try {
      await api('/api/grad/meetings', { method: 'POST', body: {
        meet_date: mCard.querySelector('.m-date').value, notes: mCard.querySelector('.m-notes').value.trim() } });
      toast('已记录'); refresh();
    } catch (e) { toast(e.message, false); }
  };
  grid.appendChild(mCard);
  container.appendChild(grid);
}

// ================= Tab 5: 小论文 =================
async function renderThesis(container, refresh) {
  const { goals } = await api('/api/goals');
  const thesis = goals.find(g => g.title.includes('小论文'));
  if (!thesis) {
    container.appendChild(el(`<div class="card"><div class="empty">
      <span class="icon">📄</span><div class="title">还没有小论文目标</div>
      <div>去「目标规划」一键初始化预置目标后可见</div>
      <a class="btn btn-primary" style="margin-top:12px;display:inline-block" href="#/goals">去目标规划</a>
    </div></div>`));
    return;
  }
  const papers = await api('/api/papers');
  const st = { unread: 0, reading: 0, done: 0 };
  papers.papers.forEach(p => { if (st[p.status] != null) st[p.status]++; });

  const card = el(`<div class="card">
    <div class="card-title">📄 ${escape(thesis.title)} <span class="badge">${thesis.progress}%</span></div>
    <div class="progress" style="margin:8px 0"><i style="width:${thesis.progress}%"></i></div>
    <div style="font-size:12.5px;color:var(--muted);margin-bottom:12px">
      选题 → 文献 → 实验 → 初稿 → 投稿 · 完成关联任务自动推进，也可手动微调（＋/−）</div>
    <div class="ms-box"></div>
    <div style="margin-top:14px;padding-top:10px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)">
      📚 关联文献池：共 ${papers.papers.length} 篇（读完 ${st.done} · 在读 ${st.reading} · 未读 ${st.unread}）——
      <a href="#/grad/papers">去文献阅读 →</a></div>
  </div>`);
  const msBox = card.querySelector('.ms-box');
  thesis.milestones.forEach(m => {
    const pct = m.total ? Math.round(m.done_count / m.total * 100) : 0;
    const row = el(`<div style="display:flex;align-items:center;gap:10px;padding:7px 0;font-size:13.5px">
      <span class="dot ${pct >= 100 ? '' : 'off'}"></span>
      <div style="flex:1"><b>${escape(m.title)}</b>
        <div class="progress" style="margin-top:4px;height:6px"><i style="width:${pct}%"></i></div></div>
      <span style="color:var(--muted);font-size:12px;min-width:44px;text-align:right">${m.done_count}/${m.total}</span>
      <button class="btn dn" style="padding:1px 8px;font-size:12px">−</button>
      <button class="btn up" style="padding:1px 8px;font-size:12px">＋</button>
    </div>`);
    row.querySelector(".up").onclick = async () => {
      await api(`/api/goals/milestones/${m.id}/bump`, { method: 'POST', body: { delta: 1 } }); refresh();
    };
    row.querySelector(".dn").onclick = async () => {
      await api(`/api/goals/milestones/${m.id}/bump`, { method: 'POST', body: { delta: -1 } }); refresh();
    };
    msBox.appendChild(row);
  });
  container.appendChild(card);
}
