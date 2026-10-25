// 页面小工具：DOM、转义、Toast、极简 Markdown 渲染
export function el(html) {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

export function escape(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

export function toast(msg, ok = true) {
  let box = document.querySelector('.toast-box');
  if (!box) {
    box = el('<div class="toast-box"></div>');
    document.body.appendChild(box);
  }
  const t = el(`<div class="toast ${ok ? '' : 'err'}">${escape(msg)}</div>`);
  box.appendChild(t);
  setTimeout(() => t.remove(), 2600);
}

/** 页面内确认弹窗（替代 window.confirm——部分内嵌浏览器会抑制原生 confirm 导致删除按钮"点了没反应"）。
 * 返回 Promise<boolean>，用法：if (!(await confirmBox('删除xx？'))) return; */
export function confirmBox(message, { title = '确认操作', okText = '删除' } = {}) {
  return new Promise((resolve) => {
    const overlay = el(`<div style="position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:90;display:flex;justify-content:center;align-items:center;padding:20px">
      <div class="card" style="width:380px;max-width:100%">
        <div class="card-title">${escape(title)}</div>
        <div style="font-size:13.5px;line-height:1.7;padding:6px 0 14px;white-space:pre-line">${escape(message)}</div>
        <div style="display:flex;gap:8px;justify-content:flex-end">
          <button class="btn c-no">取消</button>
          <button class="btn c-ok" style="background:var(--danger,#e5484d);color:#fff;border-color:transparent">${escape(okText)}</button>
        </div></div></div>`);
    const done = (v) => { overlay.remove(); resolve(v); };
    overlay.querySelector('.c-ok').onclick = () => done(true);
    overlay.querySelector('.c-no').onclick = () => done(false);
    overlay.onclick = (e) => { if (e.target === overlay) done(false); };
    document.body.appendChild(overlay);
    overlay.querySelector('.c-ok').focus();
  });
}

/** 极简 Markdown → HTML（标题/粗斜体/行内码/代码块/图片/链接/列表/引用/表格） */
export function mdToHtml(md) {
  const lines = String(md || '').split('\n');
  const out = [];
  let inCode = false, inList = false, inQuote = false;
  const closeList = () => { if (inList) { out.push('</ul>'); inList = false; } };
  const closeQuote = () => { if (inQuote) { out.push('</blockquote>'); inQuote = false; } };
  const inline = (s) => escape(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/\*([^*]+)\*/g, '<i>$1</i>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  for (const raw of lines) {
    const line = raw.replace(/\s+$/, '');
    if (line.startsWith('```')) {
      closeList(); closeQuote();
      out.push(inCode ? '</code></pre>' : '<pre><code>');
      inCode = !inCode;
      continue;
    }
    if (inCode) { out.push(escape(raw)); continue; }
    if (!line.trim()) { closeList(); closeQuote(); continue; }
    let m;
    if ((m = line.match(/^(#{1,4})\s+(.*)/))) {
      closeList(); closeQuote();
      const h = m[1].length;
      out.push(`<h${h + 1}>${inline(m[2])}</h${h + 1}>`); // 原文 h1 降一级，页面里更协调
    } else if ((m = line.match(/^[-*]\s+(.*)/))) {
      closeQuote();
      if (!inList) { out.push('<ul>'); inList = true; }
      out.push(`<li>${inline(m[1])}</li>`);
    } else if (line.startsWith('>')) {
      closeList();
      if (!inQuote) { out.push('<blockquote>'); inQuote = true; }
      out.push(`<p>${inline(line.replace(/^>\s?/, ''))}</p>`);
    } else if (line.startsWith('|') && line.includes('|', 1)) {
      closeList(); closeQuote();
      const cells = line.split('|').slice(1, -1).map(c => c.trim());
      if (cells.every(c => /^:?-{2,}:?$/.test(c))) continue; // 分隔行
      out.push('<table><tr>' + cells.map(c => `<td>${inline(c)}</td>`).join('') + '</tr></table>');
    } else if (/^!\[.*\]\(.*\)$/.test(line.trim())) {
      closeList(); closeQuote();
      const mm = line.trim().match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
      out.push(`<img class="md-img" src="${mm[2]}" alt="${escape(mm[1])}" loading="lazy">`);
    } else {
      closeList(); closeQuote();
      out.push(`<p>${inline(line)}</p>`);
    }
  }
  closeList(); closeQuote();
  if (inCode) out.push('</code></pre>');
  return out.join('\n');
}

export const WEEK_CN = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

export function todayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
