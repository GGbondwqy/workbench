// 页面注册表：新增页面 = 新建模块 + 此处加一行 import
// nav:false 的页面不出现在侧栏（如图谱全屏页），仍可用 #/graph 直达
import dashboard from './dashboard.js';
import goals from './goals.js';
import library from './library.js';
import english from './english.js';
import grad from './grad.js';
import career from './career.js';
import leetcode from './leetcode.js';
import graphview from './graphview.js';
import usage from './usage.js';
import settings from './settings.js';

export const pages = [
  dashboard, goals, library, english, grad, career, leetcode, graphview, usage, settings,
].map(p => ({ ...p, nav: p.nav !== false }));
