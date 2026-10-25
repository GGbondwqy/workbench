// 知识图谱组件 v2：后端预计算布局，前端纯静态渲染 + 拖拽/缩放（零 rAF 循环，不卡页面）
// 用法: renderGraph(container, {nodes(含x,y), edges}, {onNodeClick, height})
export function renderGraph(container, data, opts = {}) {
  const { nodes, edges } = data;
  const W = 1000, H = 800;
  const NS = "http://www.w3.org/2000/svg";

  const catColor = (c) => {
    let h = 0;
    for (const ch of String(c || "其他")) h = (h * 31 + ch.codePointAt(0)) % 360;
    return `hsl(${h}, 62%, 55%)`;
  };

  // 边截断：wikilink/manual 全留 + auto 按权重补足到 900
  const keep = edges.filter(e => e.type !== "auto");
  const auto = edges.filter(e => e.type === "auto")
    .sort((a, b) => b.weight - a.weight).slice(0, Math.max(0, 900 - keep.length));
  const E = [...keep, ...auto];
  const idx = new Map(nodes.map((n, i) => [n.id, i]));
  const maxDeg = Math.max(...nodes.map(n => n.degree || 0), 1);
  const rOf = n => 4 + Math.log2((n.degree || 0) + 1) * 3.2;

  container.innerHTML = "";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("width", "100%"); svg.setAttribute("height", opts.height || 560);
  svg.style.cursor = "grab"; svg.style.touchAction = "none";
  container.appendChild(svg);
  const gRoot = document.createElementNS(NS, "g");
  svg.appendChild(gRoot);
  const gEdges = document.createElementNS(NS, "g");
  const gNodes = document.createElementNS(NS, "g");
  gRoot.appendChild(gEdges); gRoot.appendChild(gNodes);

  const lineEls = E.map(e => {
    const l = document.createElementNS(NS, "line");
    l.setAttribute("stroke", e.type === "wikilink" ? "var(--amber)" :
      e.type === "manual" ? "var(--accent)" : "var(--line)");
    l.setAttribute("stroke-width", e.type === "auto" ? 0.6 + (e.weight || 1) * 0.12 : 2);
    l.setAttribute("opacity", e.type === "auto" ? 0.45 : 0.9);
    gEdges.appendChild(l);
    return l;
  });
  const drawEdges = () => {
    for (let i = 0; i < E.length; i++) {
      const a = nodes[idx.get(E[i].src)], b = nodes[idx.get(E[i].dst)];
      if (!a || !b) continue;
      lineEls[i].setAttribute("x1", a.x); lineEls[i].setAttribute("y1", a.y);
      lineEls[i].setAttribute("x2", b.x); lineEls[i].setAttribute("y2", b.y);
    }
  };
  drawEdges();

  let dragging = null, dragOff = [0, 0], dragMoved = false;
  nodes.forEach(n => {
    const g = document.createElementNS(NS, "g");
    g.setAttribute("transform", `translate(${n.x},${n.y})`);
    g.style.cursor = "pointer";
    const c = document.createElementNS(NS, "circle");
    c.setAttribute("r", rOf(n));
    c.setAttribute("fill", catColor(n.category));
    c.setAttribute("stroke", "var(--card)"); c.setAttribute("stroke-width", 1.5);
    const t = document.createElementNS(NS, "title");
    t.textContent = `${n.title}（关联 ${n.degree || 0}）`;
    g.appendChild(c); g.appendChild(t);
    if ((n.degree || 0) >= maxDeg * 0.3) {
      const label = document.createElementNS(NS, "text");
      label.setAttribute("x", rOf(n) + 4); label.setAttribute("y", 4);
      label.setAttribute("font-size", 11); label.setAttribute("fill", "var(--muted)");
      label.textContent = n.title.length > 12 ? n.title.slice(0, 12) + "…" : n.title;
      g.appendChild(label);
    }
    g.addEventListener("pointerdown", (ev) => {
      ev.stopPropagation();
      dragging = { n, g };
      dragMoved = false;
      const [mx, my] = toLocal(ev);
      dragOff = [n.x - mx, n.y - my];
      svg.setPointerCapture(ev.pointerId);
    });
    g.addEventListener("click", (ev) => {
      ev.stopPropagation();
      if (!dragMoved) opts.onNodeClick && opts.onNodeClick(n);
    });
    gNodes.appendChild(g);
  });

  const toLocal = (ev) => {
    const rect = svg.getBoundingClientRect();
    const s = W / rect.width;   // viewBox 等比缩放
    return [(ev.clientX - rect.left) * s, (ev.clientY - rect.top) * s];
  };
  svg.addEventListener("pointermove", (ev) => {
    if (!dragging) return;
    const [mx, my] = toLocal(ev);
    dragging.n.x = Math.max(6, Math.min(W - 6, mx + dragOff[0]));
    dragging.n.y = Math.max(6, Math.min(H - 6, my + dragOff[1]));
    dragMoved = true;
    dragging.g.setAttribute("transform", `translate(${dragging.n.x},${dragging.n.y})`);
    drawEdges();
  });
  const endDrag = () => { dragging = null; };
  svg.addEventListener("pointerup", endDrag);
  svg.addEventListener("pointercancel", endDrag);

  svg.addEventListener("wheel", (ev) => {
    ev.preventDefault();
    const k = ev.deltaY < 0 ? 1.12 : 0.89;
    const cur = gRoot.transform.baseVal.numberOfItems ?
      gRoot.transform.baseVal.getItem(0).matrix.a : 1;
    const ns = Math.max(0.3, Math.min(4, cur * k));
    const [cx, cy] = toLocal(ev);
    gRoot.setAttribute("transform", `translate(${cx},${cy}) scale(${ns}) translate(${-cx},${-cy})`);
  }, { passive: false });

  const legend = document.createElement("div");
  legend.style.cssText = "display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin-top:8px";
  legend.innerHTML = `<span>⚪ 节点=文章（大小=关联数，颜色=栏目）</span>
    <span style="color:var(--muted)">─ 自动关联</span>
    <span style="color:var(--amber)">━ 双链引用</span>
    <span>🖱 拖拽 / 滚轮缩放 / 点击开文章</span>`;
  container.appendChild(legend);
}
