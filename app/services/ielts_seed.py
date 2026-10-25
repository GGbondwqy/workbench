# -*- coding: utf-8 -*-
"""内置雅思仿真题（原创内容，随软件分发，无版权问题）。

题组结构（DESIGN F17/F18）：
{ id, subject(listening/reading), title, source=builtin,
  sections: [ { intro(可选), material(原文), questions: [
      { no, type(choice/tfng/blank), stem, options?(choice), answer, explain } ] } ] }
公开收集/手工导入的题组放 data/ielts_bank/*.json，同构。
"""

SEED_SETS = [
    # ================= 听力 1：Section 1 租房咨询 =================
    {
        "id": "b-listen-1",
        "subject": "listening",
        "title": "仿真 · Section 1 租房咨询对话",
        "source": "builtin",
        "sections": [
            {
                "intro": "你是租房咨询处的接待员，听下面这段对话，完成第 1-6 题。"
                         "（无音频时可用『看题回忆』模式：先读题作答，提交后再对照原文）",
                "material": (
                    "AGENT: Good morning, Greenfield Lettings. How can I help you?\n"
                    "WOMAN: Hi, I'm looking for a two-bedroom flat near the university, "
                    "starting from the first of next month.\n"
                    "AGENT: Certainly. Do you have a budget in mind?\n"
                    "WOMAN: Ideally no more than six hundred pounds a month, including bills "
                    "if possible.\n"
                    "AGENT: Six hundred… we have a ground-floor flat on Maple Road at 575, "
                    "but bills are extra. Water and electricity usually come to about 45 a "
                    "month in winter.\n"
                    "WOMAN: That's still within range. Is it furnished?\n"
                    "AGENT: Partly — beds and wardrobes are included, but there's no sofa "
                    "and no washing machine.\n"
                    "WOMAN: Oh. A washing machine is fairly important for me.\n"
                    "AGENT: Then perhaps the flat on Bridge Street. It's 610 a month, fully "
                    "furnished, washing machine included, and it's only a ten-minute walk to "
                    "the campus. It's on the second floor.\n"
                    "WOMAN: That sounds better. What about transport? I sometimes work "
                    "evenings at the library.\n"
                    "AGENT: The number 14 bus runs every fifteen minutes until midnight, and "
                    "there's a night bus, the N9, at half past one.\n"
                    "WOMAN: Great. And when could I view it?\n"
                    "AGENT: The current tenant is moving out on the 28th, so viewings start "
                    "on the 29th — that's a Wednesday. I can book you in at 10 a.m. or 4 p.m.\n"
                    "WOMAN: Let's make it four in the afternoon.\n"
                    "AGENT: Done. Could I take your name?\n"
                    "WOMAN: Yes, it's Helen Carter — C-A-R-T-E-R. And my mobile is "
                    "double seven, double six, oh, three two, nine four one.\n"
                    "AGENT: Thank you, Helen. See you on the 29th."
                ),
                "questions": [
                    {"no": 1, "type": "choice",
                     "stem": "How many bedrooms does the woman need?",
                     "options": ["One", "Two", "Three"], "answer": "B",
                     "explain": "开头明确提出 a two-bedroom flat。"},
                    {"no": 2, "type": "blank",
                     "stem": "Monthly rent of the Maple Road flat: £ ______",
                     "answer": "575",
                     "explain": "原文：a ground-floor flat on Maple Road at 575。"},
                    {"no": 3, "type": "choice",
                     "stem": "Why does the woman reject the Maple Road flat?",
                     "options": ["It is too far from campus",
                                 "The rent is too high",
                                 "It has no washing machine"],
                     "answer": "C",
                     "explain": "她说 A washing machine is fairly important，而该房没有。"},
                    {"no": 4, "type": "blank",
                     "stem": "Floor of the Bridge Street flat: the ______ floor",
                     "answer": "second|2nd",
                     "explain": "原文：It's on the second floor。"},
                    {"no": 5, "type": "choice",
                     "stem": "When does the late-night bus N9 leave?",
                     "options": ["At 1:30 a.m.", "At 2:30 a.m.", "Every 15 minutes"],
                     "answer": "A",
                     "explain": "原文：the N9, at half past one（凌晨一点半）。"},
                    {"no": 6, "type": "blank",
                     "stem": "Viewing appointment time on 29th: ______ p.m.",
                     "answer": "4|four",
                     "explain": "她选择了 four in the afternoon。"},
                ],
            },
        ],
    },
    # ================= 听力 2：Section 4 学术讲座 =================
    {
        "id": "b-listen-2",
        "subject": "listening",
        "title": "仿真 · Section 4 讲座：城市里的蜜蜂",
        "source": "builtin",
        "sections": [
            {
                "intro": "听一段关于城市蜜蜂的学术讲座节选，完成第 1-6 题。"
                         "（无音频时按『机经』模式自测）",
                "material": (
                    "LECTURER: Today I want to talk about an unexpected finding in urban "
                    "ecology — that city bees are often healthier than their rural "
                    "cousins. Since 2015, my team has sampled honeybee colonies in twelve "
                    "European cities, comparing them with colonies on farmland nearby.\n"
                    "The first surprise was parasite load. Urban colonies carried roughly "
                    "thirty per cent fewer mites, probably because cities break up the "
                    "large monoculture belts where parasites spread so easily.\n"
                    "Second, diet. We analysed pollen from the hives and found urban bees "
                    "visited on average over a hundred and twenty plant species, against "
                    "only about forty in farmland. City parks, balconies and railway "
                    "embankments together create what we call a 'patchy but rich' buffet.\n"
                    "Third, and this is the part that worried us: winter survival. Bees "
                    "depend on autumn flowers to build up fat reserves, yet municipal "
                    "planting schemes are often chosen for summer colour. In our coldest "
                    "study year, city colonies still lost a quarter of their numbers, "
                    "slightly worse than rural ones.\n"
                    "So what can planners do? Our modelling suggests three measures. "
                    "Plant late-flowering species such as ivy and heather; reduce mowing "
                    "from fortnightly to twice a year on roadside verges; and — perhaps "
                    "most effectively — link green roofs into continuous corridors, since "
                    "bees rarely fly higher than about the fifth storey."
                ),
                "questions": [
                    {"no": 1, "type": "blank",
                     "stem": "Study began in the year ______",
                     "answer": "2015",
                     "explain": "原文：Since 2015, my team has sampled…"},
                    {"no": 2, "type": "blank",
                     "stem": "Urban colonies carried ______% fewer mites",
                     "answer": "30|thirty",
                     "explain": "原文：roughly thirty per cent fewer mites。"},
                    {"no": 3, "type": "choice",
                     "stem": "How many plant species did urban bees visit on average?",
                     "options": ["About 40", "About 120", "About 400"],
                     "answer": "B",
                     "explain": "原文：over a hundred and twenty plant species。"},
                    {"no": 4, "type": "tfng",
                     "stem": "City bees always survive winter better than rural bees.",
                     "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "F",
                     "explain": "讲座说最冷年份城市蜂群损失 1/4，略差于乡村——不是 always better。"},
                    {"no": 5, "type": "choice",
                     "stem": "Which measure does the lecturer call MOST effective?",
                     "options": ["Planting ivy and heather", "Reducing mowing",
                                 "Linking green roofs into corridors"],
                     "answer": "C",
                     "explain": "原文：perhaps most effectively — link green roofs。"},
                    {"no": 6, "type": "blank",
                     "stem": "Bees rarely fly above about the ______ storey",
                     "answer": "fifth|5th|5",
                     "explain": "原文：higher than about the fifth storey。"},
                ],
            },
        ],
    },
    # ================= 阅读 1 =================
    {
        "id": "b-read-1",
        "subject": "reading",
        "title": "仿真 · Passage 1 北极燕鸥的漫长旅途",
        "source": "builtin",
        "sections": [
            {
                "intro": "阅读下面文章，完成第 1-7 题。",
                "material": (
                    "The Arctic tern is a small seabird, barely a hundred grams in weight, "
                    "yet it undertakes the longest known migration of any living creature. "
                    "Each year it travels from its breeding grounds in the Arctic to the "
                    "Antarctic and back again — a round trip of some 70,000 kilometres.\n\n"
                    "For decades, ornithologists could only estimate this journey from "
                    "occasional ring recoveries. That changed in 2010, when researchers "
                    "fitted tiny geolocators to terns nesting in Greenland and Iceland. "
                    "The data revealed two distinct strategies. Birds from Greenland flew "
                    "down the eastern side of the Atlantic, pausing in a rich feeding zone "
                    "off West Africa's Canary Current. Icelandic terns, by contrast, "
                    "crossed to the Americas and travelled south along the Brazilian coast, "
                    "a route several thousand kilometres longer.\n\n"
                    "Why take the detour? The answer appears to be wind. Terns exploit the "
                    "prevailing easterly trade winds over the Atlantic, and for Icelandic "
                    "birds the American route offers stronger tailwinds for much of the "
                    "journey. Energy models suggest that a tern riding favourable winds "
                    "uses up to a third less energy per kilometre than one fighting "
                    "headwinds, even over a greater distance.\n\n"
                    "Timing matters as much as route. Terns time their arrival in Antarctica "
                    "to coincide with the austral summer, so they experience two summers "
                    "each year. In a life of twenty to thirty years, this adds up to a great "
                    "many hours of daylight — the reason the tern has been called 'the bird "
                    "that lives in daylight'.\n\n"
                    "Not everything about the journey is understood. Few recoveries exist "
                    "from the northern return leg in spring, and scientists still debate "
                    "whether terns rest on the water at night or keep flying. What is clear "
                    "is that the species' fortunes are tied to both polar regions: it "
                    "breeds at one end of the planet and feeds at the other, which makes it "
                    "an unusually sensitive indicator of climate change."
                ),
                "questions": [
                    {"no": 1, "type": "tfng",
                     "stem": "The Arctic tern's annual round trip covers about 70,000 km.",
                     "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "T",
                     "explain": "首段末句原义。"},
                    {"no": 2, "type": "tfng",
                     "stem": "Before 2010, scientists tracked terns mainly by ring recoveries.",
                     "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "T",
                     "explain": "第二段：could only estimate this journey from occasional "
                                "ring recoveries。"},
                    {"no": 3, "type": "choice",
                     "stem": "Icelandic terns travel south along the coast of ______",
                     "options": ["West Africa", "Brazil", "Greenland"], "answer": "B",
                     "explain": "第二段：travelled south along the Brazilian coast。"},
                    {"no": 4, "type": "blank",
                     "stem": "Riding favourable winds can save up to ______ (a fraction) "
                             "less energy per kilometre.",
                     "answer": "a third|1/3|one third|one-third",
                     "explain": "第三段：uses up to a third less energy。"},
                    {"no": 5, "type": "tfng",
                     "stem": "Scientists have proved that terns sleep while floating on "
                             "the water.",
                     "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "NG",
                     "explain": "末段说 scientists still debate（尚有争论），未证实。"},
                    {"no": 6, "type": "choice",
                     "stem": "Why is the tern called 'the bird that lives in daylight'?",
                     "options": ["It flies only in daytime",
                                 "It experiences two summers a year",
                                 "It breeds in Antarctica"],
                     "answer": "B",
                     "explain": "倒数第二段：it experiences two summers each year。"},
                    {"no": 7, "type": "blank",
                     "stem": "In the wild, an Arctic tern can live roughly ______ to thirty "
                             "years. (one word / a number)",
                     "answer": "twenty|20",
                     "explain": "In a life of twenty to thirty years。"},
                ],
            },
        ],
    },
    # ================= 阅读 2 =================
    {
        "id": "b-read-2",
        "subject": "reading",
        "title": "仿真 · Passage 2 屋顶绿化：不只是好看",
        "source": "builtin",
        "sections": [
            {
                "intro": "阅读下面文章，完成第 1-7 题。",
                "material": (
                    "Walk through any modern European city and you will notice a quiet "
                    "change in its skyline: roofs that were once grey gravel are turning "
                    "green. Green roofs — layers of waterproofing, drainage, growing "
                    "medium and plants — are no longer an architect's novelty. In Berlin, "
                    "roughly thirty per cent of new flat roofs are planted; in Toronto, "
                    "by-laws since 2009 have made them compulsory on large new buildings.\n\n"
                    "The most frequently cited benefit is storm water. A saturated green "
                    "roof can hold between fifty and eighty per cent of the rain that "
                    "falls on it, releasing the rest slowly over hours instead of minutes. "
                    "Cities that retrofit green roofs at scale can postpone spending on "
                    "bigger storm drains, an unglamorous saving that finance departments "
                    "have begun to notice.\n\n"
                    "Energy comes second. The growing medium acts as insulation, cutting "
                    "summer heat gain through the roof by up to seventy-five per cent and "
                    "reducing winter losses, though the winter effect is more modest. "
                    "Studies in Chicago estimated that greening all of the city's roofs "
                    "would save several million dollars a year in cooling costs.\n\n"
                    "Less easy to price is the effect on urban wildlife. Even thin "
                    "'extensive' roofs, planted with sedum, support more insect species "
                    "than bare gravel, and when roofs are close enough for insects to "
                    "move between them, they begin to function as stepping stones for "
                    "bees and butterflies.\n\n"
                    "Green roofs are not a free lunch. They cost two to three times as "
                    "much to install as conventional roofs, add loading that some older "
                    "structures cannot bear, and need weeding and drainage inspection "
                    "for as long as they exist. Critics also point out that planting a "
                    "roof does nothing for a building's walls or windows, where much of "
                    "the energy is actually lost. The honest case for green roofs is not "
                    "any single number but the sum of small benefits — water, heat, "
                    "wildlife and the simple pleasure of a city that looks less like "
                    "machinery and more like a landscape."
                ),
                "questions": [
                    {"no": 1, "type": "choice",
                     "stem": "In Toronto, green roofs on large new buildings are ______",
                     "options": ["optional", "required by law", "paid for by the state"],
                     "answer": "B",
                     "explain": "第一段：by-laws since 2009 have made them compulsory。"},
                    {"no": 2, "type": "blank",
                     "stem": "A saturated green roof can retain up to ______% of rainfall.",
                     "answer": "80|eighty",
                     "explain": "第二段：between fifty and eighty per cent，上限 80%。"},
                    {"no": 3, "type": "tfng",
                     "stem": "Green roofs reduce winter heat loss as effectively as "
                             "summer heat gain.",
                     "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "F",
                     "explain": "第三段：winter effect is more modest（冬季效果较弱）。"},
                    {"no": 4, "type": "choice",
                     "stem": "Chicago's estimate about cooling savings suggests ______",
                     "options": ["retrofitting all roofs would cost several million dollars",
                                 "greening all roofs could save several million dollars a year",
                                 "green roofs have no measurable financial effect"],
                     "answer": "B",
                     "explain": "原文：save several million dollars a year in cooling costs。"},
                    {"no": 5, "type": "blank",
                     "stem": "Roofs planted only with sedum are described as ______ roofs "
                             "(one word).",
                     "answer": "extensive",
                     "explain": "第四段：thin 'extensive' roofs。"},
                    {"no": 6, "type": "choice",
                     "stem": "Which limitation of green roofs is mentioned in the final "
                             "paragraph?",
                     "options": ["They increase summer cooling demand",
                                 "They do not improve walls or windows",
                                 "They cannot support any insects"],
                     "answer": "B",
                     "explain": "末段：does nothing for a building's walls or windows。"},
                    {"no": 7, "type": "tfng",
                     "stem": "The writer concludes that green roofs are justified by a "
                             "combination of benefits rather than one figure.",
                     "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "T",
                     "explain": "末句：not any single number but the sum of small benefits。"},
                ],
            },
        ],
    },
    # ================= 听力 3：Section 1 体育中心办卡咨询（v1.9 原创） =================
    {
        "id": "b-listen-3",
        "subject": "listening",
        "title": "仿真 · Section 1 体育中心办卡咨询对话",
        "source": "builtin",
        "sections": [
            {
                "intro": "社区体育中心的办卡咨询电话（原创仿真）。"
                         "用页面上方播放器朗读原文作答；没有音频时也可先读题作答，提交后对照原文。",
                "material": (
                    "RECEPTIONIST: Good afternoon, Riverside Sports Centre. How can I help "
                    "you?\n"
                    "MAN: Hi, I've just moved to the area — I'm working at the hospital — "
                    "and I'd like to ask about membership.\n"
                    "RECEPTIONIST: Welcome! We have three membership types: Bronze, Silver "
                    "and Gold. Bronze is 25 pounds a month, Silver is 38, and Gold is "
                    "52.\n"
                    "MAN: Right. What's the difference between them?\n"
                    "RECEPTIONIST: Bronze covers the gym and the swimming pool during "
                    "off-peak hours — that's before nine in the morning and after two in "
                    "the afternoon on weekdays. Silver adds all-day access plus one "
                    "fitness class a week. Gold includes everything Silver has, plus the "
                    "sauna and two guest passes a month.\n"
                    "MAN: I see. I work night shifts, so mornings before nine would suit "
                    "me fine. But I'd like to bring my sister along sometimes.\n"
                    "RECEPTIONIST: Guest passes only come with Gold, I'm afraid. Visitors "
                    "can buy a day pass for 6 pounds at the front desk.\n"
                    "MAN: Fair enough. Is there a joining fee?\n"
                    "RECEPTIONIST: Normally 20 pounds, but it's waived this month as part "
                    "of our spring promotion.\n"
                    "MAN: That's good news. One more thing — I heard your pool is "
                    "closed?\n"
                    "RECEPTIONIST: Only the outdoor pool. It reopens on May the 14th "
                    "after its spring cleaning. The indoor pool is open as usual.\n"
                    "MAN: OK. And can I pay monthly, or does it have to be a year up "
                    "front?\n"
                    "RECEPTIONIST: Monthly is fine, or you can pay annually and get two "
                    "months free — annual Silver works out at 380 pounds a year.\n"
                    "MAN: Let me think… I'll start with Silver on the monthly plan, "
                    "please.\n"
                    "RECEPTIONIST: Perfect. I just need a few details. Your name?\n"
                    "MAN: David Kowalski — that's K-O-W-A-L-S-K-I.\n"
                    "RECEPTIONIST: Thank you, and a contact number?\n"
                    "MAN: 07714 552 098.\n"
                    "RECEPTIONIST: Lovely. New members also need a short induction — we "
                    "run them at 10 a.m. on Saturdays and 6 p.m. on Wednesdays.\n"
                    "MAN: Wednesday evening is better for me.\n"
                    "RECEPTIONIST: All booked in then. See you on Wednesday!"
                ),
                "questions": [
                    {"no": 1, "type": "blank",
                     "stem": "The monthly fee for Bronze membership is £______ (数字)",
                     "answer": "25",
                     "explain": "Bronze is 25 pounds a month。"},
                    {"no": 2, "type": "choice",
                     "stem": "What does Gold membership include that Silver does not?",
                     "options": ["All-day gym access",
                                 "One fitness class a week",
                                 "The sauna and monthly guest passes",
                                 "Free day passes for visitors"],
                     "answer": "C",
                     "explain": "Gold includes everything Silver has, plus the sauna and "
                                "two guest passes a month。"},
                    {"no": 3, "type": "blank",
                     "stem": "Off-peak hours are before 9 a.m. and after ______ p.m. on "
                             "weekdays. (数字)",
                     "answer": "2|two",
                     "explain": "before nine in the morning and after two in the "
                                "afternoon on weekdays。"},
                    {"no": 4, "type": "choice",
                     "stem": "How much is the joining fee this month?",
                     "options": ["£20", "£6", "It is waived this month",
                                 "It is included in the annual plan only"],
                     "answer": "C",
                     "explain": "Normally 20 pounds, but it's waived this month。"},
                    {"no": 5, "type": "blank",
                     "stem": "The outdoor pool reopens on May the ______. (数字)",
                     "answer": "14|14th|fourteenth",
                     "explain": "It reopens on May the 14th after its spring cleaning。"},
                    {"no": 6, "type": "blank",
                     "stem": "Annual Silver membership costs £______ a year. (数字)",
                     "answer": "380",
                     "explain": "annual Silver works out at 380 pounds a year。"},
                    {"no": 7, "type": "choice",
                     "stem": "Which induction session does the man choose?",
                     "options": ["Saturday 10 a.m.", "Wednesday 6 p.m.",
                                 "He will book it later", "He does not need one"],
                     "answer": "B",
                     "explain": "Wednesday evening is better for me。"},
                ],
            },
        ],
    },
    # ================= 听力 4：Section 2 图书馆新馆导览（v1.9 原创） =================
    {
        "id": "b-listen-4",
        "subject": "listening",
        "title": "仿真 · Section 2 图书馆新馆导览独白",
        "source": "builtin",
        "sections": [
            {
                "intro": "图书馆新馆开放日的导览广播（原创仿真，独白体）。"
                         "用页面上方播放器朗读原文作答；没有音频时也可先读题作答，提交后对照原文。",
                "material": (
                    "Good morning everyone, and welcome to the opening day of the "
                    "Greenford Central Library. I'm Margaret, the head librarian, and this "
                    "is your two-minute orientation tour.\n"
                    "Let's start with the layout. The ground floor is what we call the "
                    "living room of the library: newspapers, magazines, and the popular "
                    "fiction shelves, plus a café in the corner — yes, drinks with lids "
                    "are allowed everywhere in the building except the rare books room "
                    "upstairs.\n"
                    "The first floor holds the non-fiction collection and thirty reading "
                    "desks, twelve of which have power sockets and can be reserved online "
                    "for up to four hours a day. The second floor is dedicated to "
                    "children, with story time every Saturday at half past ten.\n"
                    "Now, membership. Joining is free — you need one proof of address and "
                    "photo identification. Standard members may borrow up to eight items "
                    "for three weeks. If you're a student, ask about the study pass: it "
                    "raises the limit to twelve items and extends loans to a month.\n"
                    "A word about returns. The return box by the main entrance is open "
                    "twenty-four hours — but please don't post DVDs there; the cold and "
                    "damp damage them. Bring those to the desk.\n"
                    "Finally, our opening hours: nine to seven on weekdays, nine to five "
                    "on Saturdays, and we're closed on Sundays and public holidays. "
                    "Tonight, however, we close late at nine for the opening "
                    "celebration, and everyone is welcome.\n"
                    "Enjoy the library, and do ask any of our staff if you need help."
                ),
                "questions": [
                    {"no": 1, "type": "choice",
                     "stem": "Where are drinks with lids NOT allowed?",
                     "options": ["The ground floor café", "The popular fiction shelves",
                                 "The rare books room", "The reading desks on floor one"],
                     "answer": "C",
                     "explain": "drinks with lids are allowed everywhere…except the rare "
                                "books room upstairs。"},
                    {"no": 2, "type": "blank",
                     "stem": "Reading desks on the first floor can be reserved online for "
                             "up to ______ hours a day. (数字)",
                     "answer": "4|four",
                     "explain": "can be reserved online for up to four hours a day。"},
                    {"no": 3, "type": "blank",
                     "stem": "Story time for children takes place every Saturday at "
                             "______ a.m. (时间，如 10:30)",
                     "answer": "10:30|10.30|half past ten|1030",
                     "explain": "story time every Saturday at half past ten。"},
                    {"no": 4, "type": "choice",
                     "stem": "What advantage does the student study pass offer?",
                     "options": ["Free café drinks", "A longer loan period and more items",
                                 "Access to the rare books room",
                                 "Reserved parking near the entrance"],
                     "answer": "B",
                     "explain": "raises the limit to twelve items and extends loans to a "
                                "month。"},
                    {"no": 5, "type": "tfng",
                     "stem": "DVDs may be returned through the 24-hour return box.",
                     "options": ["TRUE", "FALSE", "NOT GIVEN"], "answer": "F",
                     "explain": "please don't post DVDs there——明确禁止。"},
                    {"no": 6, "type": "blank",
                     "stem": "On opening day the library closes at ______ p.m. (数字)",
                     "answer": "9|nine|9pm",
                     "explain": "Tonight, however, we close late at nine。"}
                ],
            },
        ],
    },
]
