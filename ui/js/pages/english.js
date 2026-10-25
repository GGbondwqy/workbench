// 雅思备考页（v1.3 五模块）：刷题 / 真题与错题 / 口语 / 写作 / 模考与设置
import { api } from '../api.js';
import { el, escape, toast, todayStr, confirmBox } from './kit.js';

const KIND_CN = { full: "全真模考", listening: "听力", reading: "阅读", writing: "写作", speaking: "口语" };
const SUB_CN = { listening: "听力", reading: "阅读" };
const SRC_CN = { builtin: "内置仿真", public: "公开收集", manual: "自建" };
const TYPE_CN = { choice: "单选", tfng: "判断", blank: "填空" };
const TABS = [
  ["practice", "✍️ 刷题"], ["tests", "📈 真题与错题"], ["speaking", "🗣 口语"],
  ["writing", "📝 写作"], ["mock", "🗓 模考与设置"],
];

export default {
  id: 'english',
  title: '雅思备考',
  icon: '🇬🇧',
  async render(container, rerender) {
    const refresh = () => rerender ? rerender() : location.reload();
    let tab = (location.hash.split("/")[2] || "practice");
    if (!TABS.some(([k]) => k === tab)) tab = "practice";

    container.appendChild(el(`
      <div class="page-head"><h1>雅思备考</h1>
      <p>刷题（听力/阅读）· 真题与错题 · 口语 · 写作 · 模考</p></div>`));
    const tabBar = el(`<div style="display:flex;gap:8px;margin-bottom:16px;border-bottom:1px solid var(--line);padding-bottom:10px;flex-wrap:wrap"></div>`);
    TABS.forEach(([k, label]) => {
      const b = el(`<button class="btn" style="${k === tab ? "border-color:var(--accent);color:var(--accent-text);font-weight:600" : ""}">${label}</button>`);
      b.onclick = () => { location.hash = `#/english/${k}`; };
      tabBar.appendChild(b);
    });
    container.appendChild(tabBar);
    const body = el('<div></div>');
    container.appendChild(body);

    if (tab === "tests") return renderTests(body, refresh);
    if (tab === "speaking") return renderSpeaking(body, refresh);
    if (tab === "writing") return renderWriting(body, refresh);
    if (tab === "mock") return renderMock(body, refresh);
    return renderPractice(body, refresh);
  },
};

// ================= Tab 1: 刷题 =================
async function renderPractice(container, refresh) {
  let subject = "listening";
  const [bank, attempts, cfg] = await Promise.all([
    api('/api/ielts/bank'), api('/api/ielts/attempts'), api('/api/ielts/config'),
  ]);

  // 按科目统计行
  const accOf = (s) => attempts.stats.find(x => x.subject === s);
  const head = el(`<div class="stat-row" style="margin-bottom:14px">
    <div class="stat"><b>${bank.items.length}</b><span>可用题组</span></div>
    ${["listening", "reading"].map(s => {
      const a = accOf(s);
      return `<div class="stat"><b>${a ? a.accuracy + "%" : "—"}</b><span>${SUB_CN[s]}正确率（${a ? a.attempts : 0} 次）</span></div>`;
    }).join("")}
  </div>`);
  container.appendChild(head);

  // 考试安排卡片（v1.9：机考说明 + 报名官网 + 自设考试日倒计时；不编造具体考次日期）
  const examCard = el(`<div class="card" style="margin-bottom:14px">
    <div class="card-title">🗓 雅思考试安排 <span class="hint">大陆已全面机考 · 考位以官网为准</span></div>
    <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap">
      <div style="flex:1;min-width:260px;font-size:13.5px">
        报名与考位查询：<a href="https://ielts.neea.edu.cn" target="_blank" rel="noopener">教育部考试院雅思报名网 ielts.neea.edu.cn ↗</a>
        <div style="color:var(--muted);font-size:12px;margin-top:4px">
          中国大陆自 2026 年 9 月起全面转为机考（纸笔已停开）。机考几乎每天都有考位、出分约 3-5 天，
          想考“最近一两次”直接上官网挑最近的日期即可。</div>
      </div>
      <div class="exam-count" style="text-align:right"></div>
    </div></div>`);
  const cnt = examCard.querySelector(".exam-count");
  if (cfg.days_left == null) {
    cnt.innerHTML = `<div style="display:flex;gap:6px;align-items:center">
      <input type="date" class="e-date" style="width:140px">
      <button class="btn e-save" style="padding:4px 12px">设定考试日</button></div>
      <div style="font-size:12px;color:var(--muted);margin-top:4px">设定后这里显示倒计时</div>`;
    cnt.querySelector(".e-save").onclick = async () => {
      const d = cnt.querySelector(".e-date").value;
      if (!d) return toast("请先选择考试日期", false);
      try { await api('/api/ielts/config', { method: 'PUT', body: { exam_date: d } }); }
      catch (e) { return toast(e.message, false); }
      toast("已设定，倒计时生效"); refresh();
    };
  } else if (cfg.days_left >= 0) {
    cnt.innerHTML = `<div style="font-size:24px;font-weight:700">⏳ ${cfg.days_left} 天</div>
      <div style="font-size:12px;color:var(--muted)">距 ${escape(cfg.exam_date)} · 到「模考与设置」页可修改</div>`;
  } else {
    cnt.innerHTML = `<div style="font-size:19px;font-weight:700">🎉 已考完</div>
      <div style="font-size:12px;color:var(--muted)">${escape(cfg.exam_date)} · 等分中</div>`;
  }
  container.appendChild(examCard);

  // 科目切换 + 导入入口 + 新闻出题（v1.14）
  const bar = el(`<div class="inline-form" style="margin-bottom:14px">
    <button class="btn s-listening">🎧 听力</button>
    <button class="btn s-reading">📖 阅读</button>
    <span style="flex:1"></span>
    <button class="btn news-toggle">📰 新闻出题</button>
    <button class="btn imp-toggle">＋ 导入题组</button></div>`);
  const markSub = () => ["listening", "reading"].forEach(s =>
    bar.querySelector(`.s-${s}`).style.cssText = s === subject
      ? "border-color:var(--accent);color:var(--accent-text);font-weight:600" : "");
  bar.querySelector(".s-listening").onclick = () => { subject = "listening"; markSub(); drawList(); };
  bar.querySelector(".s-reading").onclick = () => { subject = "reading"; markSub(); drawList(); };
  container.appendChild(bar);
  markSub();

  // 导入卡片（手工导入 F18）
  const impCard = el(`<div class="card" style="display:none;margin-bottom:14px"><div class="card-title">＋ 手工导入题组
    <span class="hint">粘贴 JSON（公开收集的题整理成本格式后导入，只存本机）</span></div>
    <details style="font-size:12.5px;color:var(--muted);margin-bottom:8px"><summary>查看格式示例</summary>
      <pre style="background:var(--card-2);padding:10px;border-radius:8px;overflow:auto;font-size:12px">{
  "title": "剑19 Test1 阅读 P1（公开收集）",
  "subject": "reading",
  "sections": [{
    "intro": "Questions 1-5",
    "material": "阅读原文……",
    "questions": [
      { "no": 1, "type": "choice", "stem": "The writer thinks…",
        "options": ["A…", "B…", "C…"], "answer": "B", "explain": "出处" },
      { "no": 2, "type": "tfng", "stem": "……",
        "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "NG" },
      { "no": 3, "type": "blank", "stem": "______", "answer": "pollution" }
    ]
  }]
}</pre></details>
    <textarea rows="6" style="width:100%" placeholder='粘贴题组 JSON…'></textarea>
    <div style="margin-top:8px"><button class="btn btn-primary imp-go">导入</button>
    <input type="file" accept=".json" style="display:none" class="imp-file">
    <button class="btn imp-up">上传 .json 文件</button>
    <span class="imp-msg" style="margin-left:10px;font-size:12.5px;color:var(--muted)"></span></div></div>`);
  bar.querySelector(".imp-toggle").onclick = () => {
    impCard.style.display = impCard.style.display === 'none' ? '' : 'none';
  };
  impCard.querySelector(".imp-go").onclick = async () => {
    const text = impCard.querySelector("textarea").value.trim();
    if (!text) return toast("请粘贴 JSON", false);
    try {
      const r = await api('/api/ielts/bank/import', { method: 'POST', body: { json: text } });
      toast(`已导入「${r.id}」（${r.n_questions} 题）`); refresh();
    } catch (e) { impCard.querySelector(".imp-msg").textContent = e.message; toast(e.message, false); }
  };
  impCard.querySelector(".imp-up").onclick = () => impCard.querySelector(".imp-file").click();
  impCard.querySelector(".imp-file").onchange = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const text = await f.text();
    try {
      const r = await api('/api/ielts/bank/import', { method: 'POST', body: { json: text } });
      toast(`已导入「${r.id}」（${r.n_questions} 题）`); refresh();
    } catch (err) { toast(err.message, false); }
  };
  container.appendChild(impCard);

  // 新闻出题面板（v1.14：BBC/VOA 纯脚本出题，不用 AI）
  const newsCard = el(`<div class="card" style="display:none;margin-bottom:14px">
    <div class="card-title">📰 新闻出题 <span class="hint">拉取 BBC / VOA 最新文章，程序自动生成挖空+选词题（不用 AI、零费用）</span></div>
    <div class="inline-form" style="flex-wrap:wrap">
      <select class="n-kind">
        <option value="listening">🎧 听力（BBC 6 Minute English 真音频+文稿 / VOA）</option>
        <option value="reading">📖 阅读（BBC News / VOA 文章）</option>
      </select>
      <select class="n-source">
        <option value="auto">自动选源</option>
        <option value="bbc">BBC 优先</option>
        <option value="voa">VOA 优先</option>
      </select>
      <select class="n-count"><option value="1">1 套</option><option value="2" selected>2 套</option>
        <option value="3">3 套</option><option value="5">5 套</option></select>
      <button class="btn btn-primary n-go">拉取并生成</button>
      <span class="n-msg" style="font-size:12.5px;color:var(--muted)"></span></div>
    <p style="color:var(--muted);font-size:12px;margin:8px 0 0">
      做过的文章自动跳过；抓到真音频时下载到本机走原生播放器，否则用机器朗读。原文与音频只存本机。</p></div>`);
  bar.querySelector(".news-toggle").onclick = () => {
    newsCard.style.display = newsCard.style.display === 'none' ? '' : 'none';
  };
  newsCard.querySelector(".n-go").onclick = async () => {
    const msg = newsCard.querySelector(".n-msg");
    msg.textContent = "抓取中（含音频下载，最长约 1-2 分钟）…";
    try {
      const r = await api('/api/ielts/news/fetch', { method: 'POST', body: {
        kind: newsCard.querySelector(".n-kind").value,
        source: newsCard.querySelector(".n-source").value,
        count: +newsCard.querySelector(".n-count").value } });
      const done = (r.items || []).map(i => `「${i.title}」${i.n_questions} 题${i.has_audio ? ' 🎧真音频' : ''}`);
      msg.textContent = done.length
        ? `✅ 生成 ${done.length} 套：${done.join('；')}${r.failed?.length ? '｜部分失败：' + r.failed.join('；') : ''}`
        : `没有新题可生成（${r.skipped?.length || 0} 篇已做过；${(r.failed || []).join('；') || '源暂无可抓文章'}）`;
      msg.style.color = done.length ? 'var(--green)' : 'var(--amber)';
      if (done.length) { toast(`已生成 ${done.length} 套新闻题`); refresh(); }
    } catch (e) {
      msg.textContent = `❌ ${e.message}`;
      msg.style.color = 'var(--red,crimson)';
    }
  };
  container.appendChild(newsCard);

  const listBox = el('<div></div>');
  container.appendChild(listBox);

  function drawList() {
    const sets = bank.items.filter(s => s.subject === subject);
    listBox.innerHTML = '';
    if (!sets.length) {
      listBox.appendChild(el(`<div class="card"><div class="empty" style="padding:20px">
        <div class="title">该科目暂无题组</div>
        <div>点右上角「导入题组」，或把公开收集的 .json 放进 data/ielts_bank/ 文件夹</div></div></div>`));
      return;
    }
    const grid = el('<div class="grid cols-2"></div>');
    sets.forEach(s => {
      const deletable = s.source !== "builtin";   // v1.19：新闻/导入题组可删（内置 seed 拒删）
      const card = el(`<div class="card">
        <div class="card-title" style="display:flex;gap:6px;align-items:center">
          <span style="flex:1;min-width:0">${escape(s.title)}</span>
          <span class="badge gray">${SRC_CN[s.source] || s.source}</span>
          ${deletable ? '<button class="btn s-del" style="padding:1px 7px;font-size:12px" title="删除题组">✕</button>' : ''}</div>
        <div style="font-size:13px;color:var(--muted);margin-bottom:10px">
          ${SUB_CN[s.subject]} · ${s.n_questions} 题${s.best != null ? ` · 个人最好 ${s.best}%` : ' · 未做过'}</div>
        <button class="btn btn-primary go">▶ 开始做题</button></div>`);
      card.querySelector(".go").onclick = async () => {
        const set = await api(`/api/ielts/bank/${encodeURIComponent(s.id)}`);
        openSession(set);
      };
      const sdel = card.querySelector(".s-del");
      if (sdel) sdel.onclick = async () => {
        if (!(await confirmBox(`删除题组《${s.title}》？
该题组的作答留痕与相关错题将一并删除（内置仿真题不受影响）。`))) return;
        try { await api(`/api/ielts/bank/${encodeURIComponent(s.id)}`, { method: 'DELETE' }); toast('已删除'); refresh(); }
        catch (e) { toast(e.message, false); }
      };
      grid.appendChild(card);
    });
    listBox.appendChild(grid);
  }

  function openSession(set) {
    stopTts();
    container.innerHTML = '';
    container.appendChild(el(`<div class="inline-form" style="margin-bottom:12px">
      <button class="btn back">← 返回题库</button>
      <b style="font-size:15px">${escape(set.title)}</b>
      <span class="badge gray">${SRC_CN[set.source] || set.source}</span></div>`));
    container.querySelector(".back").onclick = refresh;

    const answers = {};
    set.sections.forEach((sec, si) => {
      const isListen = set.subject === "listening";
      const secCard = el(`<div class="card" style="margin-bottom:14px">
        <div class="card-title">第 ${si + 1} 节 ${sec.intro ? '· ' + escape(sec.intro) : ''}</div>
        ${isListen ? `
        <div class="aud" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:10px;background:var(--card-2);border-radius:8px;margin-bottom:10px">
          <b style="font-size:13px">🎧 音频</b>
          <audio controls preload="metadata" style="display:none;height:34px;flex:1;min-width:210px"
            src="/api/ielts/audio/${encodeURIComponent(set.id)}/${si}"></audio>
          <span class="aud-msg" style="font-size:12px;color:var(--muted);flex:1;min-width:120px"></span>
          <button class="btn tts-play" style="padding:4px 12px">▶ 机器朗读</button>
          <button class="btn tts-pause" style="padding:4px 12px">⏸ 暂停</button>
          <button class="btn tts-stop" style="padding:4px 12px">⏹ 停止</button>
          <label style="font-size:12px">语速
            <select class="tts-rate"><option value="0.75">0.75×</option>
              <option value="1" selected>1×</option><option value="1.25">1.25×</option></select></label>
        </div>` : ''}
        ${isListen
          ? `<details class="mat" style="margin-bottom:10px"><summary style="cursor:pointer;font-size:13px;color:var(--muted)">🎧 听力原文（建议提交后再展开）</summary>
             <pre style="white-space:pre-wrap;font-size:13px;margin-top:8px">${escape(sec.material)}</pre></details>`
          : `<div class="mat md-view" style="font-size:14px;margin-bottom:12px;white-space:pre-wrap">${escape(sec.material)}</div>`}
        <div class="qs"></div></div>`);
      if (isListen) attachPlayer(secCard.querySelector(".aud"), sec.material);
      const qs = secCard.querySelector(".qs");
      sec.questions.forEach(q => {
        const row = el(`<div style="padding:10px 0;border-bottom:1px solid var(--line)">
          <div style="font-size:13.5px;margin-bottom:8px"><b>Q${q.no}</b> <span class="badge gray">${TYPE_CN[q.type]}</span> ${escape(q.stem)}</div>
          <div class="ans"></div></div>`);
        const box = row.querySelector(".ans");
        if (q.type === "choice" || q.type === "tfng") {
          const opts = q.options || ["TRUE", "FALSE", "NOT GIVEN"];
          opts.forEach((o, oi) => {
            const L = q.type === "choice" ? "ABCDEF"[oi] : "";
            const b = el(`<label style="display:block;padding:4px 8px;font-size:13.5px;cursor:pointer;border-radius:6px">
              <input type="radio" name="q${q.no}" value="${escape(o)}" style="margin-right:6px">${L ? `<b>${L}.</b> ` : ''}${escape(o)}</label>`);
            b.querySelector("input").onchange = () => { answers[q.no] = o; };
            box.appendChild(b);
          });
        } else {
          const inp = el(`<input placeholder="填空：输入答案" style="width:280px;padding:6px 10px">`);
          inp.oninput = () => { answers[q.no] = inp.value; };
          box.appendChild(inp);
        }
        qs.appendChild(row);
      });
      container.appendChild(secCard);
    });

    const submit = el('<button class="btn btn-primary" style="font-size:15px;padding:8px 24px">✓ 提交答案</button>');
    submit.onclick = async () => {
      stopTts();
      const r = await api(`/api/ielts/bank/${encodeURIComponent(set.id)}/submit`,
        { method: 'POST', body: { answers } });
      showResult(set, r);
    };
    container.appendChild(submit);
  }

  function showResult(set, r) {
    stopTts();
    container.innerHTML = '';
    container.appendChild(el(`<div class="inline-form" style="margin-bottom:12px">
      <button class="btn back">← 返回题库</button>
      <b style="font-size:15px">${escape(r.title)} · 结果</b></div>`));
    container.querySelector(".back").onclick = refresh;
    container.appendChild(el(`<div class="card" style="margin-bottom:14px;text-align:center;padding:18px">
      <div style="font-size:34px;font-weight:700;color:${r.score >= 60 ? 'var(--green)' : 'var(--amber)'}">${r.correct}/${r.total}</div>
      <div style="color:var(--muted);font-size:13px">正确率 ${r.score}% · 错题已自动记入错题本 · ${
        set.subject === 'listening' ? '听力' : '阅读'}目标推进 +1</div></div>`));

    set.sections.forEach(sec => {
      const secCard = el(`<div class="card" style="margin-bottom:14px">
        <details class="mat" ${set.subject === 'reading' ? 'open' : ''}>
          <summary style="cursor:pointer;font-size:13px;color:var(--muted)">原文${set.subject === 'listening' ? '（对答案参考）' : ''}</summary>
          <pre style="white-space:pre-wrap;font-size:13px;margin-top:8px">${escape(sec.material)}</pre></details>
        <div class="qs"></div></div>`);
      const qs = secCard.querySelector(".qs");
      sec.questions.forEach(q => {
        const res = r.results.find(x => x.no === q.no) || {};
        qs.appendChild(el(`<div style="padding:10px 0;border-bottom:1px solid var(--line)">
          <div style="font-size:13.5px"><b>${res.correct ? '✅' : '❌'} Q${q.no}</b> ${escape(q.stem)}</div>
          <div style="font-size:13px;margin-top:6px">
            你的答案：<b style="color:${res.correct ? 'var(--green)' : 'var(--red,crimson)'}">${escape(res.user || '未作答')}</b>
            <span style="color:var(--muted)">｜</span>正确答案：<b>${escape(res.answer)}</b></div>
          ${res.explain ? `<div style="font-size:12.5px;color:var(--muted);margin-top:4px">💡 ${escape(res.explain)}</div>` : ''}</div>`));
      });
      container.appendChild(secCard);
    });
  }

  drawList();
}

// ================= Tab 2: 真题与错题 =================
async function renderTests(container, refresh) {
  const [cfg, tests, mistakes] = await Promise.all([
    api('/api/ielts/config'), api('/api/ielts/tests'), api('/api/ielts/mistakes'),
  ]);
  const grid = el('<div class="grid cols-2" style="align-items:start"></div>');
  const left = el('<div style="display:flex;flex-direction:column;gap:16px;min-width:0"></div>');
  const right = el('<div style="display:flex;flex-direction:column;gap:16px;min-width:0"></div>');
  grid.appendChild(left); grid.appendChild(right);
  container.appendChild(grid);

  // 真题趋势
  const tCard = el(`<div class="card"><div class="card-title">📈 真题成绩趋势 <span class="hint">目标 ${cfg.target_overall}</span></div></div>`);
  const t = tests.trend;
  if (t.dates.length) tCard.appendChild(trendSvg(t, cfg));
  else tCard.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">还没有真题记录</div></div>'));
  tCard.appendChild(el(`<div class="inline-form">
    <input placeholder="剑18" style="width:70px" class="t-book">
    <input placeholder="T2" style="width:55px" class="t-no">
    <input type="number" step="0.5" placeholder="听力分" style="width:75px" class="t-l">
    <input type="number" step="0.5" placeholder="阅读分" style="width:75px" class="t-r">
    <button class="btn t-add">记录</button></div>`));
  tCard.querySelector(".t-add").onclick = async () => {
    const book = tCard.querySelector(".t-book").value.trim();
    if (!book) return toast("请填题集", false);
    await api('/api/ielts/tests', { method: 'POST', body: { date: todayStr(), book,
      test_no: tCard.querySelector(".t-no").value.trim(),
      listening: +tCard.querySelector(".t-l").value || null,
      reading: +tCard.querySelector(".t-r").value || null } });
    toast("已记录"); refresh();
  };
  left.appendChild(tCard);

  // 错题本
  const mCard = el(`<div class="card"><div class="card-title">❌ 错题本 · 薄弱题型
    <span class="hint">刷题错题自动进这里</span></div></div>`);
  if (mistakes.stats.length) {
    const box = el('<div class="stat-row" style="margin-bottom:8px"></div>');
    mistakes.stats.slice(0, 5).forEach(s => box.appendChild(el(`
      <div class="stat" style="min-width:80px;padding:6px 12px"><b>${s.n}</b><span>${SUB_CN[s.subject] || s.subject}·${escape(s.qtype)}</span></div>`)));
    mCard.appendChild(box);
  }
  mCard.appendChild(el(`<div class="inline-form">
    <select class="m-sub"><option value="listening">听力</option><option value="reading">阅读</option></select>
    <input placeholder="题型（Heading/配对/填空）" style="width:150px" class="m-type">
    <input placeholder="错因一句话" style="flex:1" class="m-reason">
    <button class="btn m-add">记录</button></div>`));
  mCard.querySelector(".m-add").onclick = async () => {
    const qtype = mCard.querySelector(".m-type").value.trim();
    if (!qtype) return toast("请填题型", false);
    await api('/api/ielts/mistakes', { method: 'POST', body: { date: todayStr(),
      subject: mCard.querySelector(".m-sub").value, qtype,
      reason: mCard.querySelector(".m-reason").value.trim() } });
    toast("已记录"); refresh();
  };
  mistakes.items.slice(0, 10).forEach(m => mCard.appendChild(el(`
    <div style="display:flex;align-items:center;gap:6px;padding:5px 0;border-bottom:1px solid var(--line);font-size:12.5px">
      <span class="badge gray">${SUB_CN[m.subject]}</span> <b>${escape(m.qtype)}</b>
      <span style="flex:1;min-width:0;color:var(--muted)">${escape(m.reason || "")}${m.ref ? ' · ' + escape(m.ref) : ''}</span>
      <button class="btn m-del" style="padding:1px 7px;font-size:12px" title="删除错题记录">✕</button></div>`)));
  mCard.querySelectorAll(".m-del").forEach((b, i) => b.onclick = async () => {
    const m = mistakes.items[i];
    if (!(await confirmBox(`删除这条错题记录（${m.qtype}）？`))) return;
    await api(`/api/ielts/mistakes/${m.id}`, { method: 'DELETE' });
    toast("已删除"); refresh();
  });
  right.appendChild(mCard);   // v1.14 排版修复：错题本进右列（原先两卡全挤左列）
}

// ================= Tab 3: 口语（v1.15：今日话题+常考库+我的版本+计时练习） =================
async function renderSpeaking(container, refresh) {
  const [daily, bank, allTopics] = await Promise.all([
    api('/api/ielts/speak/daily'),
    api('/api/ielts/speak/bank'),
    api('/api/ielts/topics'),
  ]);
  const byId = new Map(allTopics.items.map(t => [t.id, t]));

  const timerBar = (seedId) => `<div class="sp-timer" data-seed="${seedId}" style="display:flex;gap:8px;align-items:center;margin-top:8px">
    <button class="btn t-start" style="padding:3px 12px;font-size:12px">⏱ 计时练习（1分准备+2分作答）</button>
    <b class="t-display" style="font-size:15px;min-width:64px;color:var(--muted)">--:--</b>
    <span class="t-phase" style="font-size:12px;color:var(--muted)"></span></div>`;

  const mountTimer = (wrap) => {
    const bar = wrap.querySelector('.sp-timer');
    if (!bar) return;
    const disp = bar.querySelector('.t-display');
    const phase = bar.querySelector('.t-phase');
    let left = 0, ph = '', timer = null;
    bar.querySelector('.t-start').onclick = () => {
      clearInterval(timer);
      left = 60; ph = '📝 准备';
      timer = setInterval(() => {
        left -= 1;
        if (left <= 0 && ph.includes('准备')) { left = 120; ph = '🎤 作答'; }
        else if (left <= 0) {
          clearInterval(timer); disp.textContent = '✓ 完成';
          phase.textContent = '说得如何？把想法写进「我的版本」吧';
          return;
        }
        disp.textContent = `${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}`;
        disp.style.color = ph.includes('作答') ? 'var(--red,crimson)' : 'var(--muted)';
        phase.textContent = ph;
      }, 1000);
      disp.textContent = '01:00';
    };
  };

  // 录音组件（v1.16：MediaRecorder 本机存储 + 回放 + 删除）
  const recorderBlock = (item) => {
    const key = item.seed_id || `user-${item.row_id}`;
    const wrap = el(`<div class="sp-rec" data-key="${escape(key)}" style="margin-top:10px;padding-top:8px;border-top:1px dashed var(--line)">
      <div class="inline-form" style="flex-wrap:wrap">
        <button class="btn r-toggle" style="padding:3px 14px;font-size:12px">🎤 开始录音</button>
        <span class="r-hint" style="font-size:12px;color:var(--muted)">录音只存本机，练完听回放对照范文自查</span></div>
      <div class="r-list" style="margin-top:6px"></div></div>`);
    const btn = wrap.querySelector('.r-toggle');
    const hint = wrap.querySelector('.r-hint');
    const list = wrap.querySelector('.r-list');
    let media = null, chunks = [], streaming = false;

    const loadList = async () => {
      try {
        const r = await api(`/api/ielts/speak/recording/${encodeURIComponent(key)}`);
        list.innerHTML = '';
        if (!r.items.length) { list.innerHTML = ''; return; }
        r.items.forEach(rec => {
          const row = el(`<div style="display:flex;gap:8px;align-items:center;padding:4px 0;font-size:12.5px">
            <audio controls preload="none" src="/api/ielts/speak/recording/${encodeURIComponent(key)}/${encodeURIComponent(rec.name)}" style="height:30px"></audio>
            <span style="color:var(--muted)">${escape(rec.ts)}</span>
            <span style="color:var(--muted)">${Math.round(rec.size / 1024)}KB</span>
            <button class="btn r-del" style="padding:1px 8px;font-size:11px">✕</button></div>`);
          row.querySelector('.r-del').onclick = async () => {
            try { await api(`/api/ielts/speak/recording/${encodeURIComponent(key)}/${encodeURIComponent(rec.name)}`, { method: 'DELETE' }); loadList(); }
            catch (e) { toast(e.message, false); }
          };
          list.appendChild(row);
        });
      } catch (e) { /* 静默 */ }
    };
    loadList();

    btn.onclick = async () => {
      if (!streaming) {
        if (!navigator.mediaDevices || !window.MediaRecorder)
          return toast('此浏览器不支持录音', false);
        try {
          media = new MediaRecorder(await navigator.mediaDevices.getUserMedia({ audio: true }));
        } catch (e) { return toast('麦克风权限被拒绝——请在浏览器地址栏允许麦克风后重试', false); }
        chunks = [];
        media.ondataavailable = (ev) => chunks.push(ev.data);
        media.onstop = async () => {
          const blob = new Blob(chunks, { type: media.mimeType || 'audio/webm' });
          try {
            const r = await fetch(`/api/ielts/speak/recording/${encodeURIComponent(key)}`, {
              method: 'POST', headers: { 'Content-Type': media.mimeType || 'audio/webm' },
              body: blob });
            if (!r.ok) throw new Error((await r.json()).error || '保存失败');
            hint.textContent = '✓ 已保存，可在下方回放';
            loadList();
          } catch (e) { hint.textContent = ''; toast('录音保存失败：' + e.message, false); }
        };
        media.start();
        streaming = true;
        btn.textContent = '⏹ 停止并保存';
        let sec = 0;
        hint.textContent = '● 录音中 0s';
        wrap._tick = setInterval(() => { sec += 1; hint.textContent = `● 录音中 ${sec}s`; }, 1000);
      } else {
        clearInterval(wrap._tick);
        media.stop(); streaming = false;
        btn.textContent = '🎤 开始录音';
        hint.textContent = '保存中…';
      }
    };
    return wrap;
  };

  const detailBlock = (item) => {
    // cue card（Part2）或问答（Part1/3）+ 范文 + 我的版本
    const box = el('<div style="margin-top:8px"></div>');
    if (item.cue) {
      box.appendChild(el(`<div style="font-size:13px;margin-bottom:6px"><b>Cue card：</b>You should say:
        <ul style="margin:4px 0 0 18px">${item.cue.map(c => `<li>${escape(c)}</li>`).join('')}</ul></div>`));
    }
    if (item.qa) {
      const ql = el('<div style="font-size:13px;margin-bottom:6px"><b>常见问题：</b></div>');
      item.qa.forEach(q => ql.appendChild(el(
        `<div style="padding:3px 0">• ${escape(q.q)}</div>`)));
      box.appendChild(ql);
    }
    if (item.vocab) {
      box.appendChild(el(`<div style="font-size:12.5px;color:var(--muted);margin:6px 0">
        💡 ${item.vocab.map(v => escape(v)).join(' · ')}</div>`));
    }
    const det = el(`<details style="margin-top:4px"><summary style="cursor:pointer;font-size:12.5px;color:var(--accent)">
      📄 展开范文${item.note ? '（已写「我的版本」）' : ''}</summary>
      <pre style="white-space:pre-wrap;font-size:13px;background:var(--card-2);padding:10px;border-radius:8px;margin-top:6px">${escape(item.sample || '')}</pre></details>`);
    box.appendChild(det);
    const edit = el(`<div style="margin-top:8px">
      <textarea rows="4" style="width:100%" placeholder="我的版本：从范文改起，或完全写自己的想法（保存后只存本机）…">${escape(item.note || '')}</textarea>
      <div class="inline-form" style="margin-top:6px">
        <button class="btn btn-primary n-save" style="padding:3px 14px;font-size:12px">保存我的版本</button>
        ${item.sample ? '<button class="btn n-from-sample" style="padding:3px 14px;font-size:12px">以范文为底稿</button>' : ''}
        ${item.note ? '<button class="btn n-clear" style="padding:3px 14px;font-size:12px">清空</button>' : ''}
        <span class="n-saved" style="font-size:12px;color:var(--green)"></span></div></div>`);
    edit.querySelector('.n-save').onclick = async () => {
      if (!item.seed_id) return toast('自建话题暂不支持范文（可直接写在备注里）', false);
      try {
        await api('/api/ielts/speak/note', { method: 'POST',
          body: { seed_id: item.seed_id, text: edit.querySelector('textarea').value } });
        edit.querySelector('.n-saved').textContent = '✓ 已保存';
        setTimeout(() => { const s = edit.querySelector('.n-saved'); if (s) s.textContent = ''; }, 2000);
      } catch (e) { toast(e.message, false); }
    };
    const fs = edit.querySelector('.n-from-sample');
    if (fs) fs.onclick = () => { edit.querySelector('textarea').value = item.sample || ''; };
    const clr = edit.querySelector('.n-clear');
    if (clr) clr.onclick = async () => {
      try {
        await api('/api/ielts/speak/note', { method: 'POST', body: { seed_id: item.seed_id, text: '' } });
        edit.querySelector('textarea').value = ''; toast('已清空'); refresh();
      } catch (e) { toast(e.message, false); }
    };
    box.appendChild(edit);
    box.appendChild(recorderBlock(item));
    return box;
  };

  // ---- 今日话题卡 ----
  const dCard = el(`<div class="card" style="margin-bottom:16px;border-color:var(--accent)">
    <div class="card-title">📅 今日话题 <span class="hint">${daily.day} · 每天自动换一个（Part 2 常考池轮换）</span></div>
    <div style="font-size:15px;font-weight:600;margin-bottom:4px">${escape(daily.topic)}</div>
    <div class="d-body"></div></div>`);
  const dBody = dCard.querySelector('.d-body');
  dBody.appendChild(detailBlock(daily));
  dBody.insertAdjacentHTML('afterbegin', timerBar(daily.seed_id));
  mountTimer(dBody);
  container.appendChild(dCard);

  // ---- Part 1/2/3 常考话题库 ----
  const libCard = el(`<div class="card" style="margin-bottom:16px">
    <div class="card-title">🗂 常考话题库 <span class="hint">点开练：范文参考 + 写我的版本 + 计时</span></div>
    <div class="inline-form">
      <button class="btn p-btn" data-p="2">Part 2（卡片描述）</button>
      <button class="btn p-btn" data-p="1">Part 1（简答）</button>
      <button class="btn p-btn" data-p="3">Part 3（深入讨论）</button>
      <span style="flex:1"></span></div>
    <div class="p-list" style="max-height:520px;overflow:auto"></div></div>`);
  container.appendChild(libCard);
  const pList = libCard.querySelector('.p-list');
  let curPart = 2;
  const drawParts = () => {
    libCard.querySelectorAll('.p-btn').forEach(b =>
      b.style.cssText = +b.dataset.p === curPart
        ? 'border-color:var(--accent);color:var(--accent-text);font-weight:600' : '');
    pList.innerHTML = '';
    bank.items.filter(i => i.part === curPart).forEach(item => {
      const row = el(`<div style="border-bottom:1px solid var(--line);padding:8px 0">
        <div style="display:flex;gap:8px;align-items:center">
          <button class="tick ${item.practiced ? 'on' : ''}">✓</button>
          <span style="flex:1;min-width:0;font-size:13.5px;cursor:pointer" class="t-name">
            ${escape(item.topic)}</span>
          ${item.freq ? '<span class="badge amber">高频</span>' : ''}
          ${item.note ? '<span class="badge green">有我的版本</span>' : ''}</div>
        <div class="d" style="display:none"></div></div>`);
      row.querySelector('.tick').onclick = async () => {
        if (!item.row_id) { await api('/api/ielts/topics', { method: 'POST', body: { part: item.part, topic: item.topic, freq: 0 } }); }
        else { await api(`/api/ielts/topics/${item.row_id}/toggle`, { method: 'POST' }); }
        refresh();
      };
      if (item.row_id) {   // v1.19：自建话题可删（内置话题池不显示）
        const tdel = el('<button class="btn t-del" style="padding:1px 7px;font-size:12px" title="删除自建话题">✕</button>');
        tdel.onclick = async () => {
          if (!(await confirmBox(`删除自建话题「${item.topic}」？
其练习记录与我的版本将一并删除。`))) return;
          try { await api(`/api/ielts/topics/${item.row_id}`, { method: 'DELETE' }); toast('已删除'); refresh(); }
          catch (e) { toast(e.message, false); }
        };
        row.querySelector('div[style]').appendChild(tdel);
      }
      const toggle = () => {
        const d = row.querySelector('.d');
        if (d.style.display === 'none') {
          d.appendChild(detailBlock(item));
          d.insertAdjacentHTML('afterbegin', item.cue ? timerBar(item.seed_id) : '');
          mountTimer(d);
          d.style.display = '';
        } else { d.style.display = 'none'; d.innerHTML = ''; }
      };
      row.querySelector('.t-name').onclick = toggle;
      pList.appendChild(row);
    });
  };
  libCard.querySelectorAll('.p-btn').forEach(b => b.onclick = () => {
    curPart = +b.dataset.p; drawParts();
  });
  drawParts();

  // ---- 自建话题（保留原功能） ----
  const addCard = el(`<div class="card"><div class="card-title">➕ 我遇到的话题 <span class="hint">考场上遇到的题，记下来专门练</span></div>
    <div class="inline-form"><select class="a-part"><option value="1">Part1</option><option value="2" selected>Part2</option><option value="3">Part3</option></select>
    <input placeholder="话题（如 Describe a person who inspired you）" style="flex:1" class="a-topic">
    <label style="font-size:12px"><input type="checkbox" class="a-freq"> 高频</label>
    <button class="btn a-add">添加</button></div></div>`);
  addCard.querySelector('.a-add').onclick = async () => {
    const topic = addCard.querySelector('.a-topic').value.trim();
    if (!topic) return;
    try {
      await api('/api/ielts/topics', { method: 'POST', body: {
        part: +addCard.querySelector('.a-part').value, topic,
        freq: addCard.querySelector('.a-freq').checked ? 1 : 0 } });
      toast('已添加'); refresh();
    } catch (e) { toast(e.message, false); }
  };
  container.appendChild(addCard);
}

// ================= Tab 4: 写作（v1.16 重做：每日任务+题库+范文+我的作文+计时） =================
async function renderWriting(container, refresh) {
  const [daily, bank, writings] = await Promise.all([
    api('/api/ielts/write/daily'),
    api('/api/ielts/write/bank'),
    api('/api/ielts/writings'),
  ]);
  const wordCount = (s) => (s || "").trim() ? s.trim().split(/\s+/).length : 0;

  const writeEditor = (item) => {
    const minWords = item.task === 2 ? 250 : 150;
    const mins = item.task === 2 ? 40 : 20;
    const box = el(`<div style="margin-top:8px">
      ${item.structure ? `<div style="font-size:12.5px;color:var(--muted);margin-bottom:6px">📐 结构要点：${escape(item.structure.join(' → '))}</div>` : ''}
      ${item.vocab ? `<div style="font-size:12.5px;color:var(--muted);margin-bottom:6px">💡 ${item.vocab.map(v => escape(v)).join(' · ')}</div>` : ''}
      <details ${item.note ? '' : 'open'} style="margin-bottom:8px"><summary style="cursor:pointer;font-size:12.5px;color:var(--accent)">📄 展开范文${item.note ? '（已写我的作文）' : ''}</summary>
        <pre style="white-space:pre-wrap;font-size:13px;background:var(--card-2);padding:10px;border-radius:8px;margin-top:6px">${escape(item.sample || '')}</pre></details>
      <textarea rows="8" class="we-text" style="width:100%" placeholder="我的作文（保存只存本机）…">${escape(item.note || '')}</textarea>
      <div class="inline-form" style="margin-top:6px;flex-wrap:wrap">
        <span class="wc" style="font-size:12.5px;color:var(--muted);min-width:110px">0 词（目标 ≥${minWords}）</span>
        <span class="wt" style="font-size:14px;min-width:60px;color:var(--muted)">--:--</span>
        <button class="btn wt-start" style="padding:3px 12px;font-size:12px">⏱ 计时 ${mins} 分钟</button>
        <button class="btn btn-primary we-save" style="padding:3px 14px;font-size:12px">保存我的作文</button>
        <button class="btn we-from-sample" style="padding:3px 14px;font-size:12px">以范文为底稿</button>
        ${item.note ? '<button class="btn we-clear" style="padding:3px 14px;font-size:12px">清空</button>' : ''}
        <span class="we-saved" style="font-size:12px;color:var(--green)"></span></div></div>`);
    const ta = box.querySelector('.we-text');
    const wc = box.querySelector('.wc');
    const wt = box.querySelector('.wt');
    const updWc = () => {
      const n = wordCount(ta.value);
      wc.textContent = `${n} 词（目标 ≥${minWords}）`;
      wc.style.color = n >= minWords ? 'var(--green)' : 'var(--muted)';
    };
    ta.oninput = updWc; updWc();
    box.querySelector('.we-save').onclick = async () => {
      try {
        await api('/api/ielts/write/note', { method: 'POST', body: { seed_id: item.id, text: ta.value } });
        box.querySelector('.we-saved').textContent = '✓ 已保存';
        setTimeout(() => { const s = box.querySelector('.we-saved'); if (s) s.textContent = ''; }, 2000);
      } catch (e) { toast(e.message, false); }
    };
    box.querySelector('.we-from-sample').onclick = () => { ta.value = item.sample || ''; updWc(); };
    const clr = box.querySelector('.we-clear');
    if (clr) clr.onclick = async () => {
      try { await api('/api/ielts/write/note', { method: 'POST', body: { seed_id: item.id, text: '' } });
        ta.value = ''; updWc(); toast('已清空'); refresh(); }
      catch (e) { toast(e.message, false); }
    };
    let left = mins * 60, timer = null;
    box.querySelector('.wt-start').onclick = () => {
      clearInterval(timer);
      left = mins * 60;
      timer = setInterval(() => {
        left -= 1;
        wt.textContent = `${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}`;
        wt.style.color = left <= 300 ? 'var(--red,crimson)' : 'var(--accent)';
        if (left <= 0) { clearInterval(timer); wt.textContent = '⏰ 时间到'; }
      }, 1000);
      wt.textContent = `${mins}:00`;
    };
    return box;
  };

  const dCard = el(`<div class="card" style="margin-bottom:16px;border-color:var(--accent)">
    <div class="card-title">📅 今日写作任务 <span class="hint">${daily.day} · Task 1/Task 2 池每日轮换</span></div>
    <div style="font-size:13.5px;font-weight:600;margin-bottom:2px">Task 2（≥250 词 · 40 分钟）</div>
    <div style="font-size:13px;color:var(--muted);margin-bottom:4px">${escape(daily.t2.prompt)}</div>
    <div class="d-t2"></div>
    <hr style="border:none;border-top:1px solid var(--line);margin:10px 0">
    <div style="font-size:13.5px;font-weight:600;margin-bottom:2px">Task 1（≥150 词 · 20 分钟）</div>
    <div style="font-size:13px;color:var(--muted);margin-bottom:4px">${escape(daily.t1.prompt)}</div>
    <div class="d-t1"></div></div>`);
  dCard.querySelector('.d-t2').appendChild(writeEditor(daily.t2));
  dCard.querySelector('.d-t1').appendChild(writeEditor(daily.t1));
  container.appendChild(dCard);

  const bCard = el(`<div class="card" style="margin-bottom:16px">
    <div class="card-title">🗂 写作题库 <span class="hint">点开：结构要点+范文+我的作文+计时</span></div>
    <div class="inline-form">
      <button class="btn tb-btn" data-t="2">Task 2（议论文）</button>
      <button class="btn tb-btn" data-t="1">Task 1（图表描述）</button>
      <span style="flex:1"></span></div>
    <div class="tb-list" style="max-height:520px;overflow:auto"></div></div>`);
  container.appendChild(bCard);
  const bList = bCard.querySelector('.tb-list');
  let curTask = 2;
  const drawBank = () => {
    bCard.querySelectorAll('.tb-btn').forEach(b =>
      b.style.cssText = +b.dataset.t === curTask
        ? 'border-color:var(--accent);color:var(--accent-text);font-weight:600' : '');
    bList.innerHTML = '';
    bank.items.filter(i => i.task === curTask).forEach(item => {
      const row = el(`<div style="border-bottom:1px solid var(--line);padding:8px 0">
        <div style="display:flex;gap:8px;align-items:center">
          <span style="flex:1;min-width:0;font-size:13.5px;cursor:pointer" class="t-name">${escape(item.title)}</span>
          ${item.note ? '<span class="badge green">已写作文</span>' : ''}</div>
        <div style="font-size:12.5px;color:var(--muted);margin-top:2px">${escape(item.prompt.slice(0, 90))}…</div>
        <div class="d" style="display:none"></div></div>`);
      row.querySelector('.t-name').onclick = () => {
        const d = row.querySelector('.d');
        if (d.style.display === 'none') {
          d.appendChild(el(`<div style="font-size:13px;margin-bottom:4px">${escape(item.prompt)}</div>`));
          d.appendChild(writeEditor(item));
          d.style.display = '';
        } else { d.style.display = 'none'; d.innerHTML = ''; }
      };
      bList.appendChild(row);
    });
  };
  bCard.querySelectorAll('.tb-btn').forEach(b => b.onclick = () => { curTask = +b.dataset.t; drawBank(); });
  drawBank();

  const mCard = el(`<div class="card"><div class="card-title">💭 思路速记 <span class="hint">好句子/论点随手存</span></div>
    <div class="inline-form"><input placeholder="话题（如 科技与教育）" style="width:150px" class="w-topic">
    <input placeholder="思路/素材片段" style="flex:1" class="w-content">
    <button class="btn w-add">保存</button></div><div class="w-list"></div></div>`);
  mCard.querySelector(".w-add").onclick = async () => {
    const topic = mCard.querySelector(".w-topic").value.trim();
    if (!topic) return;
    await api('/api/ielts/writings', { method: 'POST', body: { date: todayStr(),
      topic, content: mCard.querySelector(".w-content").value.trim() } });
    refresh();
  };
  const wl = mCard.querySelector(".w-list");
  writings.items.slice(0, 12).forEach(w => wl.appendChild(el(`
    <div style="padding:5px 0;border-bottom:1px solid var(--line);font-size:12.5px">
      <b>${escape(w.topic)}</b> <span style="color:var(--muted)">${escape((w.content || "").slice(0, 90))}</span></div>`)));
  if (!writings.items.length) wl.appendChild(el('<div class="empty" style="padding:8px"><div style="font-size:13px">好思路随手存</div></div>'));
  container.appendChild(mCard);
}

// ================= Tab 5: 模考与设置 =================
async function renderMock(container, refresh) {
  const [cfg, mocks] = await Promise.all([api('/api/ielts/config'), api('/api/ielts/mocks')]);
  const setCard = el(`<div class="card" style="margin-bottom:16px"><div class="card-title">⚙️ 考试设置（随时可改）
    <span class="hint">${cfg.days_left != null ? `⏳ 距考试 ${cfg.days_left} 天` : "考试日期未定"}</span></div>
    <div class="inline-form" style="margin:0">
      <label style="font-size:13px">考试日 <input type="date" class="c-exam" value="${cfg.exam_date || ""}" style="width:145px"></label>
      <label style="font-size:13px">目标总分 <input type="number" step="0.5" min="4" max="9" class="c-target" value="${cfg.target_overall}" style="width:70px"></label>
      <button class="btn btn-primary c-save">保存</button>
      <span style="color:var(--muted);font-size:12px">目标小分默认 听7.0/读7.5/写6.5/说6.5（听读优先拉分）</span>
    </div></div>`);
  setCard.querySelector(".c-save").onclick = async () => {
    await api('/api/ielts/config', { method: 'PUT', body: {
      exam_date: setCard.querySelector(".c-exam").value || null,
      target_overall: +setCard.querySelector(".c-target").value || 7,
    } });
    toast("已保存，倒计时立即生效"); refresh();
  };
  container.appendChild(setCard);

  const kCard = el(`<div class="card"><div class="card-title">🗓 模考日程 <span class="hint">临近自动进工作台建议</span></div>
    <div class="inline-form"><input type="date" class="k-date" style="width:145px">
    <select class="k-kind">${Object.entries(KIND_CN).map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select>
    <button class="btn k-add">安排</button></div><div class="k-list"></div></div>`);
  kCard.querySelector(".k-add").onclick = async () => {
    const d = kCard.querySelector(".k-date").value;
    if (!d) return;
    await api('/api/ielts/mocks', { method: 'POST', body: { date: d, kind: kCard.querySelector(".k-kind").value } });
    refresh();
  };
  const kl = kCard.querySelector(".k-list");
  mocks.items.forEach(m => kl.appendChild(el(`
    <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--line);font-size:13px">
      <span class="badge">${m.date}</span> ${KIND_CN[m.kind] || m.kind}
      <button class="btn k-del" style="margin-left:auto;padding:2px 8px;font-size:12px">✕</button></div>`)));
  if (!mocks.items.length) kl.appendChild(el('<div class="empty" style="padding:8px"><div style="font-size:13px">暂无模考安排</div></div>'));
  kl.querySelectorAll(".k-del").forEach((b, i) => b.onclick = async () => {
    await api(`/api/ielts/mocks/${mocks.items[i].id}`, { method: 'DELETE' }); refresh();
  });
  container.appendChild(kCard);
}

// ================= 听力音频双通道（v1.9 F26） =================
// 通道一：本机 data/ielts_audio/{题组id}-{节号}.mp3（或 {题组id}.mp3），后端直出；
// 通道二：无本机音频时用 speechSynthesis 机器朗读原文，按句排队、可暂停/停止/调语速。
let ttsActive = null;

function stopTts() {
  if (ttsActive) { ttsActive.stop(); ttsActive = null; }
}
// 切页/切 Tab 即停读，防止翻页后还在念
window.addEventListener("hashchange", stopTts);

function splitSentences(material) {
  const out = [];
  String(material).split(/\n+/).forEach(line => {
    (line.match(/[^.!?…]+[.!?…]+|[^.!?…]+$/g) || []).forEach(s => {
      s = s.trim();
      if (s) out.push(s);
    });
  });
  return out;
}

function attachPlayer(wrap, material) {
  // ---- 通道一：本机音频探测（隐藏 <audio>，能加载才显示） ----
  const audio = wrap.querySelector("audio");
  const msg = wrap.querySelector(".aud-msg");
  if (audio) {
    audio.addEventListener("loadedmetadata", () => { audio.style.display = "block"; });
    audio.addEventListener("error", () => { msg.textContent = "无本机音频 → 用机器朗读 ↓"; });
  }

  // ---- 通道二：TTS 按句队列 ----
  const sents = splitSentences(material);
  let i = 0, gen = 0;   // gen 代际计数：stop/重播后旧回调全部作废
  const pauseBtn = wrap.querySelector(".tts-pause");
  const setMsg = (t) => { msg.textContent = t; };

  const pickVoice = () => {
    const vs = speechSynthesis.getVoices();
    return vs.find(v => /^en-GB/i.test(v.lang)) || vs.find(v => /^en/i.test(v.lang)) || null;
  };
  const speakNext = (g) => {
    if (g !== gen) return;
    if (i >= sents.length) { setMsg(`朗读完成（共 ${sents.length} 句）`); ttsActive = null; return; }
    setMsg(`机器朗读 ${i + 1}/${sents.length} 句`);
    const u = new SpeechSynthesisUtterance(sents[i]);
    u.lang = "en-GB";
    u.rate = parseFloat(wrap.querySelector(".tts-rate").value);
    const v = pickVoice();
    if (v) u.voice = v;
    u.onend = () => { if (g !== gen) return; i += 1; speakNext(g); };
    u.onerror = () => { if (g !== gen) return; setMsg("此浏览器不支持语音朗读，请展开原文阅读"); };
    speechSynthesis.speak(u);
  };

  wrap.querySelector(".tts-play").onclick = () => {
    if (!("speechSynthesis" in window)) return setMsg("此浏览器不支持语音朗读");
    stopTts();
    ttsActive = { stop: () => { gen += 1; speechSynthesis.cancel(); i = 0; pauseBtn.textContent = "⏸ 暂停"; setMsg(""); } };
    i = 0;
    speechSynthesis.cancel();
    setTimeout(() => speakNext(gen), 150);   // cancel 后立即 speak 偶发被吞，稍候
  };
  pauseBtn.onclick = () => {
    if (!ttsActive) return;
    if (speechSynthesis.paused) {
      speechSynthesis.resume(); pauseBtn.textContent = "⏸ 暂停";
    } else if (speechSynthesis.speaking) {
      speechSynthesis.pause(); pauseBtn.textContent = "▶ 继续";
    }
  };
  wrap.querySelector(".tts-stop").onclick = () => stopTts();
  wrap.querySelector(".tts-rate").onchange = () => {
    if (ttsActive && speechSynthesis.speaking) {   // 换语速：当前句重读
      speechSynthesis.cancel();
      setTimeout(() => speakNext(gen), 150);
    }
  };
}

/** 纯 SVG 分数趋势（听/读两条线 + 目标参考线） */
function trendSvg(t, cfg) {
  const W = 480, H = 170, L = 34, R = 8, T = 12, B = 22;
  const n = t.dates.length;
  const xs = (i) => L + (n === 1 ? (W - L - R) / 2 : i * (W - L - R) / (n - 1));
  const ys = (v) => T + (9 - (v ?? 5)) / 5 * (H - T - B);
  const line = (key) => t[key].map((v, i) => v == null ? null : `${i ? "L" : "M"}${xs(i)},${ys(v)}`).join(" ");
  const dots = (key, color) => t[key].map((v, i) => v == null ? "" :
    `<circle cx="${xs(i)}" cy="${ys(v)}" r="3.2" fill="${color}"/>`).join("");
  const y = cfg.target_overall;
  return el(`<svg viewBox="0 0 ${W} ${H}" style="width:100%">
    ${[5, 6, 7, 8, 9].map(v => `<line x1="${L}" y1="${ys(v)}" x2="${W - R}" y2="${ys(v)}" stroke="var(--line)" stroke-width="0.5"/>
      <text x="4" y="${ys(v) + 3}" font-size="9" fill="var(--muted)">${v}</text>`).join("")}
    <line x1="${L}" y1="${ys(y)}" x2="${W - R}" y2="${ys(y)}" stroke="var(--amber)" stroke-dasharray="4 3" stroke-width="1"/>
    <path d="${line("listening")}" fill="none" stroke="var(--accent)" stroke-width="1.8"/>${dots("listening", "var(--accent)")}
    <path d="${line("reading")}" fill="none" stroke="var(--green)" stroke-width="1.8"/>${dots("reading", "var(--green)")}
    ${t.dates.map((d, i) => `<text x="${xs(i)}" y="${H - 6}" font-size="9" fill="var(--muted)" text-anchor="middle">${d.length > 8 ? d.slice(0, 8) : d}</text>`).join("")}
    <text x="${W - R}" y="10" font-size="10" fill="var(--accent)" text-anchor="end">— 听力</text>
    <text x="${W - R - 55}" y="10" font-size="10" fill="var(--green)" text-anchor="end">— 阅读</text>
  </svg>`);
}
