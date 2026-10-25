// 设置：AI 档案编辑（多平台）+ 知识库路径 + 外观说明
import { api } from '../api.js';
import { el, escape, toast, confirmBox } from './kit.js';

export default {
  id: 'settings',
  title: '设置',
  icon: '⚙️',
  async render(container, rerender) {
    const refresh = () => rerender ? rerender() : location.reload();
    const cfg = await api('/api/config');

    container.appendChild(el(`
      <div class="page-head"><h1>设置</h1><p>AI 多平台接入 · 知识库路径 · 配置仅存本机 data/config.json</p></div>`));

    // ---- AI 档案 ----
    const aiCard = el(`<div class="card" style="margin-bottom:16px"><div class="card-title">🤖 AI 模型接入
      <span class="hint">OpenAI 兼容：DeepSeek / 通义 Qwen / 各中转站</span></div>
      <p style="color:var(--muted);font-size:12.5px;margin:0 0 10px">
        当前：<b>${cfg.ai.active ? escape(cfg.ai.active) : '未启用（本地规则模式）'}</b>。
        填入密钥并选择档案后，每日建议/问答自动升级为 AI 生成，可随时清除回落。</p>
      <div class="prov-list"></div>
      <div class="inline-form">
        <button class="btn" id="add-prov">＋ 添加档案</button>
        <span style="color:var(--muted);font-size:12px">保存后即时生效，无需重启</span>
      </div></div>`);

    const list = aiCard.querySelector('.prov-list');
    const renderList = (providers, active) => {
      list.innerHTML = '';
      if (!providers.length) {
        list.appendChild(el('<div class="empty" style="padding:10px"><div style="font-size:13px">暂无档案</div></div>'));
        return;
      }
      providers.forEach((p, i) => {
        const row = el(`<div class="card" style="background:var(--card-2);margin-bottom:10px">
          <div class="inline-form" style="margin:0">
            <b style="min-width:60px">${escape(p.name)}</b>
            <span class="badge ${active === p.name ? 'green' : 'gray'}">${active === p.name ? '使用中' : '未启用'}</span>
            ${p.has_key ? '<span class="badge green">密钥已存</span>' : '<span class="badge amber">缺密钥</span>'}
            <span style="flex:1"></span>
            ${active !== p.name ? `<button class="btn use" style="padding:3px 10px;font-size:12px">设为当前</button>` : '<button class="btn off" style="padding:3px 10px;font-size:12px">停用</button>'}
            <button class="btn prov-del" title="删除该档案（密钥一并清除）" style="padding:3px 9px;font-size:12px">🗑</button>
          </div>
          <div class="inline-form" style="margin:6px 0 0;flex-wrap:wrap">
            <input class="base_url" placeholder="base_url 如 https://api.deepseek.com/v1" style="flex:1;min-width:220px" value="${escape(p.base_url || '')}">
            <select class="model-sel" style="width:175px">${p.model ? `<option>${escape(p.model)}</option>` : '<option value="">（先拉取模型）</option>'}</select>
            <input class="model-txt" placeholder="模型名（手填）" style="width:150px;display:none">
            <button class="btn m-fetch" title="从该服务拉取可用模型列表">⇩ 拉取模型</button>
            <button class="btn m-edit" title="切换为手动输入模型名">✎</button>
            <input class="key" type="password" placeholder="${p.has_key ? '密钥已保存（重填可覆盖）' : 'API Key'}" style="width:160px">
            <button class="btn m-test">🔌 测试</button>
          </div>
          <div class="m-msg" style="font-size:12px;color:var(--muted);margin-top:4px;min-height:16px"></div></div>`);
        const sel = row.querySelector('.model-sel');
        const txt = row.querySelector('.model-txt');
        const msg = row.querySelector('.m-msg');
        const modelValue = () => (sel.style.display === 'none' ? txt.value : sel.value).trim();
        const formArgs = () => ({ base_url: row.querySelector('.base_url').value.trim(),
          provider_name: p.name, api_key: row.querySelector('.key').value.trim() || undefined });
        // 保存该行
        const save = async () => {
          try {
            const body = { base_url: row.querySelector('.base_url').value.trim(), model: modelValue() };
            const key = row.querySelector('.key').value.trim();
            if (key) body.api_key = key;
            await api('/api/config', { method: 'PUT', body: { ai: { providers: [{ name: p.name, ...body }] } } });
            toast(`档案 ${p.name} 已保存`);
          } catch (e) { toast(e.message, false); }
        };
        row.querySelector('.base_url').onchange = save;
        sel.onchange = save;
        txt.onchange = save;
        row.querySelector('.key').onchange = save;
        // 拉取模型列表（v1.10：不手填，从服务拉）
        row.querySelector('.m-fetch').onclick = async () => {
          msg.textContent = '拉取模型列表…';
          try {
            const r = await api('/api/ai/models', { method: 'POST', body: formArgs() });
            sel.innerHTML = r.models.map(m => `<option>${escape(m)}</option>`).join('') || '<option value="">（该服务未返回模型）</option>';
            if (p.model && r.models.includes(p.model)) sel.value = p.model;
            msg.textContent = `✅ 拉到 ${r.models.length} 个模型，选择后自动保存`;
            save();
          } catch (e) { msg.textContent = ''; toast(e.message, false); }
        };
        // 手填切换（兜底：服务不支持 /models 时）
        row.querySelector('.m-edit').onclick = () => {
          const manual = sel.style.display === 'none';
          sel.style.display = manual ? '' : 'none';
          txt.style.display = manual ? 'none' : '';
          if (!manual) txt.value = sel.value;
        };
        // 连通测试：一次验证 地址+密钥+模型
        row.querySelector('.m-test').onclick = async () => {
          const model = modelValue();
          if (!model) return toast('请先拉取并选择模型', false);
          msg.textContent = '测试中（发一条 1-token 消息）…';
          try {
            const r = await api('/api/ai/test', { method: 'POST', body: { ...formArgs(), model } });
            msg.textContent = `✅ 连通正常 · ${r.latency_ms}ms`;
            msg.style.color = 'var(--green)';
          } catch (e) {
            msg.textContent = `❌ ${e.message}`;
            msg.style.color = 'var(--red,crimson)';
            return;
          }
          msg.style.color = 'var(--green)';
          save();
        };
        const useBtn = row.querySelector('.use');
        if (useBtn) useBtn.onclick = async () => {
          if (!p.has_key) return toast('请先填入密钥并保存', false);
          try { await api('/api/config', { method: 'PUT', body: { ai: { active: p.name } } }); toast(`已切换到 ${p.name}`); refresh(); }
          catch (e) { toast(e.message, false); }
        };
        const offBtn = row.querySelector('.off');
        if (offBtn) offBtn.onclick = async () => {
          try { await api('/api/config', { method: 'PUT', body: { ai: { active: null } } }); toast('已停用，回落本地规则'); refresh(); }
          catch (e) { toast(e.message, false); }
        };
        // v1.13：删除档案（确认后连同密钥物理清除）
        row.querySelector('.prov-del').onclick = async () => {
          const using = active === p.name ? '该档案正在使用中，删除后将回落本地规则；' : '';
          if (!(await confirmBox(`${using}删除档案「${p.name}」？已存的密钥将一并清除。`))) return;
          try {
            await api('/api/config', { method: 'PUT', body: { ai: { remove_provider: p.name } } });
            toast(`档案 ${p.name} 已删除`); refresh();
          } catch (e) { toast(e.message, false); }
        };
        list.appendChild(row);
      });
    };
    renderList(cfg.ai.providers, cfg.ai.active);
    aiCard.querySelector('#add-prov').onclick = async () => {
      const name = prompt('档案名称（如 my-relay）：');
      if (!name) return;
      try {
        await api('/api/config', { method: 'PUT', body: { ai: { providers: [{ name: name.trim(), base_url: '', model: '', api_key: 'placeholder' }] } } });
        toast('已添加，请填写地址/模型/密钥'); refresh();
      } catch (e) { toast(e.message, false); }
    };
    container.appendChild(aiCard);

    // ---- 语义索引（RAG） ----
    const ragCard = el(`<div class="card" style="margin-bottom:16px"><div class="card-title">🧠 语义检索索引（RAG）
      <span class="hint">问答用：关键词+语义双路找相关段落，答得更准</span></div>
      <div class="rag-info" style="font-size:13px;color:var(--muted);margin-bottom:10px"></div>
      <div class="inline-form" style="flex-wrap:wrap">
        <label style="font-size:13px">向量模型
          <select class="r-model" style="width:230px"></select></label>
        <button class="btn r-fetch">⇩ 拉取模型</button>
        <button class="btn btn-primary r-build">⚡ 构建语义索引</button>
        <span class="r-msg" style="font-size:12px;color:var(--muted)"></span>
      </div>
      <div class="progress r-bar" style="margin-top:10px;display:none"><i style="width:0%"></i></div>
      <p style="color:var(--muted);font-size:12px;margin:8px 0 0">
        构建在后台进行（一次性，新文章自动增量补充）；之后每次问答只多 1 次极低费用的调用。
        不构建也能用：问答自动退回纯关键词检索。</p></div>`);
    const rModel = ragCard.querySelector('.r-model');
    const rMsg = ragCard.querySelector('.r-msg');
    const rBar = ragCard.querySelector('.r-bar');
    const rInfo = ragCard.querySelector('.rag-info');
    if (cfg.ai.embedding) rModel.innerHTML = `<option>${escape(cfg.ai.embedding)}</option>`;
    else rModel.innerHTML = '<option value="">（先拉取，默认 qwen 向量）</option>';
    const rSave = async () => {
      await api('/api/config', { method: 'PUT', body: { ai: { embedding: { model: rModel.value.trim() } } } });
      toast('向量模型已保存（已嵌入的块会按新模型重建）'); loadRag();
    };
    rModel.onchange = () => { if (rModel.value.trim()) rSave(); };
    ragCard.querySelector('.r-fetch').onclick = async () => {
      if (!cfg.ai.active) return toast('请先在上方配置并启用一个 AI 档案', false);
      rMsg.textContent = '拉取模型列表…';
      try {
        const r = await api('/api/ai/models', { method: 'POST', body: { provider_name: cfg.ai.active } });
        const cur = cfg.ai.embedding;
        rModel.innerHTML = r.models.map(m => `<option${m === cur ? ' selected' : ''}>${escape(m)}</option>`)
          .join('') || '<option value="">（该服务未返回模型）</option>';
        rMsg.textContent = `✅ 拉到 ${r.models.length} 个，选择后自动保存`;
      } catch (e) { rMsg.textContent = ''; toast(e.message, false); }
    };
    ragCard.querySelector('.r-build').onclick = async () => {
      try {
        const r = await api('/api/kb/rag/index', { method: 'POST' });
        if (r.started) { toast('已在后台开始构建'); poll(); }
        else rMsg.textContent = r.error || '已在构建中';
      } catch (e) { toast(e.message, false); }
    };
    const loadRag = async () => {
      try {
        const st = await api('/api/kb/rag/status');
        rInfo.innerHTML = `分块 <b>${st.chunks}</b> 段 · 已建语义 <b>${st.embedded}</b> 段 · 模型 <b>${escape(st.model)}</b> ·` +
          (st.ai_ready ? ' AI 已配置' : ' <span style="color:var(--amber)">AI 未配置（构建前请先在上方接入）</span>');
        if (st.building) {
          rBar.style.display = '';
          const pct = st.total ? Math.round(st.done / st.total * 100) : 3;
          rBar.querySelector('i').style.width = `${pct}%`;
          rMsg.textContent = `构建中 ${st.done}/${st.total}…`;
          setTimeout(loadRag, 2000);
        } else {
          rBar.style.display = st.done && st.total && st.done < st.total ? '' : 'none';
          rMsg.textContent = st.error || (st.embedded ? '✅ 语义索引就绪，问答已启用混合检索' : '');
        }
      } catch (e) { /* 忽略 */ }
    };
    const poll = loadRag;
    loadRag();
    container.appendChild(ragCard);

    // ---- 知识库路径 ----
    const kbCard = el(`<div class="card" style="margin-bottom:16px"><div class="card-title">📚 知识库路径</div>
      <div class="inline-form"><input placeholder="Markdown 知识库目录绝对路径" style="flex:1" value="${escape(cfg.kb.path || '')}">
      <button class="btn btn-primary kb-save">保存并扫描</button></div></div>`);
    const kbInput = kbCard.querySelector('input');
    kbCard.querySelector('.kb-save').onclick = async () => {
      try {
        const r = await api('/api/config', { method: 'PUT', body: { kb: { path: kbInput.value.trim() || null } } });
        if (r.kb_rescan && r.kb_rescan.imported >= 0) toast(`已保存，导入 ${r.kb_rescan.imported} 篇`);
        else toast('已保存（路径无效则不会导入）');
        refresh();
      } catch (e) { toast(e.message, false); }
    };
    container.appendChild(kbCard);

    // ---- 力扣对接 ----
    const lcCard = el(`<div class="card" style="margin-bottom:16px"><div class="card-title">🧮 力扣同步</div>
      <p style="color:var(--muted);font-size:12.5px;margin:0 0 8px">
        填 leetcode.cn 用户名拉公开进度；再填 Cookie（浏览器 F12 → 网络 → 任意请求 → 复制 Cookie 头）可同步最近 AC 到刷题记录。
        本地刷题文件夹用于力扣页的「问 AI」与「AI 考我」（如 D:\\leetcode）。只存本机。</p>
      <div class="inline-form">
        <input placeholder="力扣用户名" style="width:130px" class="lc-user" value="${escape(cfg.leetcode.username || "")}">
        <input type="password" placeholder="${cfg.leetcode.has_cookie ? "Cookie 已存（重填可覆盖）" : "登录 Cookie"}" style="flex:1" class="lc-cookie">
        <input placeholder="本地刷题文件夹（选填）" style="flex:1" class="lc-folder" value="${escape(cfg.leetcode.folder || "")}">
        <button class="btn btn-primary lc-save">保存并同步</button>
      </div></div>`);
    lcCard.querySelector(".lc-save").onclick = async () => {
      const body = { username: lcCard.querySelector(".lc-user").value.trim(),
                     folder: lcCard.querySelector(".lc-folder").value.trim() };
      const ck = lcCard.querySelector(".lc-cookie").value.trim();
      if (ck) body.cookie = ck;
      try {
        await api('/api/config', { method: 'PUT', body: { leetcode: body } });
        toast("配置已存，开始同步…");
        const r = await api('/api/leetcode/sync', { method: 'POST' });
        toast(r.error ? r.error : `同步完成：新导入 ${r.recent_imported} 条${r.cookie_ok ? "" : "（Cookie 缺失/过期）"}`, !r.error);
      } catch (e) { toast(e.message, false); }
    };
    container.appendChild(lcCard);

    // ---- 外观 & 数据 ----
    container.appendChild(el(`<div class="card">
      <div class="card-title">🎨 外观与数据</div>
      <p style="font-size:13px;margin:6px 0">· 深浅主题：右上角 🌙/☀️ 一键切换，自动记住<br>
      · 数据备份：复制 <code>data/workbench.db</code> 即可整库备份<br>
      · 所有数据仅存本机，不上传任何服务器</p></div>`));
  },
};
