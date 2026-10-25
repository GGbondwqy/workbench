// 知识图谱全屏页：分层浏览（递归分组，任意层 ≤10 节点，DESIGN F19 v2.3）+ 全景大图
// 路由 #/graph?mode=layered|full&lib=bagu|mianjing|grad（本页自解析 query，路由器只认第一段）
import { api } from '../api.js';
import { el, escape, toast } from './kit.js';
import { renderGraph } from '../components/graph.js';
import { openArticle } from '../components/articleView.js';

const LIBS = [["bagu", "八股库"], ["mianjing", "面经库"], ["grad", "研究生库"]];
const MAX_NODES = 10;   // 每层节点上限

export default {
  id: 'graph',
  title: '知识图谱',
  icon: '🕸',
  nav: false,
  async render(container) {
    const raw = location.hash.split('?')[1] || '';
    const param = (k) => new URLSearchParams(raw).get(k);
    let mode = param('mode') === 'full' ? 'full' : 'layered';
    let lib = LIBS.some(([k]) => k === param('lib')) ? param('lib') : 'bagu';
    let path = [];   // 下钻栈：[{title, nodes}]，空=栏目层

    const graph = await api(`/api/kb/graph?lib=${lib}`);

    container.appendChild(el(`
      <div class="page-head" style="margin-bottom:10px"><h1 style="font-size:22px">🕸 知识图谱</h1>
      <p>${graph.nodes.length} 篇文章 · ${graph.edges.length} 条关联 · 分层每层 ≤${MAX_NODES} 节点</p></div>`));

    // ---- 工具栏 ----
    const bar = el(`<div class="card" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:10px 14px;margin-bottom:12px">
      <a href="#/career/bagu" class="btn" style="text-decoration:none">← 返回八股页</a>
      <div style="display:flex;gap:0;border:1px solid var(--line);border-radius:8px;overflow:hidden">
        <button class="btn m-layered" style="border:none;border-radius:0">🗂 分层浏览</button>
        <button class="btn m-full" style="border:none;border-radius:0">⛶ 全景大图</button>
      </div>
      <select class="lib">${LIBS.map(([k, l]) => `<option value="${k}">${l}</option>`).join('')}</select>
      <div class="inline-form" style="margin:0;flex:1;min-width:200px">
        <input placeholder="全景模式：按标题过滤节点" class="flt" style="flex:1">
        <button class="btn flt-clear" style="display:none">清除</button>
      </div>
      <span class="crumb" style="font-size:13px;color:var(--muted)"></span>
    </div>`);
    const stage = el('<div class="card" style="padding:8px;min-height:60vh"></div>');
    container.appendChild(bar);
    container.appendChild(stage);

    const modeBtns = { layered: bar.querySelector('.m-layered'), full: bar.querySelector('.m-full') };
    const setMode = (m) => { mode = m; path = []; draw(); };
    modeBtns.layered.onclick = () => setMode('layered');
    modeBtns.full.onclick = () => setMode('full');
    bar.querySelector('.lib').value = lib;
    bar.querySelector('.lib').onchange = (e) => {
      lib = e.target.value;
      location.hash = `#/graph?mode=${mode}&lib=${lib}`;
    };
    const fltInput = bar.querySelector('.flt');
    const fltClear = bar.querySelector('.flt-clear');
    fltInput.onkeydown = (e) => { if (e.key === 'Enter') draw(); };
    fltClear.onclick = () => { fltInput.value = ''; fltClear.style.display = 'none'; draw(); };

    const crumb = bar.querySelector('.crumb');

    function draw() {
      stage.innerHTML = '';
      modeBtns.layered.style.cssText = `border:none;border-radius:0;${mode === 'layered' ? 'background:var(--accent);color:var(--accent-text);font-weight:600' : ''}`;
      modeBtns.full.style.cssText = `border:none;border-radius:0;${mode === 'full' ? 'background:var(--accent);color:var(--accent-text);font-weight:600' : ''}`;
      fltInput.style.display = mode === 'full' ? '' : 'none';
      if (mode === 'layered') {
        if (!path.length) { drawCategoryLayer(); return; }
        const cur = path[path.length - 1];
        renderCrumb();
        if (cur.nodes.length <= MAX_NODES) drawArticleLayer(cur.nodes);
        else drawGroupLayer(cur.nodes, cur.depth || 0);
      } else {
        drawFull();
      }
    }

    function renderCrumb(extra) {
      crumb.innerHTML = '';
      const root = el('<a href="#" style="color:var(--accent-text)">全部栏目</a>');
      root.onclick = (e) => { e.preventDefault(); path = []; draw(); };
      crumb.appendChild(root);
      path.forEach((p, i) => {
        crumb.appendChild(el('<span> » </span>'));
        if (i < path.length - 1) {
          const a = el(`<a href="#" style="color:var(--accent-text)">${escape(p.title)}</a>`);
          a.onclick = (e) => { e.preventDefault(); path = path.slice(0, i + 1); draw(); };
          crumb.appendChild(a);
        } else {
          crumb.appendChild(el(`<b>${escape(p.title)}</b>${extra || ''}`));
        }
      });
    }

    // ---- 第 1 层：栏目聚合 ----
    function drawCategoryLayer() {
      crumb.textContent = `共 ${graph.nodes.length} 篇 · 点击栏目下钻`;
      const cats = new Map();
      graph.nodes.forEach(nd => {
        const c = nd.category || '其他';
        if (!cats.has(c)) cats.set(c, []);
        cats.get(c).push(nd);
      });
      const entries = [...cats.entries()];
      drawRingLayer(entries.map(([name, nodes]) => ({ label: name, nodes })),
                    (gi) => { path = [{ title: entries[gi][0], nodes: entries[gi][1], depth: 0 }]; draw(); });
    }

    // ---- 组层：递归分组（编号前缀 → 内容社区 → 均分兜底，F19 v2.3） ----
    function drawGroupLayer(nodes, depth) {
      const groups = makeGroups(nodes, depth);
      renderCrumb(`（${nodes.length} 篇 · 分成 ${groups.length} 组）`);
      drawRingLayer(groups, (idx) => {
        path.push({ title: groups[idx].label, nodes: groups[idx].nodes, depth: depth + 1 });
        draw();
      });
    }

    // 标题章节编号 "4.1 xxx" → [4,1]；深度 d 用前 d+1 段做组键
    function numSegs(title) {
      const m = String(title).match(/^(\d+(?:\.\d+)*)[ .、．]/);
      return m ? m[1].split('.').map(Number) : null;
    }

    function makeGroups(nodes, depth) {
      if (depth > 6) {  // 防御：极端深时直接均分
        return evenSplit(nodes).map((ns, i, arr) => ({ label: `第 ${i + 1}/${arr.length} 组`, nodes: ns }));
      }
      // ① 章节编号前缀（depth=已用过的编号级数；本次用前 depth+1 段）
      const byNum = new Map();
      const rest = [];
      for (const n of nodes) {
        const segs = numSegs(n.title);
        if (segs && segs.length > depth) {
          const key = segs.slice(0, depth + 1).join('.');
          if (!byNum.has(key)) byNum.set(key, []);
          byNum.get(key).push(n);
        } else rest.push(n);
      }
      const numEntries = [...byNum.entries()].sort((a, b) => {
        const pa = a[0].split('.').map(Number), pb = b[0].split('.').map(Number);
        for (let i = 0; i < Math.max(pa.length, pb.length); i++)
          if ((pa[i] ?? -1) !== (pb[i] ?? -1)) return (pa[i] ?? -1) - (pb[i] ?? -1);
        return 0;
      });
      // 编号维度有效判据：过半有编号 + 聚合度够（组数 ≤ 篇数 30%）
      // + 完整编号基本不重复（重复率高 = 多个系列都从 1 编号，题号无主题语义 → 交给社区分组）
      const grouped = nodes.length - rest.length;
      const fullNums = nodes.map(n => numSegs(n.title)).filter(Boolean).map(s => s.join('.'));
      const dupRate = fullNums.length ? 1 - new Set(fullNums).size / fullNums.length : 1;
      if (numEntries.length >= 2 && grouped >= nodes.length * 0.5
          && numEntries.length <= Math.max(4, nodes.length * 0.3) && dupRate <= 0.2) {
        let entries = numEntries.map(([key, ns]) => ({ label: key, nodes: ns }));
        if (rest.length) entries.push({ label: '其他', nodes: rest });
        entries = labelNumGroups(entries);
        return mergeToMax(entries);
      }
      // ② 内容社区（kNN 稀疏化 + 标签传播；稠密全连图会收敛成单社区，必须先稀疏）
      const idset = new Set(nodes.map(n => n.id));
      const subEdges = graph.edges.filter(e => idset.has(e.src) && idset.has(e.dst));
      if (subEdges.length >= nodes.length) {
        const comms = labelPropagation(nodes, subEdges);
        if (comms.length >= 2 && comms.length < nodes.length) {
          comms.sort((a, b) => b.length - a.length);
          const deg = new Map(subEdges.flatMap(e => [e.src, e.dst])
            .reduce((m, id) => (m.set(id, (m.get(id) || 0) + 1), m), new Map()));
          const entries = comms.map(ns => {
            const hub = [...ns].sort((a, b) => (deg.get(b.id) || 0) - (deg.get(a.id) || 0))[0];
            const t = hub ? hub.title.replace(/^\d+(?:\.\d+)*[ .、．]*/, '').replace(/[「」]/g, '') : '主题';
            return { label: `「${t.slice(0, 10)}」`, nodes: ns };
          });
          return mergeToMax(refineBig(entries, depth));
        }
      }
      // ③ 均分兜底（组数也 ≤MAX：超出时下钻继续分）
      const k = Math.min(Math.ceil(nodes.length / MAX_NODES), MAX_NODES);
      return mergeToMax(evenSplit(nodes, k).map((ns, i, arr) => ({ label: `第 ${i + 1}/${arr.length} 组`, nodes: ns })));
    }

    // 巨组细分：组 > 20 篇时在其子图内再分一层平铺进来（社区主题下再分主题），
    // 保证每层节点 ≤MAX 的同时避免"一层一个大胖子组"；无法再分则保留
    function refineBig(entries, depth) {
      const out = [];
      for (const g of entries) {
        if (g.nodes.length > MAX_NODES * 2 && depth < 6) {
          const idset = new Set(g.nodes.map(n => n.id));
          const sub = graph.edges.filter(e => idset.has(e.src) && idset.has(e.dst));
          if (sub.length >= g.nodes.length) {
            const comms = labelPropagation(g.nodes, sub)
              .sort((a, b) => b.length - a.length);
            if (comms.length >= 2 && comms[0].length < g.nodes.length) {
              const deg = new Map(sub.flatMap(e => [e.src, e.dst])
                .reduce((m, id) => (m.set(id, (m.get(id) || 0) + 1), m), new Map()));
              comms.forEach(ns => {
                const hub = [...ns].sort((a, b) => (deg.get(b.id) || 0) - (deg.get(a.id) || 0))[0];
                const t = hub ? hub.title.replace(/^\d+(?:\.\d+)*[ .、．]*/, '').replace(/[「」]/g, '') : '主题';
                out.push({ label: `${g.label.slice(0, 8)}·${t.slice(0, 8)}`, nodes: ns });
              });
              continue;
            }
          }
        }
        out.push(g);
      }
      return out;
    }

    function labelNumGroups(entries) {
      // 组名 "4.1–4.9"：取组内首末篇的编号
      return entries.map(g => {
        if (g.label === '其他') return g;
        const nums = g.nodes.map(n => numSegs(n.title)).filter(Boolean)
          .map(s => s.join('.')).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
        return { ...g, label: nums.length > 1 ? `${nums[0]}–${nums[nums.length - 1]}` : (nums[0] || g.label) };
      });
    }

    function labelPropagation(nodes, edges) {
      // kNN 稀疏化：每个节点只保留权重最高的 top-3 邻边，否则稠密图传播会收敛成单社区
      const byNode = new Map(nodes.map(n => [n.id, []]));
      for (const e of edges) {
        byNode.get(e.src)?.push([e.dst, e.weight || 1]);
        byNode.get(e.dst)?.push([e.src, e.weight || 1]);
      }
      const adj = new Map(nodes.map(n => [n.id, new Map()]));
      for (const [id, list] of byNode) {
        list.sort((a, b) => b[1] - a[1]);
        for (const [nb] of list.slice(0, 3)) adj.get(id).set(nb, true);
      }
      const label = new Map(nodes.map((n, i) => [n.id, i]));
      const order = [...nodes].sort((a, b) => (adj.get(b.id)?.size || 0) - (adj.get(a.id)?.size || 0));
      for (let round = 0; round < 15; round++) {
        let changed = false;
        for (const n of order) {
          const cnt = new Map();
          for (const nb of adj.get(n.id)?.keys() || [])
            cnt.set(label.get(nb), (cnt.get(label.get(nb)) || 0) + 1);
          if (!cnt.size) continue;
          let best = label.get(n.id), bestN = -1;
          for (const [l, c] of cnt)
            if (c > bestN || (c === bestN && l < best)) { best = l; bestN = c; }
          if (best !== label.get(n.id)) { label.set(n.id, best); changed = true; }
        }
        if (!changed) break;
      }
      const comm = new Map();
      for (const n of nodes) {
        if (!comm.has(label.get(n.id))) comm.set(label.get(n.id), []);
        comm.get(label.get(n.id)).push(n);
      }
      return [...comm.values()];
    }

    function evenSplit(nodes, k) {
      k = k || Math.ceil(nodes.length / MAX_NODES);
      const size = Math.ceil(nodes.length / k);
      const out = [];
      for (let i = 0; i < nodes.length; i += size) out.push(nodes.slice(i, i + size));
      return out;
    }

    function mergeToMax(entries) {
      // 组数 >MAX：相邻顺序合并成 ≤MAX 组（标签相连）
      if (entries.length <= MAX_NODES) return entries;
      const k = MAX_NODES;
      const per = Math.ceil(entries.length / k);
      const out = [];
      for (let i = 0; i < entries.length; i += per) {
        const part = entries.slice(i, i + per);
        out.push({ label: `${part[0].label} ~ ${part[part.length - 1].label}`,
                   nodes: part.flatMap(p => p.nodes) });
      }
      return out;
    }

    // ---- 环形聚合层渲染（栏目层/组层共用） ----
    function drawRingLayer(groups, onPick) {
      // 组间边权重 = 跨组文章连边数
      const gOf = new Map();
      groups.forEach((g, gi) => g.nodes.forEach(n => gOf.set(n.id, gi)));
      const cross = new Map();
      const inner = new Set(graph.nodes.map(n => n.id));
      for (const e of graph.edges) {
        const ga = gOf.get(e.src), gb = gOf.get(e.dst);
        if (ga == null || gb == null || ga === gb) continue;
        const key = [ga, gb].sort().join('§');
        cross.set(key, (cross.get(key) || 0) + 1);
      }
      const W = 1100, H = Math.max(460, Math.min(760, 160 + groups.length * 52));
      const cx = W / 2, cy = H / 2, R = Math.min(W, H) / 2 - 86;
      const pos = groups.map((_, i) => {
        const ang = -Math.PI / 2 + 2 * Math.PI * i / groups.length;
        return [cx + Math.cos(ang) * R, cy + Math.sin(ang) * R];
      });
      const NS = "http://www.w3.org/2000/svg";
      const holder = el('<div></div>');
      let svgStr = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto" id="ring-svg">`;
      for (const [key, w] of cross) {
        const [a, b] = key.split('§').map(Number);
        if (!pos[a] || !pos[b]) continue;
        const op = Math.min(0.5, 0.08 + w / 300);
        svgStr += `<line x1="${pos[a][0]}" y1="${pos[a][1]}" x2="${pos[b][0]}" y2="${pos[b][1]}"
          stroke="var(--line)" stroke-width="${Math.min(6, 0.8 + w / 120)}" opacity="${op}"/>`;
      }
      holder.innerHTML = svgStr + '</svg>';
      const svgEl = holder.firstChild;
      const maxN = Math.max(...groups.map(g => g.nodes.length), 1);
      groups.forEach((g, gi) => {
        const n = g.nodes.length;
        const r = 16 + Math.sqrt(n) * 3.6;
        const hue = [...g.label].reduce((h, ch) => (h * 31 + ch.codePointAt(0)) % 360, 0);
        const gEl = document.createElementNS(NS, 'g');
        gEl.setAttribute('transform', `translate(${pos[gi][0]},${pos[gi][1]})`);
        gEl.style.cursor = 'pointer';
        const name = g.label.length > 14 ? g.label.slice(0, 14) + '…' : g.label;
        gEl.innerHTML = `<circle r="${r}" fill="hsl(${hue},62%,55%)" stroke="var(--card)" stroke-width="2" opacity="0.92"/>
          <text y="6" text-anchor="middle" font-size="15" font-weight="600" fill="#fff" pointer-events="none">${n}</text>
          <text y="${r + 18}" text-anchor="middle" font-size="13" fill="var(--muted)" pointer-events="none">${escape(name)}</text>
          <title>${escape(g.label)} · ${n} 篇，点击继续下钻</title>`;
        gEl.onclick = () => onPick(gi);
        svgEl.appendChild(gEl);
      });
      stage.appendChild(svgEl);
      stage.appendChild(el('<div style="font-size:12px;color:var(--muted);padding:6px 4px">圆圈内数字=篇数 · 连线粗细=两组文章的关联量 · 点击下钻（每层 ≤' + MAX_NODES + ' 节点）</div>'));
    }

    // ---- 文章层（≤MAX 篇）：静态子图 ----
    function drawArticleLayer(nodes) {
      const ids = new Set(nodes.map(n => n.id));
      const edges = graph.edges.filter(e => ids.has(e.src) && ids.has(e.dst));
      const box = el('<div></div>');
      stage.appendChild(box);
      renderGraph(box, { nodes: nodes.map(n => ({ ...n })), edges }, {
        height: Math.max(420, Math.min(640, 240 + nodes.length * 36)),
        onNodeClick: (n) => openArticle(n.id, { library: lib }),
      });
    }

    // ---- 全景大图（可按标题过滤） ----
    function drawFull() {
      const kw = fltInput.value.trim();
      crumb.textContent = kw ? `过滤：“${kw}”` : `全部 ${graph.nodes.length} 篇（拖拽 / 滚轮缩放 / 点节点开文章）`;
      let nodes = graph.nodes.map(n => ({ ...n }));
      let edges = graph.edges;
      if (kw) {
        const ids = new Set(nodes.filter(n => n.title.toLowerCase().includes(kw.toLowerCase())).map(n => n.id));
        nodes = nodes.filter(n => ids.has(n.id));
        edges = edges.filter(e => ids.has(e.src) && ids.has(e.dst));
        fltClear.style.display = '';
        if (!nodes.length) { stage.appendChild(el('<div class="empty" style="padding:30px"><div class="title">没有标题含该关键词的文章</div></div>')); return; }
      } else {
        fltClear.style.display = 'none';
      }
      renderGraph(stage, { nodes, edges }, {
        height: Math.max(560, window.innerHeight - 260),
        onNodeClick: (n) => openArticle(n.id, { library: lib }),
      });
    }

    draw();
  },
};
