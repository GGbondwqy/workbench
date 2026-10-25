// 复习模式（F13）：AI 出变体题 / 降级卡片自测 → Ebbinghaus 评分
import { api } from '../../api.js';
import { el, escape, toast } from '../kit.js';

export async function startReviewSession(container, onDone) {
  const { quizzes, stats } = await api('/api/learn/due?n=10');
  container.innerHTML = "";
  container.appendChild(el(`<div class="page-head"><h1>🧠 复习模式</h1>
    <p>本次 ${quizzes.length} 张卡片 · 到期 ${stats.due} · 薄弱 ${stats.weak} · 已掌握 ${stats.done}
    ${quizzes[0]?.ai_generated === false ? ' · AI 未配置（原题自测）' : ' · AI 出题中'}</p></div>`));
  if (!quizzes.length) {
    container.appendChild(el(`<div class="card"><div class="empty"><span class="icon">🎉</span>
      <div class="title">没有待复习的卡片</div>
      <div>去八股学习读文章、点"不懂就问"，问题会自动变成卡片</div></div></div>`));
    return;
  }
  let i = 0, passed = 0;
  const box = el('<div class="card"></div>');
  container.appendChild(box);
  const renderCard = () => {
    box.innerHTML = "";
    if (i >= quizzes.length) {
      api('/api/vocab/finish', { method: 'POST', body: { count: passed } });
      box.appendChild(el(`<div class="empty"><span class="icon">✅</span>
        <div class="title">本轮复习完成（${passed}/${quizzes.length} 过）</div>
        <div>评分已按记忆曲线调度下次复习时间</div></div>`));
      onDone && onDone();
      return;
    }
    const { card, quiz, ai_generated } = quizzes[i];
    box.appendChild(el(`<div style="display:flex;justify-content:space-between;color:var(--muted);font-size:12px">
      <span>${i + 1} / ${quizzes.length} · ${escape(card.chapter)}</span>
      <span>${ai_generated ? '🤖 AI 变体题' : '📖 原题自测'} · 阶段 ${card.stage}</span></div>
      <div class="flash-word" style="font-size:22px;padding:26px 0 10px">${escape(quiz)}</div>
      <div class="flash-meaning" style="opacity:.12">💡 ${escape(card.a || '（此卡无答案，请凭记忆回想，可翻原文）')}</div>
      <div style="text-align:center;margin-top:12px"><button class="btn show">显示答案</button></div>
      <div class="grade-row" style="display:none">
        <button class="btn" data-r="fail">❌ 没过</button>
        <button class="btn" data-r="fuzzy">🤔 含糊</button>
        <button class="btn" data-r="pass">✅ 过了</button>
      </div>`));
    const ans = box.querySelector(".flash-meaning");
    box.querySelector(".show").onclick = () => {
      ans.style.opacity = "1";
      box.querySelector(".show").parentElement.style.display = "none";
      box.querySelector(".grade-row").style.display = "flex";
    };
    box.querySelectorAll("[data-r]").forEach(b => b.onclick = async () => {
      try {
        await api(`/api/learn/review/${card.id}`, { method: 'POST', body: { result: b.dataset.r } });
      } catch (e) { toast(e.message, false); }
      if (b.dataset.r === "pass") passed++;
      i++; renderCard();
    });
  };
  renderCard();
}
