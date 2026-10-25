# -*- coding: utf-8 -*-
"""投递导航清单（DESIGN v2.17 F30，v1.19）：纯数据零逻辑，随软件分发。

域名均为 2026-10-25 实测 HTTP 可达的官方入口；增删改清单=改本文件（无库表无迁移）。
"""

PLATFORMS = [
    {"name": "实习僧", "url": "https://www.shixiseng.com/", "note": "实习专场"},
    {"name": "BOSS 直聘", "url": "https://www.zhipin.com/", "note": "直聊约面"},
    {"name": "牛客", "url": "https://www.nowcoder.com/", "note": "校招+面经+笔试"},
    {"name": "智联招聘", "url": "https://www.zhaopin.com/", "note": "综合"},
    {"name": "前程无忧", "url": "https://www.51job.com/", "note": "综合"},
    {"name": "拉勾", "url": "https://www.lagou.com/", "note": "互联网"},
    {"name": "猎聘", "url": "https://www.liepin.com/", "note": "中高端"},
    {"name": "国聘", "url": "https://www.iguopin.com/", "note": "国企/央企"},
    {"name": "LinkedIn 领英", "url": "https://www.linkedin.com/jobs/", "note": "外企/海外"},
    {"name": "脉脉", "url": "https://maimai.cn/", "note": "内推/职场"},
]

COMPANIES = [
    {"group": "互联网大厂", "items": [
        {"name": "字节跳动", "url": "https://jobs.bytedance.com/campus/pos"},
        {"name": "腾讯", "url": "https://careers.tencent.com/"},
        {"name": "阿里巴巴", "url": "https://talent.alibaba.com/"},
        {"name": "蚂蚁集团", "url": "https://talent.antgroup.com/"},
        {"name": "美团", "url": "https://zhaopin.meituan.com/"},
        {"name": "京东", "url": "https://zhaopin.jd.com/"},
        {"name": "百度", "url": "https://talent.baidu.com/"},
        {"name": "拼多多", "url": "https://careers.pinduoduo.com/"},
        {"name": "网易", "url": "https://hr.163.com/"},
        {"name": "快手", "url": "https://zhaopin.kuaishou.cn/"},
        {"name": "小红书", "url": "https://job.xiaohongshu.com/"},
        {"name": "B站", "url": "https://jobs.bilibili.com/"},
        {"name": "滴滴", "url": "https://talent.didiglobal.com/"},
    ]},
    {"group": "硬件 / 智能 / 外企", "items": [
        {"name": "华为", "url": "https://career.huawei.com/"},
        {"name": "小米", "url": "https://hr.xiaomi.com/"},
        {"name": "大疆", "url": "https://we.dji.com/"},
        {"name": "科大讯飞", "url": "https://campus.iflytek.com/"},
        {"name": "微软", "url": "https://careers.microsoft.com/"},
        {"name": "谷歌", "url": "https://careers.google.com/"},
        {"name": "亚马逊", "url": "https://www.amazon.jobs/"},
        {"name": "英伟达", "url": "https://careers.nvidia.com/"},
        {"name": "Shopee", "url": "https://careers.shopee.com/"},
    ]},
]
