# -*- coding: utf-8 -*-
"""内置雅思口语话题库（原创内容，随软件分发，无版权问题）。DESIGN v2.13 / v1.15。

- SPEAK_P2：Part 2 话题卡 {id, part:2, topic, cue:[...], sample(≈180 词范文), vocab:[亮点表达]}
- SPEAK_P1：Part 1 话题组 {id, part:1, topic, qa:[{q, sample}]}
- SPEAK_P3：Part 3 深入讨论 {id, part:3, topic, qa:[{q, sample}]}
全部为原创英文内容；范文为 Band 7 风格自然口语（含连读式口语句与地道搭配）。
"""

SPEAK_P2 = [
    {
        "id": "p2-person-inspired",
        "part": 2,
        "topic": "Describe a person who has inspired you",
        "cue": ["who this person is", "how you know them",
                "what they have done", "and explain why they inspired you"],
        "sample": (
            "The person who immediately springs to mind is my high school physics "
            "teacher, Mr. Wang. He was in his fifties when I met him, and to be honest, "
            "at first glance he looked like the most ordinary teacher you could imagine — "
            "grey jacket, thermos of tea, the works. What made him remarkable was the "
            "way he treated questions. Whenever anyone asked him something, even something "
            "silly, he would stop the whole lesson and say, 'That's exactly the kind of "
            "question a scientist should ask.' That stuck with me, because up until then "
            "I'd been terrified of sounding stupid.\n\n"
            "What inspired me most wasn't his knowledge — plenty of teachers know their "
            "subject — it was his attitude towards mistakes. He kept a folder of his own "
            "failed experiment designs and showed it to us every year, saying that science "
            "runs on trial and error. Thanks to him, I stopped seeing mistakes as "
            "embarrassment and started seeing them as data. I'm doing a master's degree "
            "in engineering now, and honestly, whenever I hit a wall, I still hear his "
            "voice telling me to treat the problem as a question worth asking."),
        "vocab": ["springs to mind 立刻想起", "at first glance 乍一看", "the works 一应俱全",
                  "stick with me 让我印象深刻", "hit a wall 遇到瓶颈", "trial and error 试错"],
    },
    {
        "id": "p2-place-visit",
        "part": 2,
        "topic": "Describe a place you would like to visit in the future",
        "cue": ["where it is", "how you learned about it",
                "what you would do there", "and explain why you want to go there"],
        "sample": (
            "I've always dreamed of visiting Iceland, specifically the southern coast "
            "in winter. I first heard about it years ago from a documentary about "
            "glaciers, and since then it keeps popping up on my social media feed — "
            "apparently half the internet has been there for the waterfalls and the "
            "black sand beaches.\n\n"
            "If I ever make it there, the number one thing on my list is seeing the "
            "northern lights. I've read that you need to drive out of the city to escape "
            "light pollution, wait for a clear night, and then just stand in the freezing "
            "cold for hours — which sounds miserable and magical at the same time. Beyond "
            "that, I'd love to soak in one of the hot springs and watch the snow fall, and "
            "maybe walk on a glacier with a guide.\n\n"
            "The reason I want to go is pretty simple: I've spent my whole life in big, "
            "crowded cities, and Iceland is basically the opposite — empty, quiet, and "
            "wildly dramatic landscape. It feels like the kind of trip that resets your "
            "perspective. Also, I turn thirty in a few years, and I'd rather mark that "
            "with a memory like that than with another dinner party."),
        "vocab": ["keeps popping up 不断出现", "escape light pollution 避开光污染",
                  "miserable and magical at the same time 又苦又神奇",
                  "wildly dramatic 极为壮观", "reset your perspective 重置视角"],
    },
    {
        "id": "p2-object-important",
        "part": 2,
        "topic": "Describe an object that is important to you",
        "cue": ["what it is", "when and how you got it",
                "how you use it", "and explain why it is important to you"],
        "sample": (
            "The object I'd choose is a battered old mechanical keyboard that my father "
            "gave me when I started university. It's nothing fancy — no RGB lighting, no "
            "fancy software — just a plain grey board from the early 2000s with keys that "
            "click like a typewriter.\n\n"
            "He handed it down because he'd used it for fifteen years at his own desk, and "
            "he said something like, 'A good tool should outlive its first owner's excuses.' "
            "I've written every essay, every line of code, and every late-night job "
            "application on it since. Two of the keycaps have gone completely smooth from "
            "use, which people always comment on.\n\n"
            "It matters to me for two reasons. Practically, I just type better on it — my "
            "hands know where everything is. But emotionally, it's a small piece of my "
            "dad's work life sitting on my desk. When I'm procrastinating, I sometimes "
            "think about how many hours of his life went through those keys, and it snaps "
            "me back to work. If it ever breaks, I'll get it repaired rather than replaced. "
            "Some things earn their place."),
        "vocab": ["battered 破旧的", "hand down 传下来", "outlive 比…长久",
                  "procrastinate 拖延", "snap me back 让我回神", "earn their place 配得上位置"],
    },
    {
        "id": "p2-journey-memorable",
        "part": 2,
        "topic": "Describe a memorable journey you have taken",
        "cue": ["where you went", "who you went with",
                "what happened during the trip", "and explain why it was memorable"],
        "sample": (
            "The trip that stands out is a train journey I took with two university "
            "friends from Chengdu to Lhasa, which takes about thirty-six hours because "
            "the train climbs over the Tibetan plateau. We booked hard sleeper seats to "
            "save money, which turned out to be the best decision of the whole trip.\n\n"
            "The memorable part was the slow change of scenery. You start in humid, green "
            "Sichuan basin, and by the second morning you're above the clouds — endless "
            "grassland, yaks, and mountains with snow on them going past your window for "
            "hours. At one point the whole carriage went quiet, and a stranger across from "
            "us shared his oranges and told us stories about working on the railway "
            "itself.\n\n"
            "It was memorable partly because of the altitude — we all got slightly dizzy "
            "and giggly, which made everything funnier — but mostly because a train journey "
            "gives you time that a flight doesn't. You can't skip the boring parts, so you "
            "end up actually talking to people. When we finally stepped off in Lhasa, "
            "blinking in the thin sunlight, it felt earned. I don't think I'd remember a "
            "two-hour flight the same way."),
        "vocab": ["stands out 格外突出", "hard sleeper 硬卧", "above the clouds 云层之上",
                  "dizzy and giggly 晕乎乎地傻笑", "it felt earned 有种挣来的满足感"],
    },
    {
        "id": "p2-skill-learn",
        "part": 2,
        "topic": "Describe a skill you would like to learn",
        "cue": ["what the skill is", "how you would learn it",
                "how long you think it would take", "and explain why you want to learn it"],
        "sample": (
            "The skill on my wish list right now is cooking properly — and by that I mean "
            "actually understanding food, not just following recipes step by step. My "
            "current level is what my friends politely call 'survival cooking': three "
            "dishes I can make without setting off the smoke alarm.\n\n"
            "My plan is fairly realistic. There's a community cooking class near my "
            "university that runs on Saturday mornings, and I'd start there for the "
            "fundamentals — knife skills, how heat actually works, that kind of thing. "
            "After that, I'd pick one cuisine, probably Sichuan food since I'm from "
            "Chengdu, and cook one new dish every week for a year. My grandmother is an "
            "amazing cook, so I'd also try to get her to supervise and, more importantly, "
            "to criticise.\n\n"
            "I'd guess it takes about a year to go from clumsy to confident, and a "
            "lifetime to actually master it. The reason I want this particular skill is "
            "that cooking is one of the few skills you get to use three times a day. It "
            "saves money, it's healthier than takeout, and honestly, the idea of being "
            "the person who can casually cook a good meal for friends is very appealing "
            "to me."),
        "vocab": ["on my wish list 愿望清单上", "survival cooking 保命式做饭",
                  "set off the smoke alarm 触发烟雾报警", "fundamentals 基本功",
                  "very appealing to me 对我很有吸引力"],
    },
    {
        "id": "p2-media-impressed",
        "part": 2,
        "topic": "Describe a book or film that impressed you",
        "cue": ["what it is", "when you read or watched it",
                "what it was about", "and explain why it impressed you"],
        "sample": (
            "The film that left the deepest impression on me is an old Chinese movie "
            "called 'To Live', directed by Zhang Yimou. I watched it in my second year of "
            "university for a film club, and I went in expecting just another period drama "
            "— I came out completely changed.\n\n"
            "The story follows one ordinary family across about four decades of Chinese "
            "history. The couple lose almost everything — money, children, dignity at "
            "times — and yet the film never feels hopeless, because they just keep "
            "living. There's a scene near the end where the old couple eat a simple meal "
            "with their grandson, and nothing dramatic happens at all, but the whole "
            "cinema was silent.\n\n"
            "It impressed me for two reasons. First, the acting is astonishing — you "
            "forget you're watching actors. Second, and more importantly, it reshaped how "
            "I think about resilience. I used to think resilience meant being strong and "
            "unshakeable, but this film argues it's more like stubborn, quiet "
            "persistence — you adapt, you grieve, and then you keep going. As someone "
            "who stresses out about exams and career plans, that lesson was weirdly "
            "comforting. I've rewatched it twice since, and it hits just as hard."),
        "vocab": ["left the deepest impression 印象最深", "period drama 年代剧",
                  "reshaped how I think 重塑了想法", "unshakeable 不可动摇的",
                  "hits just as hard 依然震撼"],
    },
    {
        "id": "p2-hobby-enjoy",
        "part": 2,
        "topic": "Describe a hobby you enjoy doing",
        "cue": ["what the hobby is", "when you started it",
                "how often you do it", "and explain why you enjoy it"],
        "sample": (
            "My hobby is long-distance running — nothing competitive, just slow, "
            "steady jogging around the river near my campus. I got into it about three "
            "years ago, purely out of guilt: I'd spent my first year of university "
            "surviving on takeout and eleven-hour gaming sessions, and one day I got "
            "out of breath climbing two flights of stairs.\n\n"
            "These days I run four or five times a week, usually early in the morning "
            "before the heat and the crowds. I've worked my way up from two "
            "embarrassing kilometres to a comfortable ten, and last spring I finished "
            "my first half marathon, which I'm still unreasonably proud of.\n\n"
            "What I enjoy most is the head-clearing effect. I spend all day staring at "
            "screens — studying engineering, doing coding practice — and running is the "
            "only hour where my brain genuinely switches off. There's also a quiet "
            "social side: the same faces nod at you by the river every morning, and "
            "occasionally someone joins your pace for a kilometre or two. I know people "
            "say this about every hobby, but running really did change my routine, my "
            "sleep, and my mood. It's cheap, it's simple, and it travels with you — "
            "which makes it the perfect hobby for a student."),
        "vocab": ["out of guilt 出于愧疚", "worked my way up 逐步练到",
                  "unreasonably proud 骄傲得不讲道理", "head-clearing effect 清空大脑的效果",
                  "travels with you 走到哪带到哪"],
    },
    {
        "id": "p2-event-celebration",
        "part": 2,
        "topic": "Describe a celebration or festival you attended",
        "cue": ["what the celebration was", "when and where it took place",
                "what people did", "and explain why you enjoyed it"],
        "sample": (
            "The celebration I'd love to talk about is last Spring Festival, which I "
            "spent in my grandparents' small town in Sichuan instead of staying in the "
            "city. It took place over three days around Chinese New Year, and it's the "
            "first time in years our whole family had managed to gather in one place.\n\n"
            "What struck me was how much work goes into it. My grandmother started "
            "cooking two days early — the whole house smelled of Sichuan pepper and "
            "steamed rice cakes. On New Year's Eve, about twenty of us squeezed around "
            "three pushed-together tables for the reunion dinner, and my uncle, who "
            "lives in Shenzhen and whom I barely ever see, spent the whole evening "
            "telling embarrassing childhood stories about my father. Afterwards we set "
            "off fireworks in the courtyard, and the kids were shrieking with delight.\n\n"
            "I enjoyed it because it felt like a genuine pause. City life is all "
            "deadlines and delivery apps, but that night nobody looked at a phone for "
            "hours. It reminded me that festivals aren't really about the rituals — "
            "they're an excuse for the whole scattered family to physically be in one "
            "room. I've since decided to go back every year, because honestly, that "
            "kind of togetherness has an expiry date — my grandparents won't be around "
            "forever."),
        "vocab": ["struck me 让我感触很深", "squeezed around 挤在",
                  "shrieking with delight 尖叫着开心", "a genuine pause 真正的暂停",
                  "has an expiry date 有期限"],
    },
    {
        "id": "p2-difficult-success",
        "part": 2,
        "topic": "Describe something difficult you did successfully",
        "cue": ["what it was", "why it was difficult",
                "how you managed to do it", "and explain how you felt afterwards"],
        "sample": (
            "The hardest thing I've ever pulled off was finishing my first half "
            "marathon last spring. That might not sound dramatic to serious runners, "
            "but for me it was a genuine mountain, because eighteen months earlier I "
            "could barely jog three kilometres without stopping.\n\n"
            "The difficulty was mostly mental. Physically, a training plan solves "
            "everything — I followed a free sixteen-week schedule from a running app. "
            "But mentally, training through a Sichuan winter means getting up at six "
            "thirty in cold rain, over and over, when nobody would ever know if you "
            "skipped a day. There were weeks where I hit every target, and weeks where "
            "I managed only two runs and felt like a fraud.\n\n"
            "What got me through was making it boringly routine. I laid out my running "
            "clothes the night before, told a friend my weekly distance so I'd be "
            "embarrassed to quit, and stopped negotiating with myself at 6 a.m. — the "
            "deal was simply 'put on shoes, step outside'.\n\n"
            "Crossing the finish line, I didn't cry or anything cinematic like that — "
            "I mostly felt disbelief, and then hunger. But the confidence leaked into "
            "the rest of my life. Every time research or coursework looks impossible "
            "now, I remind myself: sixteen weeks of boring consistency beats "
            "inspiration. That's the lesson I keep."),
        "vocab": ["pulled off 成功做到", "felt like a fraud 觉得自己在装样子",
                  "boringly routine 无聊地规律化", "cinematic 电影式的",
                  "boring consistency beats inspiration 坚持胜过灵感"],
    },
    {
        "id": "p2-tech-app",
        "part": 2,
        "topic": "Describe a website or app you use a lot",
        "cue": ["what it is", "how you found it",
                "what you use it for", "and explain why you use it so much"],
        "sample": (
            "The app I'd be lost without is called Anki — it's a flashcard program "
            "built around spaced repetition, which means it shows you a card exactly "
            "before your brain is about to forget it. A friend in my study group "
            "recommended it during exam season, and I've been hooked ever since.\n\n"
            "I use it for everything that requires memorising. English vocabulary is "
            "the big one — I have a deck of about two thousand words for IELTS, with "
            "example sentences I wrote myself. I also keep decks for technical concepts "
            "from my engineering courses, and even one for cooking timings, which my "
            "friends find hilarious.\n\n"
            "What makes me use it daily is that it gamifies discipline without being "
            "childish. The app tracks a 'streak', and I'm at over four hundred days "
            "now, which I refuse to break — it takes ten minutes on the bus each "
            "morning. Compared to scrolling short videos, those ten minutes compound "
            "in a way that's genuinely visible: I can read English articles now that "
            "would have defeated me a year ago. It's not glamorous, and the interface "
            "is honestly quite dated, but it's the highest value-per-minute app on my "
            "phone, and I recommend it to every student I meet."),
        "vocab": ["be lost without 离了它不行", "spaced repetition 间隔重复",
                  "hooked 上瘾", "gamifies discipline 把自律游戏化",
                  "compound 累积放大", "value-per-minute 每分钟价值"],
    },
    {
        "id": "p2-meal-enjoyed",
        "part": 2,
        "topic": "Describe a meal you enjoyed",
        "cue": ["what the meal was", "where and when you had it",
                "who you were with", "and explain why you enjoyed it"],
        "sample": (
            "The meal that comes to mind is a hotpot dinner I had with my lab "
            "classmates right after our last brutal exam week, at a tiny hotpot place "
            "near campus that stays open until two in the morning.\n\n"
            "It was a classic Sichuan mala hotpot — the kind where the broth is so "
            "red with chilli and Sichuan pepper that newcomers get scared. There were "
            "six of us, we ordered far too much — sliced beef, lotus root, duck "
            "intestine, tofu skin, the works — and we spent about three hours cooking "
            "piece by piece in the bubbling pot and complaining about the exam that "
            "had just destroyed us.\n\n"
            "What made it special wasn't really the food, though the food was "
            "excellent. It was the timing and the company. Everyone had been living "
            "on instant noodles and stress for two weeks, and suddenly there was "
            "nowhere to rush to. By midnight the conversation had drifted from exams "
            "to completely ridiculous topics — which lab equipment we'd take to a "
            "desert island, that sort of thing — and the windows were all steamed up.\n\n"
            "I enjoyed it because it felt like a proper exhale after holding your "
            "breath for weeks. Hotpot forces you to slow down — you literally can't "
            "eat it quickly — and that night it turned six tired strangers-in-the-"
            "same-lab into actual friends."),
        "vocab": ["comes to mind 想到", "the works 一样不落", "steamed up 起雾",
                  "a proper exhale 痛快地呼一口气", "forces you to slow down 迫使你慢下来"],
    },
    {
        "id": "p2-advertisement",
        "part": 2,
        "topic": "Describe an advertisement you remember well",
        "cue": ["where you saw it", "what it was about",
                "what made it memorable", "and explain how you felt about it"],
        "sample": (
            "The advertisement I still remember is a public service film about "
            "distracted driving that played before online videos a few years ago. I "
            "must have seen it a hundred times, and I've never once skipped it.\n\n"
            "The setup is simple: it opens like a warm family vlog — a father filming "
            "his little daughter singing in the back seat, ordinary traffic, sunlight. "
            "Then his phone buzzes with a message. For a second, the frame wobbles. "
            "And then, instead of showing a crash, the film cuts to silence and a black "
            "screen that says: 'No message is worth this.' That's it. Thirty seconds, "
            "no gore, no screeching tyres.\n\n"
            "What makes it memorable is the restraint. Most adverts shout at you; this "
            "one goes quiet at exactly the moment you brace yourself for noise, and "
            "your imagination does the rest. I remember my own stomach dropping the "
            "first time, and I still catch myself putting my phone in the glove box "
            "when I'm in a car with a driving friend.\n\n"
            "I felt genuinely respectful towards the makers. It changed behaviour — "
            "mine, at least — with no product to sell, which is rare. To me it's proof "
            "that an advert can be a piece of honest filmmaking rather than just "
            "noise trying to sell you something."),
        "vocab": ["public service film 公益片", "distracted driving 分心驾驶",
                  "the frame wobbles 画面晃动", "brace yourself 做好心理准备",
                  "stomach dropping 心里一沉", "glove box 手套箱"],
    },
]

SPEAK_P1 = [
    {"id": "p1-hometown", "part": 1, "topic": "Hometown", "qa": [
        {"q": "Where is your hometown?",
         "sample": "I'm from Chengdu, a big city in southwest China — it's the capital "
                   "of Sichuan province. Most people know it for spicy food and pandas, "
                   "which is a pretty good summary, honestly."},
        {"q": "What do you like most about it?",
         "sample": "Definitely the pace of life. It's a big city with millions of "
                   "people, but people there genuinely know how to relax — tea houses "
                   "on every corner, mahjong in the afternoon. Nothing ever feels as "
                   "tense as Beijing or Shanghai."},
        {"q": "Has it changed much recently?",
         "sample": "Massively. The subway network basically tripled in the last decade, "
                   "and whole new districts have sprung up. The downside is that some "
                   "old streets I grew up around have been turned into shopping malls — "
                   "convenient, but a bit characterless."},
        {"q": "Would you like to live there in the future?",
         "sample": "Yes, quite likely. My family is there, the food is unbeatable, and "
                   "it has a growing tech industry, so career-wise it works too. I'd "
                   "say it's my default plan rather than a distant dream."}]},
    {"id": "p1-work-study", "part": 1, "topic": "Work or Study", "qa": [
        {"q": "Do you work or are you a student?",
         "sample": "I'm a first-year master's student majoring in computer science. I "
                   "spend most of my days on coursework and a small research project."},
        {"q": "Why did you choose this subject?",
         "sample": "Partly genuine interest — I like building things that work — and "
                   "partly practical reasons, since the job market for AI-related roles "
                   "is strong. It helps that the two motivations point the same way."},
        {"q": "What's the most challenging part of your studies?",
         "sample": "Reading academic papers, honestly. My first attempt at one took a "
                   "whole afternoon and I understood maybe thirty percent. It's getting "
                   "better, but the vocabulary and the density still slow me down."},
        {"q": "Do you prefer studying in the morning or evening?",
         "sample": "Morning, without question. My brain is useless after ten at night, "
                   "but at seven a.m. I can focus for hours. So I front-load my hardest "
                   "work and save routine tasks for the evening."}]},
    {"id": "p1-weather", "part": 1, "topic": "Weather", "qa": [
        {"q": "What's the weather like in your city?",
         "sample": "Chengdu is famously cloudy — we joke that seeing the sun is an "
                   "event worth posting about. Summers are humid and hot, winters are "
                   "damp and chilly, and it rarely gets extreme either way."},
        {"q": "Do you prefer hot or cold weather?",
         "sample": "Cold, easily. You can always add another layer, but there's a "
                   "limit to how much you can take off in public. Also I sleep much "
                   "better in a cool room."},
        {"q": "Does the weather affect your mood?",
         "sample": "More than I'd like to admit. A week of grey skies makes me sluggish "
                   "and unmotivated, while the first sunny day after rain puts everyone "
                   "on campus in a noticeably better mood."},
        {"q": "Do you check weather forecasts?",
         "sample": "Every single day — it's automatic now. Mostly to decide whether to "
                   "run outdoors or move my training indoors, because running in "
                   "Chengdu drizzle is miserable."}]},
    {"id": "p1-food", "part": 1, "topic": "Food and Cooking", "qa": [
        {"q": "What's your favourite food?",
         "sample": "Hotpot, no contest. It's social, it's spicy, and every person gets "
                   "to cook exactly what they like in the same pot — which somehow "
                   "avoids all the arguments about where to eat."},
        {"q": "Can you cook?",
         "sample": "At a survival level. I can manage fried rice, tomato and egg — the "
                   "classic student trio — and one pasta dish. It's functional rather "
                   "than impressive, though I'm working on it."},
        {"q": "Have your eating habits changed recently?",
         "sample": "Yes, slightly for the better. Graduate life made me realise takeout "
                   "every day is expensive and makes me sluggish, so I now cook simple "
                   "lunches a few times a week and keep takeout for social occasions."},
        {"q": "Do you like trying food from other countries?",
         "sample": "Absolutely — Japanese ramen and Thai food are my go-tos. I judge a "
                   "new city by whether I can find a decent Southeast Asian place, "
                   "which my friends think is a strange metric."}]},
    {"id": "p1-transport", "part": 1, "topic": "Transportation", "qa": [
        {"q": "How do you usually get around?",
         "sample": "Mostly the subway plus a shared bike for the last kilometre — that "
                   "combination covers ninety percent of my trips. It's cheap and "
                   "predictable, unlike the buses."},
        {"q": "How long is your daily commute?",
         "sample": "About thirty minutes each way door to door. It's long enough that I "
                   "always carry headphones, but short enough that I can't complain "
                   "seriously — friends in Beijing commute an hour and a half."},
        {"q": "Is traffic a problem in your city?",
         "sample": "Bad at rush hour, especially around the ring roads. The city's "
                   "answer has been building metro lines aggressively, which has helped, "
                   "but car ownership is still growing faster than the roads can cope."},
        {"q": "Do you think public transport will improve?",
         "sample": "Definitely. The trend is clearly positive — new lines, cleaner "
                   "electric buses, real-time apps. If anything, I worry more about "
                   "peak-hour crowding than about coverage."}]},
    {"id": "p1-free-time", "part": 1, "topic": "Free Time", "qa": [
        {"q": "What do you do in your free time?",
         "sample": "A mix of running, gaming with old friends online, and lately "
                   "reading — actual paper books, because I stare at screens all day "
                   "and my eyes demand a break."},
        {"q": "Do you prefer to spend free time alone or with others?",
         "sample": "Depends on the week. After intense coursework I recharge alone "
                   "with a run or a book; but if I've been isolated for too long, I "
                   "get restless and need people around a table."},
        {"q": "Is free time important?",
         "sample": "Crucial, and I learned it the hard way. My worst academic weeks "
                   "have always been the ones where I 'saved time' by cutting all rest "
                   "— I just became slower and grumpier. Free time is maintenance."},
        {"q": "Do people in your country have enough free time?",
         "sample": "Generally no — the work culture is intense, especially in big "
                   "cities. That said, younger people are pushing back more and "
                   "treating their evenings as non-negotiable, which I think is healthy."}]},
]

SPEAK_P3 = [
    {"id": "p3-education", "part": 3, "topic": "Education & Learning", "qa": [
        {"q": "How has technology changed the way people learn?",
         "sample": "The biggest change is access — a student in a small town can watch "
                   "the same lectures as one in a capital city. The trade-off is "
                   "attention: the same phone that delivers the lecture also delivers "
                   "fifteen notifications an hour, so self-discipline matters more "
                   "than ever."},
        {"q": "Should schools teach practical skills like cooking or finance?",
         "sample": "I'd say yes, with a caveat. Schools can't teach everything, but "
                   "tax forms and compound interest will affect everyone's life, while "
                   "some content we force students through won't. A basic 'life "
                   "operations' module would pay for itself quickly."},
        {"q": "Do you think exams are a fair way to assess students?",
         "sample": "They're fair in one narrow sense — everyone faces the same paper — "
                   "but they reward a specific skill: performing under time pressure. "
                   "Coursework captures steady effort better. Honestly, a blend of the "
                   "two is the least unfair system anyone has invented so far."},
        {"q": "Will teachers be replaced by AI in the future?",
         "sample": "Replaced, no; reshaped, certainly. AI can explain a concept "
                   "infinitely patiently, but teaching is also motivation, spotting why "
                   "a student is stuck, and the social experience of learning together. "
                   "The teachers who combine those human skills with AI tools will "
                   "thrive; the ones who only recite, less so."}]},
    {"id": "p3-technology", "part": 3, "topic": "Technology & Daily Life", "qa": [
        {"q": "Do people rely too much on smartphones?",
         "sample": "Probably, though 'too much' is doing a lot of work in that "
                   "sentence. The phone replaced a camera, a map, a wallet, and a "
                   "library — of course we hold it constantly. The real problem is "
                   "specific apps engineered to eat attention, not the device itself."},
        {"q": "Are older people excluded by new technology?",
         "sample": "Often, and unnecessarily so. When a hospital appointment requires "
                   "an app and a QR code, the barrier isn't intelligence, it's design "
                   "arrogance. The encouraging part is that after the pandemic, even "
                   "my grandparents learned video calls — they adapt when the "
                   "interface respects them."},
        {"q": "How will AI change everyday life in the next ten years?",
         "sample": "Invisibly, mostly — like electricity did. The interesting shift "
                   "is from tools you operate to assistants you delegate to: drafting "
                   "documents, handling paperwork, tutoring kids. The open question is "
                   "who benefits — if it mainly boosts professionals, the gap widens."},
        {"q": "Should there be limits on screen time for children?",
         "sample": "Limits, yes; bans, no. Children need to learn digital habits the "
                   "same way they learn to eat — with structure, not prohibition. The "
                   "parents' own phone use matters more than any rule, because kids "
                   "copy what they see, not what they're told."}]},
    {"id": "p3-environment", "part": 3, "topic": "Environment & Cities", "qa": [
        {"q": "Who is most responsible for environmental problems — individuals, companies, or governments?",
         "sample": "In order of leverage: governments, then companies, then "
                   "individuals. One regulation on packaging beats a million personal "
                   "virtues. That said, individual choices create the political demand "
                   "that makes strong regulation possible, so the categories work "
                   "together rather than compete."},
        {"q": "What can cities do to become greener?",
         "sample": "The boring interventions are the powerful ones: dense metro "
                   "networks, protected bike lanes, and trees — actual trees, which "
                   "lower street temperature by several degrees. Chengdu's park ring "
                   "around the city is a good example of doing this at scale."},
        {"q": "Is economic growth compatible with protecting the environment?",
         "sample": "It used to look like a trade-off, but the picture has changed — "
                   "solar and wind are now the cheapest power in many places, so "
                   "growth and emissions are finally decoupling in some economies. The "
                   "harder question is whether it happens fast enough, not whether "
                   "it's possible."},
        {"q": "Do you think people will change their lifestyles for the environment?",
         "sample": "Slowly, and only when the green option is also the convenient or "
                   "cheap one. Recycling caught on where bins were everywhere; electric "
                   "scooters exploded because they're fun. Moral appeals alone have a "
                   "poor track record — design beats lectures."}]},
    {"id": "p3-society", "part": 3, "topic": "Society & Modern Life", "qa": [
        {"q": "Why do more young people live alone nowadays?",
         "sample": "Several forces at once: careers pull people to big cities away "
                   "from family, marrying later is socially acceptable now, and — "
                   "crucially — small apartments make solo living economically "
                   "possible. It's less a rebellion than a set of practical defaults."},
        {"q": "Is social media making people less social in real life?",
         "sample": "It reshapes rather than reduces sociability. I've kept closer to "
                   "old classmates through group chats than any previous generation "
                   "could. But there's a real cost at the shallow end: sitting in a "
                   "room where everyone scrolls isn't the same as being together."},
        {"q": "Should companies allow flexible working?",
         "sample": "Where the work permits it, yes — three years of remote experiments "
                   "proved most jobs don't need a fixed desk. The nuance is that "
                   "junior employees lose a lot from missing casual learning around "
                   "them, so a hybrid pattern probably serves them better than "
                   "full remote."},
        {"q": "How can people maintain a work-life balance?",
         "sample": "Mostly by drawing lines the technology can't erase for you — a "
                   "hard finish time, notifications off after dinner. Balance rarely "
                   "happens by accident; it's a set of small policies you enforce on "
                   "yourself before the calendar enforces its own."}]},
]
