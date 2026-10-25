// 前端入口：主题 → 顶栏日期 → 导航 → 路由
import { initTheme } from './theme.js';
import { initRouter } from './router.js';
import { pages } from './pages/index.js';

function renderNav() {
  const nav = document.getElementById('nav');
  nav.innerHTML = pages.filter(p => p.nav).map(p => `
    <a href="#/${p.id}" data-page="${p.id}">
      <span>${p.icon}</span><span>${p.title}</span>
    </a>`).join('');
}

function markActive(id) {
  document.querySelectorAll('#nav a').forEach(a =>
    a.classList.toggle('active', a.dataset.page === id));
}

function renderToday() {
  const now = new Date();
  const fmt = new Intl.DateTimeFormat('zh-CN', {
    month: 'long', day: 'numeric', weekday: 'long',
  }).format(now);
  document.getElementById('today').innerHTML =
    `${fmt}<small>学途工作台 · 研一 · 2029 届</small>`;
}

// 页面重渲染（供页面内操作后刷新自身，避免整页 reload）
async function renderPage(id) {
  markActive(id);
  const view = document.getElementById('view');
  const page = pages.find(p => p.id === id) || pages[0];
  const rerender = () => renderPage(id);
  view.innerHTML = '';
  try {
    await page.render(view, rerender);
  } catch (e) {
    view.innerHTML = `<div class="card"><div class="empty">
      <span class="icon">⚠️</span>
      <div class="title">页面渲染失败</div>
      <div>${String(e && e.message || e)}</div></div></div>`;
  }
  document.title = `${page.title} · 学途工作台`;
}

initTheme();
renderNav();
renderToday();
initRouter(renderPage);
