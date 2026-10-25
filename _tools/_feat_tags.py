# -*- coding: utf-8 -*-
"""一次性：给四处 AI 调用加 feature 标签（v1.10）。"""
import io
import re

# learn.py：两处 chat([ ... ]) → feature="学习卡片"
p = 'app/services/learn.py'
t = io.open(p, encoding='utf-8').read()
blocks = [m.start() for m in re.finditer(r'self\._ctx\.ai\.chat\(\[', t)]
assert len(blocks) == 2, f"learn.py 期望 2 处 chat，实际 {len(blocks)}"
for s in sorted(blocks, reverse=True):
    e = t.index('])', s)
    t = t[:e] + '], feature="学习卡片")' + t[e + 2:]
io.open(p, 'w', encoding='utf-8', newline='').write(t)

# plan.py：每日建议
p = 'app/services/plan.py'
t = io.open(p, encoding='utf-8').read()
old = '"今日建议：" + "；".join(i["title"] for i in top3)})'
assert old in t, 'plan.py 锚点未命中'
t = t.replace(old, '"今日建议：" + "；".join(i["title"] for i in top3)},\n                feature="每日建议")', 1)
io.open(p, 'w', encoding='utf-8', newline='').write(t)

# kb.py：知识问答（锚点用不含反斜段的行）
p = 'app/services/kb.py'
t = io.open(p, encoding='utf-8').read()
i = t.find('" + context},')
assert i > 0 and t[i:i + len('" + context},\n        ])')] == '" + context},\n        ])'
t = t[:i] + '" + context},\n        ], feature="知识问答")' + t[i + len('" + context},\n        ])'):]
io.open(p, 'w', encoding='utf-8', newline='').write(t)

print('feature tags done: kb=知识问答 / plan=每日建议 / learn×2=学习卡片')
