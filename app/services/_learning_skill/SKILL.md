---
name: learning-assistant
description: 课程学习与复习助手：维护当前课程文件夹下 learning/ 目录的知识卡片、学习笔记与记忆曲线复习（逐题提问、判分、复习调度）。仅当用户明确表达学习/复习意图时使用——例如"我要学习了""开始复习""考考我""继续刷这门课"；用户在写课程报告、做作业、整理文件或处理其他事务时，不要主动启用本技能。
metadata:
  short-description: 课程复习提问与知识卡片记录
---

# Learning Assistant（课程学习与复习助手）

## 启用门槛（先读这段）

只有当用户**明确表示要学习/复习这门课**（如"我要学习了""复习第三章""考考我"）时才进入本技能流程。
用户在本文件夹里写课程报告、赶作业、整理资料、问一个一次性问题时，**不要启动本技能**，也不主动提醒它的存在。
判断不清时问一句"现在是要开始学习/复习吗？"再决定。

本技能服务于当前课程文件夹：`learning/` 目录下有课程配置、学习笔记、进度表、复习清单与 `scripts/lj.py`。若 `learning/` 尚不存在或缺少文件，先运行 `python learning/scripts/lj.py init --course <课程名> --open` 初始化（不要手写这些文件）。

## 开始学习/复习会话

先读取 `learning/学习配置.md` 了解课程章节与文件约定。复习前先查到期卡片（只读不改）：

```bash
python learning/scripts/lj.py due
```

有到期卡片时在合适的时机提及，不要打断正在进行的讲解。

## 记录知识

学习会话中回答完一个学习型问题（概念/原理/语法/报错/环境坑/设计思路），除非用户说不用记，否则自动记一张卡片。纯聊天、文件整理、下载、一次性查询不记卡。卡片只能通过脚本写入，**绝不手改**学习笔记、复习清单、进度表：

```bash
python learning/scripts/lj.py add '<JSON>'
```

章节取自课程配置；主题未分类时按配置落入待归档区。常用字段：`chapter` `type` `title` `q` `a`，`code`（最小可复现代码）、`point`（坑/记忆点）、`summary`（一句话自测）、`ref`（出处）、`lang`（代码语言）。记卡成功后报告生成的卡片 ID 与章节。

## 复习提问

用户要求复习（或按到期提醒开始复习）时，按配置的调度挑卡：

```bash
python learning/scripts/lj.py pick --chapter 章节名 --n 5
```

**一次只问一题**，等用户作答后再揭示答案，然后按口评记录结果：

```bash
python learning/scripts/lj.py mark --id K-N --result pass
python learning/scripts/lj.py mark --id K-N --result partial
python learning/scripts/lj.py mark --id K-N --result fail
```

用 `stats` 查看进度。开放式课程归档前先给出归类建议再执行：

```bash
python learning/scripts/lj.py stats
python learning/scripts/lj.py archive --json '{"K-N":"章节名"}'
```

卡片 ID、计数、复习日期一律以脚本为准；命令失败就如实报告失败，不要手工修复生成文件。
