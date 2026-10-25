// wiki 阅读弹窗：双链渲染 / 反向链接 / 向 AI 提问（存知识卡片）
import { api } from '../api.js';
import { el, escape, toast, mdToHtml, confirmBox } from '../pages/kit.js';

let titleIndex = null;   // relpath/title → relpath 映射缓存
async function ensureIndex(lib) {
  if (titleIndex) return titleIndex;
  const r = await api(`/api/kb/tree?lib=${lib}`);
  titleIndex = new Map(r.items.map(a => [a.title, a.relpath]));
  return titleIndex;
}

/** 渲染正文：先替换 [[双链]] 为占位再走 markdown，防被转义吞掉 */
function renderWiki(body) {
  const holders = [];
  const text = body.replace(/\[\[([^\]]+)\]\]/g, (_, t) => {
    holders.push(t);
    return `WIKILINK§${holders.length - 1}§`;
  });
  let html = mdToHtml(text);
  html = html.replace(/WIKILINK§(\d+)§/g, (_, i) => {
    const t = escape(holders[+i]);
    return `<a href="#" class="wiki-link" data-wiki="${t}">🔗${t}</a>`;
  });
  return html;
}

const WRITABLE_RE = /^(custom\/|mianjing\/|grad\/)/;

export async function openArticle(relpath, opts = {}) {
  const lib = opts.library || "bagu";
  const [a, index] = await Promise.all([
    api(`/api/kb/article?path=${encodeURIComponent(relpath)}`),
    ensureIndex(lib),
  ]);
  const canDelete = WRITABLE_RE.test(relpath);   // v1.19：可写库文章可删
  const overlay = el(`<div style="position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:60;display:flex;justify-content:center;padding:24px 14px;overflow:auto">
    <div class="card" style="max-width:860px;width:100%;height:fit-content;max-height:calc(100vh - 48px);overflow:auto">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <span class="badge">${escape(a.category || "文章")}</span>
        <span style="display:flex;gap:6px">
        ${canDelete ? '<button class="btn art-del" style="color:var(--danger,#e5484d)">🗑 删除</button>' : ""}
        <button class="btn close">✕ 关闭</button></span>
      </div>
      <div class="md-view"></div>
      <div class="bl-box" style="margin-top:14px"></div>
      <div class="ask-box" style="margin-top:14px;border-top:1px solid var(--line);padding-top:12px">
        <div style="font-size:13px;font-weight:600;margin-bottom:6px">💬 不懂就问（问答自动存为知识卡片，供复习）</div>
        <div class="inline-form" style="margin:0"><input placeholder="针对本文提问，如：为什么需要四次挥手？" style="flex:1">
        <button class="btn btn-primary ask-btn">提问</button></div>
        <div class="ask-result" style="font-size:13px"></div>
      </div>
    </div></div>`);
  overlay.querySelector(".md-view").innerHTML = renderWiki(a.body);
  if (canDelete) overlay.querySelector(".art-del").onclick = async () => {
    if (!(await confirmBox(`删除文章《${a.title}》？
正文、检索、图谱关联与复习分块将一并清理（磁盘文件同步删除）。`))) return;
    try {
      await api(`/api/kb/article?path=${encodeURIComponent(relpath)}`, { method: "DELETE" });
      toast("已删除"); overlay.remove(); opts.onDeleted && opts.onDeleted();
    } catch (e) { toast(e.message, false); }
  };
  overlay.querySelector(".close").onclick = () => overlay.remove();
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

  // 双链点击 → 跳转文章
  overlay.querySelectorAll(".wiki-link").forEach(lnk => lnk.onclick = async (e) => {
    e.preventDefault();
    const target = index.get(lnk.dataset.wiki) ||
      [...index.entries()].find(([t]) => lnk.dataset.wiki.includes(t) || t.includes(lnk.dataset.wiki))?.[1];
    if (target) { overlay.remove(); openArticle(target, opts); }
    else toast("未找到对应文章", false);
  });

  // 反向链接
  const blBox = overlay.querySelector(".bl-box");
  if (a.backlinks && a.backlinks.length) {
    blBox.innerHTML = `<div style="font-size:12.5px;color:var(--muted);margin-bottom:4px">↩ 引用本篇的文章</div>`;
    a.backlinks.forEach(b => {
      const l = el(`<a href="#" style="display:block;font-size:13px;padding:3px 0">📄 ${escape(b.title)}</a>`);
      l.onclick = (e) => { e.preventDefault(); overlay.remove(); openArticle(b.relpath, opts); };
      blBox.appendChild(l);
    });
  }

  // 向 AI 提问（F12）：AI 直答；无 AI 时给知识库参考回答
  const input = overlay.querySelector(".ask-box input");
  const resultBox = overlay.querySelector(".ask-result");
  const doAsk = async () => {
    const q = input.value.trim();
    if (!q) return;
    resultBox.innerHTML = '<span style="color:var(--muted)">思考中…（AI 未配置时给知识库参考段落）</span>';
    try {
      const r = await api("/api/learn/ask", { method: "POST",
        body: { q, ref_path: relpath, library: lib } });
      resultBox.innerHTML = "";
      if (r.ai_used) {
        resultBox.appendChild(el(`<div class="md-view">${mdToHtml(r.card.a)}</div>`));
        if (r.card.point) resultBox.appendChild(el(
          `<div style="font-size:12.5px;color:var(--muted);margin-top:4px">💡 记忆点：${escape(r.card.point)}</div>`));
      } else if (r.card.a) {
        resultBox.appendChild(el('<div><span class="badge gray">参考</span> <span style="font-size:12px;color:var(--muted)">来自知识库命中段落，接入 AI 后可直接追问</span></div>'));
        resultBox.appendChild(el(`<div class="md-view" style="margin-top:6px">${mdToHtml(r.card.a)}</div>`));
      } else {
        resultBox.textContent = "✅ 已保存为知识卡片（知识库未命中相关内容；可在复习模式自测）";
      }
      input.value = "";
      toast("问题已存入卡片库");
    } catch (e) { toast(e.message, false); }
  };
  overlay.querySelector(".ask-btn").onclick = doAsk;
  input.onkeydown = (e) => { if (e.key === "Enter") doAsk(); };

  document.body.appendChild(overlay);
}
