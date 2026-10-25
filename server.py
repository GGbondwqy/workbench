# -*- coding: utf-8 -*-
"""学途工作台 · 本地服务入口。

用法：
    python server.py                 # 默认 127.0.0.1:8787，自动打开浏览器
    python server.py --port 9000     # 指定端口
    python server.py --no-browser    # 不自动开浏览器

零第三方依赖，仅需 Python 3.10+。
"""
import argparse
import logging
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import mimetypes
import json
import traceback
from urllib.parse import urlsplit, parse_qs

from app.bootstrap import create_app

ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "ui"
LOG = logging.getLogger("workbench.server")


class WorkbenchHandler(BaseHTTPRequestHandler):
    server_version = "StudyWorkbench/0.1"
    protocol_version = "HTTP/1.1"
    ctx = None   # 由 serve() 注入
    router = None

    # ---- 基础响应 ----
    def _send_json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_audio(self, path: Path, ctype: str):
        """二进制音频（F26 双通道之一）：支持单段 Range，供 <audio> 拖动进度。"""
        try:
            data = path.read_bytes()
        except OSError:
            self._send_json(404, {"error": "not found"})
            return
        total, status, extra = len(data), 200, {}
        rng = self.headers.get("Range") or ""
        if rng.startswith("bytes="):
            first, _, last = rng[6:].partition("-")
            try:
                start = int(first or 0)
                end = int(last) if last else total - 1
                if 0 <= start <= end < total:
                    data, status = data[start:end + 1], 206
                    extra["Content-Range"] = f"bytes {start}-{end}/{total}"
            except ValueError:
                pass
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Accept-Ranges", "bytes")
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path):
        try:
            data = path.read_bytes()
        except OSError:
            self._send_json(404, {"error": "not found"})
            return
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix in (".html", ".js", ".css"):
            ctype += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        if path.name == "index.html":
            # 坑 #6 根治：部分内嵌浏览器会给静态导入的 ES 模块留旧编译缓存，
            # 改了前端"刷新也不生效"。进站页带上 Clear-Site-Data，重载即清空本站缓存。
            self.send_header("Clear-Site-Data", '"cache"')
        self.end_headers()
        self.wfile.write(data)

    # ---- 请求分发 ----
    def _handle(self, method):
        parts = urlsplit(self.path)
        path = parts.path
        try:
            if path.startswith("/api/"):
                body = self._read_body()
                query = {k: v[-1] for k, v in parse_qs(parts.query).items()}
                result = self.router.dispatch(method, path, self.ctx, body, query)
                if result is None:
                    self._send_json(404, {"error": f"no route: {method} {path}"})
                else:
                    status, obj = result
                    if isinstance(obj, dict) and "_audio_file" in obj:
                        self._send_audio(Path(obj["_audio_file"]),
                                         obj.get("_audio_type") or "audio/mpeg")
                    else:
                        self._send_json(status, obj)
            else:
                self._serve_static(path)
        except BrokenPipeError:
            pass
        except Exception:
            LOG.error("unhandled error on %s %s\n%s", method, path, traceback.format_exc())
            self._send_json(500, {"error": "internal error"})

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except ValueError:
            ctype = (self.headers.get("Content-Type") or "").lower()
            if ctype.startswith("audio/") or ctype.startswith("application/octet-stream"):
                return {"_raw_bytes": raw, "_ctype": ctype}   # 二进制上传（v1.16 口语录音）
            return {"_raw": raw.decode("utf-8", "replace")}

    def _serve_static(self, path):
        rel = path.lstrip("/") or "index.html"
        if rel.endswith("/"):
            rel += "index.html"
        target = (UI_DIR / rel).resolve()
        # 路径穿越防护：必须仍在 ui 目录内
        if not str(target).startswith(str(UI_DIR.resolve())):
            self._send_json(403, {"error": "forbidden"})
            return
        if not target.is_file():
            target = UI_DIR / "index.html"  # SPA 回退
        self._send_file(target)

    # ---- HTTP 动词 ----
    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_DELETE(self):
        self._handle("DELETE")

    def log_message(self, fmt, *args):
        LOG.debug(fmt, *args)


def serve(host, port, open_browser):
    ctx, router = create_app(ROOT)
    WorkbenchHandler.ctx = ctx
    WorkbenchHandler.router = router

    httpd = ThreadingHTTPServer((host, port), WorkbenchHandler)
    url = f"http://{host}:{port}/"
    print(f"[学途工作台] 服务已启动: {url}  (Ctrl+C 退出)")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[学途工作台] 已停止")
    finally:
        httpd.server_close()
        ctx.close()


def main():
    parser = argparse.ArgumentParser(description="学途工作台本地服务")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    from app.core.config import load_config
    base_cfg = load_config(ROOT / "data")
    host = args.host or base_cfg["server"]["host"]
    port = args.port or base_cfg["server"]["port"]
    serve(host, port, not args.no_browser)


if __name__ == "__main__":
    main()
