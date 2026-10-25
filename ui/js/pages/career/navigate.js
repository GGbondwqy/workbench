// 投递导航（v1.19 F30）：招聘平台 + 公司官网分组，点链接新窗口直达投递
import { api } from '../../api.js';
import { el, escape } from '../kit.js';

export async function renderNavigate(container, refresh) {
  const nav = await api('/api/career/nav');

  const linkChip = (name, url, note = "") =>
    `<a class="btn nav-link" href="${escape(url)}" target="_blank" rel="noopener noreferrer"
        style="display:inline-flex;align-items:center;gap:6px;padding:6px 12px;font-size:13px;text-decoration:none">
      🌐 ${escape(name)}${note ? `<span style="color:var(--muted);font-size:11.5px">${escape(note)}</span>` : ""}</a>`;

  const pCard = el(`<div class="card" style="margin-bottom:14px">
    <div class="card-title">🧭 招聘平台 <span class="hint">找实习/校招/社招的一站入口，点击新窗口打开</span></div>
    <div class="nav-plat" style="display:flex;flex-wrap:wrap;gap:8px"></div></div>`);
  const plat = pCard.querySelector(".nav-plat");
  nav.platforms.forEach(x => plat.insertAdjacentHTML("beforeend", linkChip(x.name, x.url, x.note)));
  container.appendChild(pCard);

  nav.companies.forEach(g => {
    const card = el(`<div class="card" style="margin-bottom:14px">
      <div class="card-title">🏢 ${escape(g.group)} <span class="hint">点击直达该公司招聘官网（${g.items.length} 家）</span></div>
      <div class="nav-co" style="display:flex;flex-wrap:wrap;gap:8px"></div></div>`);
    const box = card.querySelector(".nav-co");
    g.items.forEach(x => box.insertAdjacentHTML("beforeend", linkChip(x.name, x.url)));
    container.appendChild(card);
  });

  container.appendChild(el(`<div style="color:var(--muted);font-size:12px;margin-top:4px">
    清单为软件内置（官方域名，可随版本增删）；打开后若站点要求登录，登录后搜索对应实习/校招岗位即可。</div>`));
}
