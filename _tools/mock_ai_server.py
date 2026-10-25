# -*- coding: utf-8 -*-
"""本地 mock OpenAI 兼容服务（8788）：用于无真实 key 时冒烟测试 AI 链路。"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        body = {"choices": [{"message": {"content":
            "模拟AI回答：三次握手的核心是确认双方的收发能力都正常。\n\n展开：SYN→SYN+ACK→ACK…\n\n记忆点：三次确认双向能力"}}]}
        data = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8788), H).serve_forever()
