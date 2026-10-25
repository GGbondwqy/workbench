# -*- coding: utf-8 -*-
"""内置雅思写作题库（原创内容，随软件分发，无版权问题）。DESIGN v2.14 / v1.16。

- WRITE_T2：Task 2 议论文 8 大类 {id, title, prompt, structure:[段落要点], sample(≈280词), vocab}
- WRITE_T1：Task 1 图表 4 类 {id, title, prompt, structure, sample(≈170词), vocab}
范文为 Band 7 风格学术英语；Task 1 未配真实图表，练习重点为数据描述语言（配图练习请对照剑桥真题）。
"""

WRITE_T2 = [
    {"id": "t2-education-online", "task": 2, "title": "Education · Online Learning",
     "prompt": "Online education is becoming increasingly popular. Do the advantages "
               "of studying online outweigh the disadvantages?",
     "structure": ["引言：改写题目 + 明确立场（优势大于劣势）",
                   "主体1：优势 1-2（灵活、可及性）+ 展开例证",
                   "主体2：承认劣势（自律、实操）+ 反驳或让步",
                   "结论：重申立场 + 一句展望"],
     "sample": (
         "In recent years, studying through online platforms has moved from a niche "
         "alternative to a mainstream choice, particularly since the pandemic "
         "normalised remote learning. While online education brings clear drawbacks, "
         "I believe its advantages are greater for most learners.\n\n"
         "The primary benefit is flexibility. Students can access recorded lectures at "
         "any hour and replay difficult sections, which suits people who combine study "
         "with work or family responsibilities. A second advantage is reach: a learner "
         "in a small town can attend courses from top universities without relocating, "
         "and often at a fraction of the cost. During the pandemic, this accessibility "
         "kept education running for hundreds of millions of students who would "
         "otherwise have lost years.\n\n"
         "Admittedly, online study has real weaknesses. It demands a level of self-"
         "discipline that many students have not yet developed, and subjects that rely "
         "on laboratories or clinical practice are difficult to teach through a screen. "
         "There is also a social cost: much of what we learn at school comes from "
         "informal interaction with classmates, and a video call cannot fully replace "
         "it. However, these problems are increasingly being addressed through hybrid "
         "models that combine online content with occasional in-person sessions.\n\n"
         "In conclusion, although distance learning is not suitable for every subject "
         "or every personality, its flexibility and reach outweigh the disadvantages "
         "for the majority. The sensible path forward is not to reject online "
         "education but to design it carefully around its limits."),
     "vocab": ["normalise 使常态化", "a fraction of the cost 零头成本",
               "self-discipline 自律", "hybrid models 混合模式",
               "outweigh the disadvantages 优势大于劣势"]},
    {"id": "t2-technology-ai", "task": 2, "title": "Technology · AI at Work",
     "prompt": "Artificial intelligence will replace many jobs in the future. Some "
               "people think governments should slow down this development. Do you "
               "agree or disagree?",
     "structure": ["引言：改写 + 立场（不同意单纯拖慢，应引导）",
                   "主体1：AI 取代岗位的现实与风险",
                   "主体2：为什么「减速」不是答案（竞争力、技术不可逆）",
                   "主体3：更好的政策工具（再培训、税制、安全标准）",
                   "结论：重申"],
     "sample": (
         "Artificial intelligence is already reshaping labour markets, from translation "
         "to customer service, and anxiety about mass unemployment is understandable. "
         "Some argue that governments should deliberately slow the technology down. I "
         "disagree with this approach: slowing AI is neither feasible nor fair, and the "
         "wiser response is to manage its consequences.\n\n"
         "It is true that automation displaces workers. repetitive and predictable "
         "tasks — data entry, basic transcription, routine analysis — are being absorbed "
         "by machines faster than previous waves of technology. For affected individuals "
         "this is not an abstract debate but a sudden loss of income and identity.\n\n"
         "However, trying to brake the technology itself would fail on its own terms. AI "
         "development is global: a country that pauses it simply loses jobs to one that "
         "does not. Historically, from the printing press to the internet, attempts to "
         "suppress transformative technologies have protected neither workers nor "
         "consumers.\n\n"
         "Governments have better tools. First, fund large-scale retraining so that "
         "displaced workers can move into growing sectors rather than into unemployment. "
         "Second, update tax and welfare systems so that productivity gains are shared "
         "rather than concentrated. Third, set safety and transparency standards that "
         "steer AI towards augmenting humans instead of merely replacing them.\n\n"
         "In conclusion, the problem is not that AI is moving too quickly, but that our "
         "institutions are adapting too slowly. Governments should steer, not stall."),
     "vocab": ["labour markets 劳动力市场", "absorbed by machines 被机器吸收",
               "brake the technology 给技术踩刹车", "retraining 再培训",
               "steer, not stall 引导而非叫停"]},
    {"id": "t2-environment-individual", "task": 2, "title": "Environment · Personal Responsibility",
     "prompt": "Some people believe that individuals can do little to improve the "
               "environment; only governments and large companies can make a "
               "difference. To what extent do you agree?",
     "structure": ["引言：部分同意的立场",
                   "主体1：政府与企业的杠杆确实更大（法规、供应链）",
                   "主体2：但个人并非无能为力（需求信号、政治压力）",
                   "结论：二者互补而非对立"],
     "sample": (
         "It is often claimed that ordinary citizens are powerless in the face of "
         "environmental collapse, and that only governments and corporations have the "
         "leverage to act. I partly agree with this view, but I would argue that "
         "individuals play a role that the other two actors cannot replace.\n\n"
         "The case for focusing on institutions is strong. A single regulation on "
         "packaging or power-plant emissions can achieve what millions of well-meaning "
         "consumers cannot, and most carbon emissions can be traced to a few hundred "
         "companies rather than to private lifestyles. Asking individuals to solve a "
         "structural problem can even function as a distraction, shifting blame away "
         "from the industries that create it.\n\n"
         "Nevertheless, individuals are not powerless. Consumer demand is the signal "
         "companies respond to: the rapid growth of plant-based foods, second-hand "
         "markets and renewable energy tariffs all began with individual choices "
         "reaching critical mass. Voting behaviour matters even more directly — strong "
         "environmental regulation exists precisely because electorates demanded it. "
         "Personal habits also shape social norms, which is why one household's "
         "rooftop solar panels tend to spread down the street.\n\n"
         "In conclusion, governments and corporations do hold the larger levers, and I "
         "accept the premise of the argument to that extent. But individual and "
         "institutional action are complements, not substitutes: citizens create the "
         "political and market pressure without which large organisations will never "
         "act. The most accurate answer is that everyone holds part of the lever."),
     "vocab": ["leverage 杠杆/影响力", "structural problem 结构性问题",
               "critical mass 临界规模", "complements, not substitutes 互补而非替代",
               "hold part of the lever 各握一段杠杆"]},
    {"id": "t2-work-remote", "task": 2, "title": "Work · Remote Working",
     "prompt": "Working from home is becoming the norm. Do the benefits of this "
               "development outweigh the drawbacks for both employees and employers?",
     "structure": ["引言：现象 + 立场",
                   "主体1：员工与雇主各自获益点",
                   "主体2：代价（协作、新人成长、边界模糊）",
                   "结论：混合模式是最优解"],
     "sample": (
         "For a growing share of office workers, the daily commute has been replaced "
         "by a walk to the kitchen table, and remote work now looks less like a "
         "temporary experiment than a permanent norm. On balance, I believe the "
         "benefits outweigh the costs, provided companies manage the transition "
         "deliberately.\n\n"
         "Employees gain obvious advantages: hours reclaimed from commuting, greater "
         "autonomy over the working day, and for many people a quieter environment "
         "for deep work. Employers benefit too — smaller offices, access to talent in "
         "other cities, and in several documented cases equal or higher productivity. "
         "The pandemic effectively ran a global trial, and the sky did not fall.\n\n"
         "The drawbacks, however, are real. Collaboration suffers when every "
         "interaction must be scheduled; ideas that used to emerge in corridor "
         "conversations now require a calendar invitation. Junior staff lose the "
         "informal learning that happens by osmosis in an office. And when home becomes "
         "the workplace, the boundary between the two blurs, producing the modern "
         "problem of always being half at work.\n\n"
         "These costs explain why most firms have settled on hybrid arrangements "
         "rather than full remote: two or three office days preserve collaboration and "
         "mentoring while keeping most of the flexibility. In conclusion, remote work "
         "is a net positive, but the companies that benefit most are those that treat "
         "it as a design problem rather than an accident."),
     "vocab": ["a permanent version 永久形态", "by osmosis 耳濡目染",
               "the boundary blurs 边界模糊", "net positive 总体为正",
               "a design problem 设计问题"]},
    {"id": "t2-health-sport", "task": 2, "title": "Health · Public Sport Facilities",
     "prompt": "Some people think that governments should spend money on public "
               "sports facilities, while others believe this money should be spent "
               "on other public services. Discuss both views and give your opinion.",
     "structure": ["引言：呈现两种观点",
                   "主体1：反对方的理由（医疗、教育更紧迫）",
                   "主体2：支持方的理由（预防性健康、社会效益）",
                   "结论：给出平衡的个人立场"],
     "sample": (
         "How a city allocates its budget reveals its priorities, and the question of "
         "whether to fund public sports facilities or direct the money to other "
         "services is a genuinely difficult one. This essay will examine both sides "
         "before arguing that sport deserves a meaningful, if not dominant, share.\n\n"
         "Critics of spending on gyms and stadiums make a fair point. Hospitals, "
         "schools and care for the elderly are needs that feel immediate and "
         "non-negotiable, while a running track can look like a luxury. When budgets "
         "are tight, few voters would accept cutting a clinic to build a tennis "
         "centre, and sports facilities that stand empty become a symbol of waste.\n\n"
         "Supporters counter with an argument about prevention. Physical inactivity is "
         "a root cause of obesity, diabetes and depression, all of which cost health "
         "systems far more than a swimming pool does. Affordable facilities — running "
         "tracks, outdoor gyms, community courts — are among the cheapest health "
         "interventions available, and they generate social benefits beyond fitness: "
         "teenagers with somewhere to play in the evening are less likely to drift "
         "into trouble, and neighbourhood sport builds the trust that makes streets "
         "safer.\n\n"
         "In my view, the two positions can be reconciled by thinking of sport as "
         "preventive medicine. A modest, well-placed investment in free public "
         "facilities reduces future pressure on exactly the services the critics want "
         "to protect. The sensible policy is not to choose between a clinic and a "
         "court, but to fund the court so that fewer people end up needing the clinic."),
     "vocab": ["allocates its budget 分配预算", "non-negotiable 不可妥协的",
               "a root cause of 根源", "preventive medicine 预防医学",
               "be reconciled 被调和"]},
    {"id": "t2-media-news", "task": 2, "title": "Media · News Sources",
     "prompt": "Nowadays many people get their news from social media rather than "
               "newspapers or television. Do you think this development is positive "
               "or negative?",
     "structure": ["引言：现象 + 总体判断（利弊并存、关键在素养）",
                   "主体1：正面（速度、多元声音）",
                   "主体2：负面（算法茧房、假消息）",
                   "结论：媒体素养是决定因素"],
     "sample": (
         "Social media has become the primary news source for billions of people, "
         "displacing newspapers and broadcast television within a single generation. "
         "In my view this shift is neither simply positive nor simply negative — its "
         "value depends almost entirely on the media literacy of the person scrolling.\n\n"
         "The positive side is genuine. News now travels at the speed of a repost, so "
         "earthquakes, elections and public health warnings reach people instantly. "
         "Social platforms also break the gatekeeper monopoly of traditional media: "
         "witnesses can publish directly, and stories that powerful institutions would "
         "prefer buried can go viral. For minority voices and local communities, this "
         "democratisation of publishing has been transformative.\n\n"
         "The costs are equally real. Algorithms are optimised for engagement, not "
         "accuracy, which rewards outrage and punishes nuance; the result is that many "
         "users live inside filter bubbles that confirm what they already believe. "
         "Falsehood also travels faster than correction — research repeatedly shows "
         "fake stories spread further than true ones — and a generation that reads "
         "headlines without sources is poorly equipped to tell the difference.\n\n"
         "Overall, I would call the development conditionally positive. The technology "
         "has permanently widened who can speak and how fast information moves, which "
         "is a gain; whether that gain is realised depends on teaching people to check "
         "sources, read beyond headlines and seek out disagreement. Media literacy, "
         "not the platforms themselves, will decide whether this era is remembered as "
         "an enlightenment or an infection."),
     "vocab": ["gatekeeper monopoly 守门人垄断", "go viral 病毒式传播",
               "filter bubbles 信息茧房", "media literacy 媒介素养",
               "conditionally positive 有条件的积极"]},
    {"id": "t2-city-life", "task": 2, "title": "Cities · Overcrowding",
     "prompt": "Many cities are becoming overcrowded. What are the causes of this, "
               "and what solutions can you suggest?",
     "structure": ["引言：指出双问结构",
                   "主体1：原因（就业集中、公共资源、城乡差距）",
                   "主体2：对策（发展卫星城、公共服务均等化、远程办公）",
                   "结论：一句话总结"],
     "sample": (
         "Across the world, metropolitan areas keep swelling while smaller towns "
         "hollow out, and the resulting overcrowding puts pressure on housing, "
         "transport and public services. This essay examines the main drivers of the "
         "trend before proposing measures that could spread the load more evenly.\n\n"
         "The causes are primarily economic. Jobs — especially high-skilled ones — "
         "cluster in capital cities, so ambition pulls young people inward. Public "
         "investment follows the same gravity: the best hospitals, universities and "
         "cultural venues concentrate where the population already is, which attracts "
         "yet more people. Finally, mechanised agriculture has released rural workers "
         "who naturally move to where the jobs are, completing a self-reinforcing "
         "cycle.\n\n"
         "No single measure will reverse this, but several could slow it. The most "
         "promising is to build competing centres: relocating government agencies, "
         "universities and major employers to secondary cities creates jobs where "
         "housing is still affordable, as the development of new districts around "
         "several Chinese megacities has shown. Improving transport links — high-speed "
         "rail and regional metro networks — widens the area a city can draw workers "
         "from without cramming everyone into its core. And the rise of remote work, "
         "accelerated by the pandemic, offers a genuinely new option: some knowledge "
         "workers can now live wherever they like.\n\n"
         "In conclusion, overcrowding is the rational result of opportunity being "
         "concentrated in one place. The durable solution is not to discourage "
         "migration but to distribute the opportunity, so that staying does not mean "
         "falling behind."),
     "vocab": ["metropolitan areas 大都会区", "self-reinforcing cycle 自我强化循环",
               "secondary cities 二线城市", "cramming into 塞进",
               "distribute the opportunity 分散机会"]},
    {"id": "t2-society-aging", "task": 2, "title": "Society · Ageing Population",
     "prompt": "Societies around the world are ageing. What problems does this "
               "cause, and how can governments and individuals respond?",
     "structure": ["引言：双问结构",
                   "主体1：问题（养老金、医疗、劳动力萎缩）",
                   "主体2：应对（延迟退休、自动化、个人储蓄与健康）",
                   "结论：总结"],
     "sample": (
         "Falling birth rates and longer lifespans are quietly transforming societies: "
         "in Japan, Italy and increasingly China, more than a fifth of the population "
         "is already over sixty-five. This essay considers the pressures an ageing "
         "society creates and the responses available to governments and individuals.\n\n"
         "The problems arrive on three fronts. Public pensions were designed when ten "
         "workers supported each retiree; in some countries the ratio is heading "
         "towards two, which makes current systems arithmetically unsustainable. "
         "Health systems face similar strain, since elderly care is the most "
         "expensive kind. Meanwhile, a shrinking workforce slows the economic growth "
         "that pays for everything else.\n\n"
         "Governments have several levers, though none is painless. Raising the "
         "retirement age reflects longer healthy lifespans, and encouraging "
         "immigration offsets a shrinking workforce, though both are politically "
         "sensitive. Automation and AI can substitute for missing workers in many "
         "sectors, turning a demographic problem partly into a technology problem.\n\n"
         "Individuals, however, cannot leave this to policy. Working longer and "
         "saving earlier directly reduce dependence on the state, and — just as "
         "importantly — staying physically active and socially connected in "
         "middle age is the cheapest form of insurance against the illnesses that "
         "make old age expensive. A society of healthy seventy-year-olds faces a "
         "very different future from one of fragile ones.\n\n"
         "In conclusion, ageing threatens the arithmetic of welfare states and the "
         "momentum of economies. The response must combine pension reform and "
         "technology at the national level with earlier savings and healthier habits "
         "at the personal one."),
     "vocab": ["arithmetically unsustainable 算术上不可持续",
               "on three fronts 三条战线", "politically sensitive 政治敏感",
               "the cheapest form of insurance 最便宜的保险", "pension reform 养老金改革"]},
]

WRITE_T1 = [
    {"id": "t1-line-chart", "task": 1, "title": "Task 1 · 线图 Line Chart",
     "prompt": "The line graph shows the number of international students "
               "enrolled at three universities in Australia between 2000 and 2020. "
               "（数据示例：Uni A 12k→38k；Uni B 8k→22k；Uni C 5k→18k）",
     "structure": ["引言：改写题目（shows → illustrates/compares）",
                   "概览：一句总趋势（总体都在涨，A 涨最猛）",
                   "主体1：A 的走势（起点、显著增长、倍数）",
                   "主体2：B 与 C 对比（B 平稳领先 C；期末排序）"],
     "sample": (
         "The line graph illustrates how many international students were enrolled at "
         "three Australian universities over a twenty-year period from 2000 to 2020.\n\n"
         "Overall, student numbers rose at all three institutions, with University A "
         "experiencing by far the most dramatic growth.\n\n"
         "In 2000, University A had 12,000 international students, the highest of the "
         "three. Its enrolment climbed steadily throughout the first decade, reaching "
         "about 20,000 by 2010, before accelerating sharply in the following ten "
         "years to finish at 38,000 — more than tripling the starting figure.\n\n"
         "Universities B and C followed broadly similar upward paths but at a "
         "gentler pace. University B began with 8,000 students and grew almost "
         "linearly to 22,000 by the end of the period, while University C started "
         "from the lowest base of 5,000 and took until around 2015 to overtake "
         "University B's original figure, eventually closing the period at 18,000. "
         "Despite the convergence, University A remained the most popular "
         "destination for international students throughout."),
     "vocab": ["illustrates 展示", "by far the most dramatic growth 增长最猛",
               "climbed steadily 平稳攀升", "more than tripling 超过三倍",
               "closing the period at 期末达到"]},
    {"id": "t1-bar-chart", "task": 1, "title": "Task 1 · 柱图 Bar Chart",
     "prompt": "The bar chart shows the average weekly hours people in five "
               "age groups spent on social media in 2010 and 2020. "
               "（数据示例：18-25 岁 6→14h；26-40 岁 4→9h；41-55 岁 2→5h；56-70 岁 1→2h；70+ 0.5→1h）",
     "structure": ["引言：改写 + 时间跨度",
                   "概览：所有年龄组都在增长；年轻人耗时最多",
                   "主体1：18-25 组（翻倍以上）与 26-40 组",
                   "主体2：年长组增幅小 → 排序总结"],
     "sample": (
         "The bar chart compares the average time that five age groups spent on "
         "social media per week in 2010 and a decade later.\n\n"
         "Overall, usage increased across every age bracket, and the younger the "
         "group, the more hours it logged.\n\n"
         "Young adults aged 18 to 25 were the heaviest users in both years: their "
         "weekly average doubled from six hours in 2010 to fourteen in 2020, "
         "remaining well above all other groups. The 26-40 age band followed a "
         "similar trajectory, more than doubling from four to nine hours.\n\n"
         "Among older users the growth was steadier but smaller. Those aged 41 to "
         "55 went from two hours to five, while the 56-70 group rose from one hour "
         "to just two. People over seventy, who averaged only half an hour weekly in "
         "2010, reached a single hour by 2020 — still a fraction of what the "
         "youngest group spent. In short, although social media penetrated every "
         "generation over the decade, the age-based gap in usage widened rather "
         "than narrowed."),
     "vocab": ["age bracket 年龄段", "the heaviest users 使用最多的人群",
               "a similar trajectory 相似轨迹", "penetrated every generation 渗透每代人",
               "the gap widened 差距拉大"]},
    {"id": "t1-pie-charts", "task": 1, "title": "Task 1 · 饼图 Pie Charts",
     "prompt": "The pie charts show how household spending in an average family "
               "was distributed in 1995 and 2020 across five categories. "
               "（数据示例：Housing 30%→38%；Food 25%→15%；Transport 15%→12%；Education 10%→20%；Leisure 20%→15%）",
     "structure": ["引言：改写",
                   "概览：住房与教育占比升、食品降",
                   "主体1：上升项（Housing 最大且再升、Education 翻倍）",
                   "主体2：下降项（Food 从第二滑落、Transport/Leisure）"],
     "sample": (
         "The pie charts compare how an average household divided its spending "
         "across five categories in 1995 and twenty-five years later.\n\n"
         "Overall, housing and education absorbed a growing share of the family "
         "budget, while spending on food declined most sharply.\n\n"
         "Housing was the largest single expense in both years, rising from 30% of "
         "total spending in 1995 to 38% in 2020. The most striking change, however, "
         "was in education, which doubled from one-tenth of the budget to a fifth, "
         "overtaking transport to become the second-largest category.\n\n"
         "By contrast, food — the joint largest item in 1995 at a quarter of all "
         "spending — saw its share fall to just 15%, a reflection of falling food "
         "prices relative to other costs. Transport and leisure followed the same "
         "downward direction, shrinking from 15% and 20% respectively to 12% and "
         "15%. Taken together, the charts show a household whose fixed costs — "
         "roof and schooling — squeezed out nearly every other category over the "
         "period."),
     "vocab": ["absorbed a growing share 占比扩大",
               "the most striking change 最显著变化", "overtaking 反超",
               "a reflection of 是…的反映", "squeezed out 挤占"]},
    {"id": "t1-process", "task": 1, "title": "Task 1 · 流程图 Process",
     "prompt": "The diagram shows how recycled paper is produced from waste "
               "paper. （流程：收集分拣→浸泡打浆→去墨清洗→压平烘干→成品卷）",
     "structure": ["引言：改写 + 点明共几步",
                   "概览：循环性/多阶段",
                   "主体1：前半流程（收集→制浆→去墨），用被动语态+连接词",
                   "主体2：后半流程（压平→烘干→成品）"],
     "sample": (
         "The diagram illustrates the process by which waste paper is converted "
         "into new recycled paper, in five main stages.\n\n"
         "Overall, the process is largely mechanical and chemical, taking used "
         "paper through several treatments before it re-emerges as a usable "
         "product.\n\n"
         "First, used paper is collected from households and offices and sorted "
         "by hand to remove non-paper items such as staples and plastic. The "
         "sorted paper is then soaked in water and pulped into a thick fibrous "
         "mixture. In the third stage, ink and other impurities are stripped out: "
         "the pulp is filtered and chemically cleaned until it becomes a usable "
         "slurry.\n\n"
         "The cleaned pulp is spread into thin sheets, which are pressed to "
         "remove most of the water. Finally, the sheets are dried at high "
         "temperature and wound into large rolls of finished recycled paper, "
         "ready to be distributed to printers and publishers. What is notable is "
         "that the output can itself be recycled again, making the process a "
         "closed loop rather than a linear one."),
     "vocab": ["be converted into 被转化为", "pulped 打浆", "stripped out 去除",
               "wound into 卷成", "a closed loop 闭环"],
     "note": "配图练习请对照剑桥真题图表；本模板练的是流程描述语言。"},
]
