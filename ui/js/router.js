// hash 路由：#/career/projects → 页面 id 只取第一段，其余段供页面内子 Tab 使用
export function currentRoute(fallback = 'dashboard') {
  const hash = location.hash.replace(/^#\/?/, '').split('?')[0];
  const id = hash.split('/')[0];
  return id || fallback;
}

export function navigate(id) {
  location.hash = `#/${id}`;
}

export function initRouter(onRoute) {
  const fire = () => onRoute(currentRoute());
  window.addEventListener('hashchange', fire);
  fire();
}
