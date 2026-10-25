# 二次开发指南

> 面向想改代码、加模块、做定制的开发者（包括 AI 编码助手）。先读完本文再动手，可以少踩所有前人踩过的坑。
> 使用说明见 [USAGE.md](USAGE.md)。

---

## 1. 技术栈与目录结构

| 层 | 技术 | 说明 |
|---|---|---|
| 后端 | Python 3.10+ **标准库**（http.server / sqlite3 / json） | 零第三方依赖；`pip install pypdf` 为唯一可选增强 |
| 数据 | SQLite（WAL）+ `data/` 目录 | 单文件备份；迁移机制自建 |
| 前端 | 原生 HTML/CSS/JS（ES Modules），**无构建** | 改完刷新即生效 |
| AI | OpenAI 兼容 HTTP 适配器（urllib） | 一套适配器通吃 DeepSeek / Qwen / 中转站 |

```
server.py            入口：静态服务 + SPA 回退 + /api/* 分发 + 路径穿越防护
app/
  bootstrap.py       唯一组装点（Composition Root）：register → 迁移 → post_migrate → 路由
  core/              核心层（无业务概念）：config / db / events / registry / timeutil / textkit
  ai/                AI Provider 层：chat() + embed()，未配置返回 None
  services/          业务逻辑层：每域一个模块，自动发现（20 个域）
  api/               薄路由层：routes_*.py 自动发现
ui/
  js/main.js         前端入口：主题 → 导航 → hash 路由
  js/pages/          页面注册表（新页面 = 新文件 + index.js 一行）
  js/components/     图谱渲染 / 阅读弹窗
data/                运行时数据（gitignore）：workbench.db + config.json（含密钥）+ 本机内容
_tools/              测试套件（纯 Python urllib）
```

## 2. 分层架构与依赖规则（红线，违反必返工）

```
ui → api → services → core
ai → core
```

1. **core 不 import 任何上层**：core 里只有通用设施，不知道任何业务概念。
2. **services 之间禁止互相 import**。跨域协作只有两种合法方式：
   - 注册表查询：`ctx.services.get("task_service").xxx()`；
   - 事件总线：`ctx.events.publish("task.completed", {...})` / `ctx.events.subscribe(...)`。
3. **共享无状态纯函数放 `app/core/textkit.py`**：多个域都用到的通用纯函数（文本抽取/分块/关键词/选段/AI 输出解析）下沉 core，services 向下 import 合法。判据：**无状态、零业务概念、只被调用不调用他人**。带业务语义的解析（如学习卡片格式、题库校验）留在各自域内。
4. **调度一律在业务逻辑层**（服务里），UI 只发起请求展示结果，底层只被调用。
5. **数据表所有权**：每个 service 只建/只写自己的表（表名带域前缀）；跨域读数据走对方 service 的查询方法，禁止跨域直写表。
6. **api 层禁止直连 db**，一切经 service；**ai 层禁止 import 任何 service**。

## 3. 启动流程与自动发现

`app/bootstrap.py` 依次执行：

1. 读配置（`data/config.json`，本地覆盖）
2. 建 DB / EventBus / ServiceRegistry / AIRegistry
3. **自动扫描** `app/services/*.py`：每个模块暴露 `register(ctx)`（注册服务 + 登记迁移 + 订阅事件）
4. 执行数据库迁移（`schema_migrations` 表记录，幂等）
5. `post_migrate(ctx)`：种子数据必须放这里（迁移后才可查表，**不能放 register**）
6. **自动扫描** `app/api/routes_*.py`：每个暴露 `register_routes(router, ctx)`

## 4. 新增一个业务模块（零改动接入）

三件套，不改任何既有模块文件：

```python
# 1) app/services/thing.py
from app.core.registry import AppContext

MIGRATIONS = [
    ("0001_thing", """
        CREATE TABLE IF NOT EXISTS thing_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at TEXT DEFAULT '')""")
]

class ThingService:
    name = "thing_service"
    def __init__(self, ctx: AppContext):
        self._ctx = ctx
    def add(self, title):
        self._ctx.db.execute(
            "INSERT INTO thing_items (title) VALUES (?)", (title,))

def register(ctx: AppContext):
    ctx.services.register(ThingService.name, ThingService(ctx))
```

```python
# 2) app/api/routes_thing.py
from app.core.registry import AppContext

def register_routes(router, ctx):
    T = lambda: ctx.services.get("thing_service")
    def add(ctx: AppContext, params, body, query):
        T().add(body["title"]); return {"ok": True}
    router.post("/api/things", add)
```

```javascript
// 3) ui/js/pages/thing.js + 在 pages/index.js 加一行 import
import { api } from '../api.js';
import { el } from './kit.js';

export async function renderThing(container, refresh) { /* 调 /api/things */ }

export default { id: 'thing', title: '新页面', icon: '🧩', render: renderThing };
```

## 5. 共享文本工具（app/core/textkit.py）

| 函数 | 用途 |
|---|---|
| `extract_text(path)` | 尽力抽取文件正文：md/txt/代码直读，docx/pptx 标准库解包，pdf 走可选 pypdf；失败返回空串 |
| `docx_text(data)` / `pptx_text(data)` | 二进制 → 文本（标准库解包） |
| `pdf_text(data)` | 返回 `None` 表示 pypdf 缺失或解析失败（调用方据此降级提示） |
| `chunks_of(text, size=500)` | 按空行聚段分块 |
| `terms_of(q)` | 查询词项（中文二字组 + 英文/数字词） |
| `select_chunks(files_text, query, k, budget)` | 关键词打分选段喂 AI；query 为空时轮转各文件（出题用） |
| `parse_quiz_json(reply, n)` | AI 出题 JSON 容错解析，失败返回 `[]` |

**什么时候该下沉 core**：第二个域也要用同一个函数时就该下沉；只在一个域里用的（哪怕看起来通用）留在域内。

## 6. AI 层契约（app/ai/）

- 业务代码统一 `ctx.ai.chat(messages, feature="功能标签")` / `ctx.ai.embed(texts)`；
- **未配置 / 调用失败返回 `None`**——调用方必须写降级路径（本地规则/原文段落/自评自打卡），这是"不配 AI 也 100% 可用"底线的实现方式；
- `feature` 标签会进入用量记账（ai_usage 表），取值如：知识问答 / 每日建议 / 课程问答 / 力扣问答 / 语义嵌入；
- 配置热更新：`PUT /api/config` 后 `ctx.ai.refresh(...)`，无需重启。

## 7. 前端约定

- **无构建**：原生 ES Modules，页面模块 `export default { id, title, icon, render }`，在 `pages/index.js` 注册；
- `el(html)` **模板只能有一个根元素**——多根时第二个被静默丢弃（历史上坑过一次）；
- 按钮绑定**禁止 `querySelector('button')` 通用取法**（会取到卡片里第一个按钮），一律用明确 class 名；
- 删除等危险操作统一走 `confirmBox()`（kit.js），不要用 `window.confirm`；
- hash 路由只认第一段（`#/grad/courses/3` 的后两段由 grad 页自解析）；**改前端后浏览器要强刷**（Ctrl+F5），hash 切页不重载 JS 模块；
- fetch 统一走 `api.js` 的 `api()` 封装（错误会 throw，页面 catch 后 toast）。

## 8. 测试（_tools/）

- 跑法：先起服务，再 `python -X utf8 _tools/xxx_test.py`（**必须 `-X utf8`**；不要用 Git Bash curl 发中文——会丢字符，测试一律 Python urllib）；
- 套件：`e2e_test.py`（全链路）+ `v13~v30_test.py`（各版本专项，纯函数/夹具类可离线跑）；
- **哪些依赖本地数据**：e2e / v13 依赖知识库有文章（全新克隆可能失败，属预期）；v24-v30、v28 等纯函数与临时夹具套件开箱即跑；
- **自清洁铁律**：新增用例凡写用户数据域，测完必须清理——API 有 DELETE 用 API，没有则 sqlite 回滚；**测试进程持有未提交的 sqlite 写事务时，服务端写端点会撞锁 500**（API 自清洁放在本地事务 commit/close 之后）；
- **AI 劫持测试**（mock OpenAI）整存整还 `base_url / model / embedding / active` 四件，只恢复 active 会把用户档案指向死掉的 mock 端口；
- 含中文的 query 参数必须 `urllib.parse.quote(x, safe='')`。

## 9. 踩坑清单（前人付过学费）

1. **8787 端口多实例**：端口被占不报错而是多实例同听，"改了不生效"。起服务前 `netstat -ano | grep 8787`，taskkill 干净再起。
2. **改后端必须重启服务；改前端浏览器强刷**。
3. **种子数据放 `post_migrate(ctx)`**，不能在 `register(ctx)` 里查表。
4. SQLite 单元素元组带逗号 `(x,)`；FTS5 中文靠"字间插空格"分词，短语匹配加引号。
5. `today = ...today()` 式局部变量遮蔽模块函数 → UnboundLocalError 高发点。
6. per-item `except` 会把错误吞进结果列表而非日志——外部请求"永久挂起"先限流跑一次看列表内容。
7. 大文件下载必须带总时长+大小上限（`resp.read()` 会被慢速滴流拖死）；同秒生成的文件名要防撞。
8. **上游接口会漂移**（如 leetcode.cn GraphQL schema 改版）：内省被禁时，下载站点主页 JS chunk 搜 `query \w+` 提取现行查询文本，勿手改旧字段。
9. Windows 下用 Python pathlib 处理中文路径，别用 shell 的 rm/glob。

## 10. 数据与隐私约束（改代码时同样要守）

- `data/` 整目录 gitignore：数据库、config.json（含密钥）、日志、本机内容（题库/录音/自建文章）；
- **第三方版权内容绝不入库**：外部知识库/收集的题库只存在 `data/` 或仓库外目录，靠配置挂载；
- 密钥只写本机：任何页面/接口回显配置时只能给 `has_key` 布尔，不能回显密钥本体；
- 服务默认只绑 `127.0.0.1`。

## 11. 发布前检查清单

- [ ] `grep -rn "sk-\|api_key.*=\s*['\"]" app/ ui/ _tools/` 无真实密钥
- [ ] `data/` 不在 git 追踪中（`git status` 应看不到）
- [ ] 个人路径/用户名/站外地址已清理（搜索 `D:\`、个人用户名等）
- [ ] 新增表有迁移 SQL 且旧库可幂等升级
- [ ] 新 AI 功能有 `None` 降级路径
- [ ] 测试套件跑绿，且新用例已自清洁
