// AI 用量页（v1.10）：本地记账——今日/本月汇总、逐日趋势、按模型/按功能明细、单价可改
import { api } from '../api.js';
import { el, escape, toast } from './kit.js';

const fmtCost = (v) => {
  if (v == null) return '—';
  if (v >= 100) return '¥' + v.toFixed(1);
  if (v >= 1) return '¥' + v.toFixed(2);
  if (v >= 0.01) return '¥' + v.toFixed(3);
  return v > 0 ? '¥' + v.toFixed(4) : '¥0';
};
const fmtTok = (n) => n >= 10000 ? (n / 10000).toFixed(1) + '万' : String(n ?? 0);

export default {
  id: 'usage',
  title: 'AI 用量',
  icon: '💰',
  async render(container, rerender) {
    const refresh = () => rerender ? rerender() : location.reload();
    const [sum, prices] = await Promise.all([
      api('/api/usage/summary?days=30'), api('/api/usage/prices'),
    ]);

    container.appendChild(el(`
      <div class="page-head"><h1>AI 用量</h1>
      <p>每次 AI 调用自动记账 · 花费按单价折算（参考价可改成你中转站的实际价）</p></div>`));

    if (!sum.all.calls) {
      container.appendChild(el(`<div class="card"><div class="empty" style="padding:26px">
        <div class="title">还没有 AI 调用记录</div>
        <div>启用 AI 后，问答 / 每日建议 / 学习卡片 / 语义嵌入的每次调用都会记在这里<br>
        （历史从本功能启用开始累积，之前的调用没有留痕）</div></div></div>`));
      return;
    }

    // ---- 汇总卡 ----
    const cards = el(`<div class="stat-row" style="margin-bottom:16px">
      <div class="stat"><b>${sum.today.calls}</b><span>今日调用</span></div>
      <div class="stat"><b>${fmtTok(sum.today.prompt_tokens + sum.today.completion_tokens)}</b><span>今日 token</span></div>
      <div class="stat"><b>${fmtCost(sum.today.cost)}</b><span>今日花费</span></div>
      <div class="stat"><b>${sum.month.calls}</b><span>本月调用</span></div>
      <div class="stat"><b>${fmtTok(sum.month.prompt_tokens + sum.month.completion_tokens)}</b><span>本月 token</span></div>
      <div class="stat"><b>${fmtCost(sum.month.cost)}</b><span>本月花费</span></div>
      <div class="stat"><b>${fmtCost(sum.all.cost)}</b><span>累计花费（${sum.all.calls} 次）</span></div>
    </div>`);
    container.appendChild(cards);

    // ---- 30 天趋势（CSS 柱图：高度=花费，hover 显示明细） ----
    const maxCost = Math.max(...sum.trend.map(d => d.cost), 0.000001);
    const trendCard = el(`<div class="card" style="margin-bottom:16px">
      <div class="card-title">📈 近 30 天花费趋势 <span class="hint">柱=花费，悬停看明细</span></div>
      <div class="trend" style="display:flex;align-items:flex-end;gap:3px;height:110px;padding:6px 2px 0"></div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);padding:4px 2px 0">
        <span>${sum.trend[0].day.slice(5)}</span><span>${sum.trend[sum.trend.length - 1].day.slice(5)}</span></div></div>`);
    const tBox = trendCard.querySelector('.trend');
    sum.trend.forEach(d => {
      const h = Math.max(d.cost > 0 ? 6 : 2, Math.round(d.cost / maxCost * 96));
      const bar = el(`<div title="${d.day} · ${d.calls} 次 · ${fmtTok(d.prompt_tokens + d.completion_tokens)} tok · ${fmtCost(d.cost)}"
        style="flex:1;height:${h}px;border-radius:3px 3px 0 0;background:${d.cost > 0 ? 'var(--accent)' : 'var(--line)'}"></div>`);
      tBox.appendChild(bar);
    });
    container.appendChild(trendCard);

    // ---- 按模型（含单价编辑；真实花费=未命中输入×全价+缓存命中×折扣价+输出×输出价） ----
    const modelCard = el(`<div class="card" style="margin-bottom:16px">
      <div class="card-title">🤖 按模型明细 <span class="hint">单价=元/百万token（参考价，改成实际价后全部历史重算；花费=未命中输入+缓存命中+输出）</span></div>
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead><tr style="color:var(--muted);text-align:left">
          <th style="padding:6px 4px">模型</th><th>次数</th><th>输入tok</th><th>缓存命中tok</th><th>输出tok</th><th>花费</th>
          <th>输入单价</th><th>命中单价</th><th>输出单价</th><th></th></tr></thead>
        <tbody class="m-rows"></tbody></table></div>`);
    const mRows = modelCard.querySelector('.m-rows');
    prices.models.forEach(m => {
      const hasCached = m.cached_tokens > 0;
      const miss = Math.max(0, m.prompt_tokens - m.cached_tokens);
      const cost = (miss * m.price_in + m.cached_tokens * m.price_hit
        + m.completion_tokens * m.price_out) / 1e6;
      const tr = el(`<tr style="border-top:1px solid var(--line)">
        <td style="padding:7px 4px"><b>${escape(m.model)}</b>${m.priced ? '' : ' <span class="badge amber">未定价</span>'}
          <div style="font-size:11px;color:var(--muted)">${escape(m.provider || '')}</div></td>
        <td>${m.calls}</td><td>${fmtTok(m.prompt_tokens)}</td>
        <td ${hasCached ? '' : 'title="上游未返回缓存命中信息（DeepSeek 系返回 prompt_cache_hit_tokens，OpenAI 系返回 prompt_tokens_details.cached_tokens）"'}>${hasCached ? fmtTok(m.cached_tokens) : '—'}</td>
        <td>${fmtTok(m.completion_tokens)}</td>
        <td><b title="未命中输入 ${fmtTok(miss)}×¥${m.price_in} + 缓存命中 ${fmtTok(m.cached_tokens)}×¥${m.price_hit} + 输出 ${fmtTok(m.completion_tokens)}×¥${m.price_out}">${fmtCost(cost)}</b></td>
        <td><input class="p-in" type="number" step="0.1" min="0" value="${m.price_in}" style="width:70px;padding:4px 6px"></td>
        <td><input class="p-hit" type="number" step="0.05" min="0" value="${m.price_hit}" style="width:70px;padding:4px 6px"></td>
        <td><input class="p-out" type="number" step="0.1" min="0" value="${m.price_out}" style="width:70px;padding:4px 6px"></td>
        <td><button class="btn p-save" style="padding:3px 10px;font-size:12px">改价</button></td></tr>`);
      tr.querySelector('.p-save').onclick = async () => {
        try {
          await api('/api/usage/prices', { method: 'PUT', body: {
            model: m.model,
            price_in: +tr.querySelector('.p-in').value || 0,
            price_hit: tr.querySelector('.p-hit').value,
            price_out: +tr.querySelector('.p-out').value || 0 } });
          toast(`已更新 ${m.model} 单价，花费已重算`); refresh();
        } catch (e) { toast(e.message, false); }
      };
      mRows.appendChild(tr);
    });
    container.appendChild(modelCard);

    // ---- 按功能 ----
    const featCard = el(`<div class="card">
      <div class="card-title">🧩 按功能明细</div>
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead><tr style="color:var(--muted);text-align:left">
          <th style="padding:6px 4px">功能</th><th>次数</th><th>输入tok</th><th>输出tok</th><th>花费</th></tr></thead>
        <tbody>${sum.by_feature.map(f => `
          <tr style="border-top:1px solid var(--line)">
            <td style="padding:7px 4px"><b>${escape(f.feature)}</b></td>
            <td>${f.calls}</td><td>${fmtTok(f.prompt_tokens)}</td><td>${fmtTok(f.completion_tokens)}</td>
            <td><b>${fmtCost(f.cost)}</b></td></tr>`).join('')}</tbody></table></div>`);
    container.appendChild(featCard);
  },
};
