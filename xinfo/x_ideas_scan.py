#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X 创意雷达 - RSS 版本
纯 Python 标准库实现，零外部依赖
"""

import urllib.request
import xml.etree.ElementTree as ET
import json
import os
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import sys
import re

# ============================================================================
# 配置区
# ============================================================================

# 要监控的 X 账号列表
TARGET_ACCOUNTS = [
    # ── 原有账号 ──────────────────────────────────────────────
    "dashen_wang",       # AI最严厉的父亲，技术架构师，研究 AI 自动化与人类行为
    "xingpt",            # XinGPT，AI 干货与个人成长分享
    "skyfree14242454",   # sky_AI，2026年从头学习 AI 的创业者
    "linxiaobei888",     # xiaobeiLin(小北)，软件工程，关注 AI Coding
    "zarazhangrui",      # 原有账号
    "op7418",            # 原有账号
    "dtnewsai",          # 原有账号
    #"joanrod_ai",# 原有账号  ← 移除 2026-03-11
    #"samruddhi_mokal",# 原有账号  ← 移除 2026-03-19
    #"stuffyokodraws",# 原有账号  ← 移除 2026-03-11
    # ── AI 领袖 / 研究员 ──────────────────────────────────────
    "AndrewYNg",         # Andrew Ng，Coursera 联合创始人，斯坦福教授，前百度/谷歌大脑负责人
    "xiao_ted",          # Ted Xiao，Google DeepMind 创始成员，关注物理 AGI
    "sama",              # Sam Altman，OpenAI 首席执行官
    "janleike",          # Jan Leike，Anthropic AI 对齐负责人，前 OpenAI 核心成员
    "JeffDean",          # Jeff Dean，Google DeepMind 首席科学家
    "cstanley",          # Christopher Stanley，SpaceX/X/xAI 安全工程专家
    "KarelDoostrlnck",   # Karel，OpenAI 研究员，专注后训练阶段
    "jackclarkSF",       # Jack Clark，Anthropic 联合创始人，OECD AI 专家
    "ilyasut",           # Ilya Sutskever，SSI 创始人，前 OpenAI 首席科学家
    "miramurati",        # Mira Murati，前 OpenAI CTO
    "ylecun",           # Yann LeCun，暂时移除（nitter 持续无法抓取）
    "karpathy",          # Andrej Karpathy，前 OpenAI/Tesla AI 负责人
    "gdb",               # Greg Brockman，OpenAI 总裁
    "demishassabis",# Demis Hassabis，Google DeepMind CEO
    # ── 科技名人 / 投资人 ─────────────────────────────────────
    "lexfridman",        # Lex Fridman，知名播客主持人，MIT AI 研究员
    "pmarca",            # Marc Andreessen，a16z 联合创始人，著名风险投资人
    "paulg",             # Paul Graham，Y Combinator 联合创始人
    "naval",             # Naval，AngelList 创始人，关注 AI 与硅谷哲学
    "VitalikButerin",    # Vitalik Buterin，以太坊创始人，常发表 AI 安全/对齐深刻见解
    "jack",# Jack Dorsey，前 Twitter CEO，现专注于去中心化 AI 协议
    "BillGates",         # Bill Gates，比尔·盖茨，长期撰写 AI 产业转型观察
    "tim_cook",          # Tim Cook，Apple 首席执行官
    "NateSilver538",     # Nate Silver，数据分析大神，关注预测模型与 AI
    # ── 创业者 / 独立开发者 ───────────────────────────────────
    "bramk",             # Bram，独立开发者，AI 提示词专家
    "haoshanhong",       # Haoshan Hong，Fluentide CEO，清华苏世民学者
    #"lqiao",# Lin Qiao，Fireworks AI 创始人兼 CEO  ← 移除 2026-03-11
    "byCanen",           # Canen，AI 工具开发者，aitoolfinder.org 负责人
    "SamuelBeek",        # sam，VEED (AI 视频编辑) CPO
    #"UncleJAI",         # Uncle J，移除（原创率低，发推稀少）
    "nateliason",        # Nat Eliason，打造 Felix Craft AI "零人公司"
    "GoSailGlobal",      # Jason Zhu，独立开发，AI SaaS 出海及内容分享
    #"alex_mikhalev",    # Dr Alexander Mikhalev，移除（原创率 15%，内容稀少）
    "levinomad",         # Levi Yuan，出海 AI 应用开发者，数字游民
    "Jacobsklug",        # Jacob Klug，creme.digital 联合创始人，用 AI 构建软件
    "alexcooldev",       # Alex Nguyen，独立黑客，开发多款 AI 原生应用
    "TheGeorgePu",       # George Pu，独立创业者，构建 AI 无法替代的产品
    "0xTab",             # Tabish，OpenSpec (YC W26) 创始人
    "mickeyumythy",      # Umythy，关注产品开发与 AI 创业
    "onenewbite",        # 一口新饭，MoneyXYZ 创始人，关注科技与投资
    #"elvissun",         # Elvis，移除（仅 2 条原创，数据太少）
    #"categoryx",        # Simon Rowe，移除（零原创，全为转推）
    # ── 中文 AI 观察者 ────────────────────────────────────────
    "kuaidaoqingyi",     # 快刀青衣，得到联合创始人，AI 爱好者与观察者
    "AYi_AInotes",       # 阿绎 AYi，AIGC 实践者，擅长 AI 信息提纯
    "onehopeA9",         # OneHopeA9，链上玩家，致力于让 AI 为其工作
    "xiangxiang103",     # 雨哥向前冲，AI 投资者，实研关隘模型创始人
    "yinmin1987",        # 尹珉，Linux 基金会布道师，《LangGraph实战》编著
    "AISuperDomain",     # AI超元域，AI 深度观察与资讯分享
    # ── 其他技术 / Web3 ──────────────────────────────────────
    #"fabioivsantos",    # Fabio Pauli，移除（最新推文 2025-06，停更 9 个月）
    "xqliu",             # Larry & Leo & Lucky，资深开发者，关注交易与 AI 应用
    #"ToanTruong_",      # Toan Truong，移除（零数据，nitter 抓取失败）
    "lansification",     # LAN，研究游戏化体验与 AI 社区
    "Mehedi_Crypto1",    # Mehedi，Web3 分析师，关注 AI 数据价值
    "madsf88",           # Mads，学习"氛围编码（Vibe Code）"的开发者
    "dov_wo",            # Dov，Mango Labs 创始人，AI 与 Crypto 交叉研究
    #"JanErik7117",       # Jan Erik Syverød，AI 技术关注者
    #"DanAcosta",        # Daniel Acosta，移除（停更至 2022 年）
    #"cc202201",         # CC，移除（零数据，nitter 抓取失败）
    #"lake_delores14",   # Delores，移除（零数据，nitter 抓取失败）
    #"Xking332",         # X，移除（零数据，nitter 抓取失败）
    #"QuiverAI",# AI数据分析，周报推荐  ← 移除 2026-03-04
    "xn1cklas",  # 多源推荐，值得关注的技术创作者
    "camworboys",  # 来自 @jack 推荐的优质账号
    "FelixCraftAI",  # @nateliason 推荐的 AI 工具专家
    "OpenAI",  # @ilyasut、@sama 联合推荐的官方账号
    "AnthropicAI",  # @jackclarkSF 推荐的 AI 研究前沿
    "arcprize",  # @demishassabis、@xiao_ted 推荐的 AI 竞赛平台
    "Saboo_Shubham_",  # AI Core & Research
    "LiorOnAI",  # AI Core & Research
    "gan_chuang",  # AI Core & Research
    "mntruell",  # AI Core & Research
    "claudeai",  # AI Core & Research
    "_arohan_",  # AI Core & Research
    # ── 从人物分类文档自动导入 & 分类 (2026-03-24) ──────────────────
    # 1. AI 核心人物与机构 (AI Core & Research)
    "HuaWenyue31539",    # Wenyue Hua，KAUST AI Rising Star LLM-based agent, LLM reasoning
    "jocarrasqueira",    # Joana Carrasqueira，former Head of DevRel ｜ Pharma scientist & MBA turned tec...
    "feiliu_nlp",        # Fei Liu，Working on large language models, LLM inference, reasonin...
    "bindureddy",        # Bindu Reddy，the world’s first AI super assistant and general-purpose ...
    "GeminiApp",         # Google Gemini，The Gemini app turns research into reality, bringing fron...
    "NotebookLM",        # NotebookLM，Think smarter, not harder. Meet your brain's new best friend
    "GoogleLabs",        # Google Labs，Google’s home for our latest AI tools and experiments.
    "YuXiang_IRVL",      # Yu Xiang，Ex- research scientist
    "Arminn_Ai",         # ΛRMIN ｜ AI，CPP Higgsfield • Topaz Labs
    "NliGjvJbycSeD6t",   # Yinhuai，PhD@HKUST｜Humanoid, Manipulation, CV
    "deepseek_ai",       # DeepSeek，Unravel the mystery of AGI with curiosity. Answer the ess...
    "ElevenLabs",        # ElevenLabs，AI research and products that transform how we interact w...
    "pirroh",            # Michele Catasta，President & Head of AI
    "OpenAINewsroom",    # OpenAI Newsroom，Tweets are on the record. If you like this account, you’l...
    #"huggingface",# Hugging Face，The AI community building the future.  ← 移除 2026-03-25
    "BradSchoenfeld",    # Brad Schoenfeld, PhD，Researcher/educator on muscle building and fat loss. Auth...
    "grok",              # Grok
    "johnschulman2",     # John Schulman，Interested in reinforcement learning, alignment, birds, j...
    "PyTorch",           # PyTorch，Tensors and neural networks in Python with strong hardwar...
    "GoogleDeepMind",    # Google DeepMind，We’re a team of scientists, engineers, ethicists and more...
    "xai",               # xAI
    "AIatMeta",          # AI at Meta，Together with the AI community, we are pushing the bounda...
    "GoogleAI",          # Google AI，Making AI helpful for everyone. Show thinking ↓
    "elonmusk",          # Elon Musk
    # 2. AI 工具与辅助开发 (AI Tools & Coding Agents)
    "danese60920",       # OpenClaw ｜｜ SUPPORT ✪，The Al that does things. Emails, calendar, home automatio...
    "searchcloudone",    # Search Cloud One，We love everything in the cloud - the sky is not the limit
    "openclaw",          # OpenClaw，The AI that does things. Emails, calendar, home automatio...
    "steipete",          # Peter Steinberger，Polyagentmorous ClawFather. Came back from retirement to ...
    "moltbook",          # moltbook，Where openclaw bots, clawdbots, and AI agents of any kind...
    "zhiheng_huang",     # ZH Huang，｜ AI agents for real work ｜
    "posthog",           # PostHog，How developers build successful products. Hedgehog enthus...
    "turborepo",         # Turborepo
    "typelessdotcom",    # Typeless，Voice = Superpowers ｜ Founder & CEO
    "XEng",              # Engineering，updates from our engineering team
    "frankdilo",         # Francesco Di Lorenzo，the AI-powered social media scheduler.
    "arisberikut",       # Aris Cursor，Open to project Teacher Bootcamp Vibe coder Next.js + GoL...
    "opencode",          # OpenCode，The open source coding agent
    "indie_maker_fox",   # Fox@MkSaaS.com，Directory boilerplate：
    "Zread_ai",          # Zread.AI，Let the repo talk. For AI builders and human developers.
    "ProductHunt",       # Product Hunt，Get new products in your inbox:
    "godofprompt",       # God of Prompt，Sharing AI Prompts, Tips & Tricks. The Biggest Collection...
    "JermicX",           # Jermic 𝕏 ，正在做：AIART - AI 提示词灵感库、PicSeed - 灵感收集助手
    #"raindesign007",# Rain，Vibe Coding，UX/UI，ProductDesign，AI  ← 移除 2026-03-25
    "woshi_ai",          # WOSHI，Discover AI prompts .
    "ReflctWillie",      # willie，Node Banana, easypeasyease Lnkdn:
    "CodeByPoonam",      # Poonam Soni，Post about everything latest in AI ｜ Founder: AI Toast｜ D...
    "googleaidevs",      # Google AI Developers，AI for every developer. So what will you build?
    "folo_is",           # Folo，Follow everything in one place. Join our community:
    #"cline",# Cline，We turn your inference into production code.  ← 移除 2026-03-25
    "cursor_ai",         # Cursor，The best way to code with AI.
    "MindBranches",      # MindBranches，AI enhanced diagrams to help you understand complex conce...
    "Tesla",             # Tesla，Electric vehicles, giant batteries & solar, AI & robotics
    "tripoai",           # Tripo，The only one you need to follow for 3D and AI. ｜ Webapp:
    "skirano",           # Pietro Schirano，Creator of Claude Engineer, DesignerGPT, Sequential think...
    "github",            # GitHub，The AI-powered developer platform to build, scale, and de...
    "Replit",            # Replit ⠕，Idea to app, fast. Create beautiful, modern web applicati...
    "oran_ge",           # Orange AI，CEO of MarsWave. Build for Agents, by Agents.
    "pmndrs",            # Poimandres，A developer collective building open tools for the creati...
    "OpenAIDevs",        # OpenAI Developers，Official updates for developers building with Codex & the...
    "googledevs",        # Google for Developers，Discover the latest developer tools, resources, events, a...
    "readwise",          # Readwise，Save your best highlights from Kindle, Twitter, Pocket, I...
    "Microsoft",         # Microsoft，We're on a mission to empower every person and every orga...
    # 3. 独立开发者与 AI 实战派 (Indie Hackers & AI Practitioners)
    "akokoi1",           # WY，大龄程序员，前搜狐员工，Golang、PHP、JavaScript、Dart、Swift开发，多年国际外包经验，全...
    "EvanLing888",       # Aria Ling，Linglish CEO ｜ AI重构沉浸式英语学习，让每一次输入都变成可衡量的成长。AI在改变世界；拒绝鸡汤，只...
    "huangyun_122",      # 黄赟，Every great AI journey starts with a single Prompt vx: hu...
    "fankaishuoai",      # 范凯说 AI ｜ AI Insights，从互联网创业走到 AI 时代。 分享趋势判断、转型框架与落地实践：内容创作、AI 产品、个人 IP、超级个体。 W...
    "Hesamation",        # ℏεsam，ai/ml • giving birth to agents in my spare time
    "irabukht",          # Ira Bodnar，building AI agent for paid ads at
    "gregisenberg",      # GREG ISENBERG，we build companies like
    "solzen77",          # Solzen77，Solana, Polymarket, BNB Bot developer
    "clockmeta",         # Clock，systems builder // shadow_clone_jutsu
    "0xFortuneRust",     # FortuneRust，WebSite, Mobile, Game, Blockchain developer
    "mbaddar2",          # Moh Baddar，Help SMEs Build Cost Efficient AI Solutions ｜ AI Engineer...
    "jiayuan_jy",        # Jiayuan (JY) Zhang，Building something new. Founder & CEO of
    "suresh_manian",     # Resh，AI First Enthusiast ｜ Physics & CS @ CMU, MSAI @ Northeas...
    "1khanfarrukh",      # FARRUKH KHAN，Founder & CEO Inference Analytics, building AI for sensit...
    "yanhua1010",        # Yanhua，AI Solopreneur · Creator · Growth
    "aehyok",            # AI少年，全栈独立开发者，CEO， 喜欢编程和爱折腾AI 我的个人网站：
    "zstmfhy",           # AI奶爸，技术不该高冷，创作可以很暖 合作：ZST321456
    "YukerX",            # Yuker，RUC '24 ｜ Law Student ｜ Musician ｜ Researcher ｜ Builder ｜...
    "heyshrutimishra",   # Shruti，Reality is programmable ｜ Building digital leverage w/ AI...
    "Wasay6797",         # Wasay Ali，Digital Consultant ｜ Helping Businesses Scale with Custom...
    "tomkrcha",          # Tom Krcha，Chief Vibe Officer at
    "VRR8DEoGXu9vsXQ",   # 小桂
    "LuizaJarovsky",     # Luiza Jarovsky, PhD，Co-founder of the AI, Tech & Privacy Academy (1,400+ part...
    "ben_m_somers",      # Ben Somers，Tweeting about education & Building
    "averycode",         # Avery，psychology grad turned software engineer, ex apple/hubspot
    "PMbackttfuture",    # AI产品黄叔，两家大厂AI产品顾问 加社团学skills：
    "AlchainHust",       # 花叔，小红书：花叔（只工作不上班版 公众号：花叔 即刻：Alchian花生
    "H0wie_Xu",          # Howie Xu，Chief AI Officer @ Gen, Lecturer at Stanford ｜ ex SVP of ...
    "KintuLabs",         # Chris Osborne，i like to build things
    "OnlyXuanwo",        # Xuanwo，PMC Chair. VISION: Data Freedom. Working on
    "WhileTravelling",   # Evrim Kanbur，Shanghai 14 years and counting. Teaching at Shanghai Jiao...
    "NeuraNova9",        # Audrey Crews，First women with Neuralink BCI, Thought-controlled creato...
    "maddiedreese",      # Maddie D. Reese，Learning! Doesn’t know how to code. 4x hackathon winner a...
    "eliana_jordan",     # Eliana，Just a dive instructor who learned to code ｜｜
    "ityouknows",        # 纯洁的微笑，AI 跨境电商：单店营收破万，自营近 10 家店，探索出海放大中
    "MersonVoice",       # 莫森 ｜ 破局哥，关注我 跟上破局哥的节奏！ 公司业务｜社群交流｜个人VX｜在网站
    "jimmyjiangYEZ",     # Jimmy Jiang，Ex-Big Tech (EU & US)
    "IndieDevHailey",    # 开发者Hailey，独立开发者 · AIGC 实践派 AI × 全栈｜只做能跑的产品 PixTribe：灵感 → 作品 → 变现平台 ...
    "dynamicwangs",      # DynamicWang，Choreographer｜VisualArtist｜Photographer｜Composer｜AWPlanet...
    "swyx",              # swyx，achieve ambition with intentionality, intensity, integrit...
    "lennysan",          # Lenny Rachitsky，Deeply researched product, growth, and career advice
    "rileybrown",        # Riley Brown，(the #1 full stack vibe coding platform)
    "lulumeservey",      # Lulu Cheng Meservey，Rostra founder, Shopify board, ex Activision & Substack, ...
    "PJaccetturo",       # PJ Ace，- 300M+ Views ｜ Featured in Variety, Hollywood Reporter. ...
    "enggirlfriend",     # Engineer Girlfriend，working on AI, the fun kind
    "ayaboch",           # Aya Bochman，⋅ software developer ⋅ bootstrapping to $1M ARR ⋅ I love ...
    "Sutoscience",       # Amy Suto ｜  Founder & Bestselling Author，with 30,000+ subscribers
    "stijnnoorman",      # Stijn Noorman，Helping you grow your X business. Tweets on writing, busi...
    "yupi996",           # 程序员鱼皮，项目狂魔，10+上线产品，GitHub 20k+ followers
    "YanXing_newone",    # Thinker
    "hrswatigupta",      # Swati Gupta，350K+ Audience on LinkedIn ｜ AI Content Creator ｜ Resume ...
    "craftian_keskin",   # Keskin，Midjourney, AI, Video Games. Love exploring new Midjourne...
    "xiaohu",            # 小互，带你了解全球最前沿科技、AI动态... 学AI找小互，找小互，上
    "ttmouse",           # ttmouse - 豆爸，“AI快崛醒了，赶紧给AI打工” ——我认真的 腾讯阿里十年设计 + 六年六赛道产品 第三个十年：不卷人，卷AI ...
    "servasyy_ai",       # huangserva，古早程序员 ｜ AI出海 ｜ 自由职业 机车游侠&机速购&骑享租创始人 15年前 freelance 起步 → 连...
    "hx831126",          # 虎小象，不过是 Prompt Kiddide 罢了
    "shellywangcat",     # Shelly，AI 探索 ，币圈摸鱼 很爱买锅跟做饭，INFJ 网络话痨 0 市场预算实现 1500 万用户 跑过百亿交易额 分...
    "kat_kampf",         # kat kampf，• she/her • views and subpar jokes are my own
    "guishou_56",        # Niko，分享$0 → $10000/月的技术创业之路 公众号：Niko的出海记录
    "tomosman",          # Tom Osman，Exploring what's possible with technology ｜ Initiator of
    "iX00AI",            # iX，AI Video Creator ｜ Higgsfield Official Evangelist ｜ Found...
    "brad_zhang2024",    # 烟花老师，AI 社区【一支烟花】 发起人， AI 应用架构师，分享深度 AI 内容，链接 AI 创业者
    "shesjuliez",        # Julie Zhu，Design Lead @. Previously Senior Designer @ Alibaba. Poli...
    "qin_ue",            # QinUE，Former Creative Director ｜ Now AI slave
    "songguoxiansen",    # 松果先森，微信公众号：松果先森，扣666进AI群 AI交流TG群：
    "Astronaut_1216",    # Zephyr.在思考丨阿杭杭杭，公开我的AI时代创业思考，保持分享、快速迭代、谦逊求教、日日精进
    "gkxspace",          # 余温，AI 产品构建 & AI 商业化方案 & 企业 AI 转型
    "Suryansh777777",    # Suryansh Chourasia，- a photo studio designed for creators and brands who wan...
    "Linkc",             # 陈言Linkc-Chen，自媒体副业，3个月变现10w+，一年做到小红书AI赛道头部。
    "YouMind_AI",        # YouMind，Learn smarter. Create bolder.
    "MANISH1027512",     # 古一，正在孵化一个有温度又硬核的 AIGC 创作者社区
    "JundeMorsenWu",     # JUNDE WU，Founder of Panoptes (acq.
    "msjiaozhu",         # MapleShaw，Daily experiments, hacks & builds ｜ 把 AI 玩得越来越野
    "austinit",          # Austin，一个程序员，通过开发产品和投资赚钱。编程段子居多，请勿特别当真。
    "caizhenghai",       # forecho，8 年美股投资者，13 年程序开发。 - 联系我：
    "shaunrein",         # Shaun Rein，Founder of The China Market Research Group (CMR). Author ...
    "Navalquot",         # Naval Ravikant Bot ｜ Navalism，Sharing Naval Ravikant quotes. Fan page, not affiliated. ...
    "QuotesOfNaval",     # Naval Ravikant Quotes
    "shizhiang1",        # Eric 在搞钱
    "_FORAB",            # AB Kuai.Dong，热爱研究、热爱家庭、热爱分享，2016 年入行从业。
    "howie_serious",     # howie.serious，purity of thought. be exactly who you are : just a seriou...
    "wshuyi",            # Wang Shuyi，Teach AI for Science on
    "MatthewBerman",     # Matthew Berman，Building Forward Future. YouTuber, Angel Investor, Develo...
    "atulkumarzz",       # Atul Kumar，Influencer Marketing biz: atulhx@gmail.com -
    "dotey",             # 宝玉，Prompt Engineer, dedicated to learning and disseminating ...
    "0xCheshire",        # 柴郡｜Crypto+AI Plus，你要更相信你自己！ 商务合作 ｜ 联系我：
    "samuraipreneur",    # The SamurAI，using ai to scale and to get more done in less time this ...
    "PandaTalk8",        # Mr Panda，程序员 ｜ AI 创业者 ｜ 个人IP教练 ｜ 商业技术观察 ｜ 公众号：PandaTalk8
    "DareFailed",        # James Steinberg，30u30 Acquired YC Founder:
    "starzq",            # Star@Day1Global Podcast，Top Podcast on AI, Robotics, Crypto ｜ ex Alibaba, Douban
    "RuiHuang_art",      # Rui Huang，：stellaxis.info@gmail.com
    "minchoi",           # Min Choi，Building with AI. Sharing what's wild, what's practical, ...
    "amasad",            # Amjad Masad
    "chrisboettcher9",   # Chris Boettcher，Helping Men and Women over 40 lose 15-150 lbs and resolve...
    "henuwangkai",       # henu王凯，Chrome 插件市场可安装「松鼠快看」插件版本 微信：wangkaisv
    "Gorden_Sun",        # Gorden Sun，只发AI相关信息，个人维护的AI资讯日报（已连续日更3年）
    "sairahul1",         # Rahul
    "mortenjust",        # Morten Just，I post stuff you can try and talk about products.
    "nealtaparia",       # Neal Taparia，Entrepreneur & Investor ｜ I discuss working less and doin...
    "punk2898",          # Punk（2898 ），Vibe Coding Enthusiast ｜定居新加坡
    "FinanceYF5",        # AI Will，增长顾问 ｜ AI行业分析师，Learn in Public
    "heyrobinai",        # Robin Delta，I help you make money & get more work done with AI tools
    "AlphaSchoolATX",    # Alpha，Our students love school, learn 2X fast, and learn life s...
    "ecomEddie",         # EDDIE CHENG，(growth agency for DTC)
    "thsottiaux",  # 优先关注，AI 研究方向
    "thdxr",  # 开发工具方向
    "sundarpichai",  # Google 战略动向
    "satyanadella",  # Microsoft 官方背书，Azure AI 动态
    "OfficialLoganK",  # 顶级 AI 研究者背书
    "petergyang",  # 产品/创业视角
    "garrytan",  # YC/创业生态核心节点
    "mustafasuleyman",  # Microsoft AI 负责人
    "aakashgupta",  # 多圈层共振，信号强
    "doganuraldesign",  # xAI 生态设计方向
]

# nitter 实例列表（多实例 fallback）
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
]

# RSSHub 实例列表（Nitter 全部失败后的备用数据源）
# RSSHub 路由: /twitter/user/:username
RSSHUB_INSTANCES = [
    "https://rsshub.pseudoyu.com",
]

# 文件路径（相对于脚本所在目录）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "log")
DAY_LOG_DIR = os.path.join(LOG_DIR, "day")   # 每日持久化日志目录
IDEAS_FILE = os.path.join(LOG_DIR, "ideas.md")
SEEN_FILE = os.path.join(LOG_DIR, ".ideas_seen.json")

# 配置参数
MAX_RETRIES = 2          # 每个实例的重试次数
SEEN_URLS_LIMIT = 5000   # seen.json 最大记录数（FIFO）
KEEP_DAYS = 5            # ideas.md 保留天数
INSTANCE_COOLDOWN = 90   # 实例失败后的冷却时间（秒），冷却后自动恢复
MAX_PER_ACCOUNT = 5      # 每个账号最多保留的推文数

# 并发配置
CONCURRENT_PER_INSTANCE = 2   # 每个 Nitter 实例的最大并发请求数
JITTER_MIN = 0.8              # 请求间最小随机延迟（秒）
JITTER_MAX = 2.5              # 请求间最大随机延迟（秒）
MAX_WORKERS = 2#CONCURRENT_PER_INSTANCE * (len(NITTER_INSTANCES) + len(RSSHUB_INSTANCES))

# User-Agent 池（轮换以降低被识别风险）
_UA_POOL = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
]

# 每个实例的信号量 — 模块加载时预初始化，避免懒初始化竞争
_instance_semaphores: dict = {
    inst: threading.Semaphore(CONCURRENT_PER_INSTANCE)
    for inst in NITTER_INSTANCES + RSSHUB_INSTANCES
}

# 日志文件写入锁（多线程并发时防止日志行交错）
_log_lock = threading.Lock()

# ============================================================================
# 工具函数
# ============================================================================

def ensure_dirs():
    """确保必要的目录存在"""
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(DAY_LOG_DIR, exist_ok=True)

# 当天日志文件路径（延迟求值，ensure_dirs 后才有效）
def _day_log_path():
    return os.path.join(DAY_LOG_DIR, datetime.now().strftime('%Y-%m-%d') + '.log')


def _day_result_path():
    return os.path.join(DAY_LOG_DIR, datetime.now().strftime('%Y-%m-%d') + '_result.json')

def log(msg, level='INFO'):
    """追加一行到当天日志文件（线程安全，同时打印到 stdout）"""
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"[{ts}] [{level}] {msg}"
    with _log_lock:
        print(line)
        try:
            with open(_day_log_path(), 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except Exception:
            pass  # 日志写失败不影响主流程

def strip_html(text):
    """剥离 HTML 标签，返回纯文本"""
    if not text:
        return ""
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#39;', "'", text)
    # 清理噪音
    text = re.sub(r'https?://nitter\.[^\s]+', '', text)
    text = re.sub(r'\bVideo\b', '', text)
    text = re.sub(r'\bImage\b', '', text)
    text = re.sub(r'\u2014\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def strip_emoji(text):
    """移除所有 emoji 字符，保留纯文本"""
    if not text:
        return ""
    # 移除常见 emoji 范围
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"   # 表情
        "\U0001F300-\U0001F5FF"   # 符号和图标
        "\U0001F680-\U0001F6FF"   # 交通和地图
        "\U0001F1E0-\U0001F1FF"   # 国旗
        "\U00002702-\U000027B0"   # 其他符号
        "\U0001F900-\U0001F9FF"   # 补充 emoji
        "\U0001FA00-\U0001FA6F"   # 棋类/扩展
        "\U0001FA70-\U0001FAFF"   # 更多扩展
        "\U00002600-\U000026FF"   # 杂项符号
        "\U0000FE00-\U0000FE0F"   # 变体选择符
        "\U0000200D"              # ZWJ
        "\U00002B50"              # 星星
        "\U0000231A-\U0000231B"   # 手表
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)
    text = re.sub(r'\s{2,}', ' ', text)  # 压缩多余空格
    return text.strip()

def _is_useful_title(title):
    """判断标题是否有信息量"""
    clean = title.strip().lower()
    if not clean:
        return False
    if clean in ('image', 'video', '推文'):
        return False
    # 纯链接标题：x.com/i/article/...
    if re.match(r'^https?://', clean) or re.match(r'^x\.com/', clean):
        return False
    return True

def _classify_type(title):
    """根据标题判断推文类型"""
    if title.startswith('RT ') or title.startswith('RT by @'):
        return 'rt'
    if title.startswith('R to @'):
        return 'reply'
    if title.startswith('Pinned:'):
        return 'pinned'
    return 'original'

def _extract_original_author(link):
    """从 URL 中提取原始作者用户名"""
    # https://x.com/someuser/status/123#m
    match = re.match(r'https?://x\.com/([^/]+)/', link)
    if match:
        return match.group(1)
    return ''

def _extract_summary(title, description):
    """从 description 提取有效摘要（去重、去噪、单行）"""
    clean_desc = strip_html(description)
    clean_desc = strip_emoji(clean_desc)
    if not clean_desc:
        return ""
    
    # description 和 title 内容去重
    title_clean = strip_emoji(title).strip()
    title_norm = title_clean[:60]
    if title_norm and clean_desc.startswith(title_norm):
        extra = clean_desc[len(title_clean):].strip()
        if not extra or len(extra) < 20:
            return ""
        clean_desc = extra
    
    # 清理引用推文噪音：移除 "SomeUser (@handle)" 格式
    clean_desc = re.sub(r'^[^\n]{0,50}\(@\w+\)\s*\n?', '', clean_desc).strip()
    
    # 单独的箭头/指向符号无意义
    if re.match(r'^[\s\W]{0,5}$', clean_desc):
        return ""
    
    # 压缩为单行（换行 → 空格），保持 Markdown 列表结构
    clean_desc = re.sub(r'\n+', ' ', clean_desc).strip()
    
    # 截断到 150 字符
    if len(clean_desc) > 150:
        cut = clean_desc[:150]
        for sep in ['。', '.', '!', '?', ',', '，']:
            pos = cut.rfind(sep)
            if pos > 60:
                cut = cut[:pos+1]
                break
        clean_desc = cut.rstrip() + '…'
    
    return clean_desc

def load_seen_urls():
    """加载已见过的 URL（兼容旧格式，返回 records list + url set）"""
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                raw = data.get('seen_urls', [])
                
                # 兼容旧格式：纯字符串列表 → 转为 record
                if raw and isinstance(raw[0], str):
                    records = [{'url': url, 'source': '', 'type': '', 'author': '', 'seen_at': ''} for url in raw]
                    url_set = set(raw)
                    print(f"  📦 已从旧格式迁移 {len(records)} 条记录")
                    return records, url_set
                
                # 新格式：record 列表
                url_set = set(r['url'] for r in raw)
                return raw, url_set
        except Exception as e:
            print(f"⚠️  加载 seen.json 失败: {e}")
            return [], set()
    return [], set()

def save_seen_urls(seen_records):
    """保存已见过的 URL 记录（FIFO 限制 + 原子写入）"""
    records = seen_records[-SEEN_URLS_LIMIT:]
    try:
        tmp_file = SEEN_FILE + ".tmp"
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump({'seen_urls': records}, f, indent=2, ensure_ascii=False)
        os.replace(tmp_file, SEEN_FILE)
    except Exception as e:
        print(f"⚠️  保存 seen.json 失败: {e}")

def _get_semaphore(instance: str) -> threading.Semaphore:
    """获取指定实例的并发信号量（已在模块加载时预初始化）"""
    return _instance_semaphores.get(
        instance,
        _instance_semaphores.setdefault(instance, threading.Semaphore(CONCURRENT_PER_INSTANCE))
    )

def _random_ua() -> str:
    """随机返回一个 User-Agent"""
    return random.choice(_UA_POOL)

def fetch_rss(username, nitter_instance):
    """从指定 nitter 实例获取 RSS（带随机 UA）"""
    url = f"{nitter_instance}/{username}/rss"
    headers = {'User-Agent': _random_ua()}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.read()

def fetch_rsshub(username, rsshub_instance):
    """从指定 RSSHub 实例获取 RSS（带随机 UA）"""
    url = f"{rsshub_instance}/twitter/user/{username}"
    headers = {'User-Agent': _random_ua()}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read()

# 构建域名替换表（从配置动态生成）[P1-5]
_DOMAIN_REPLACEMENTS = []
for _inst in NITTER_INSTANCES:
    _domain = _inst.replace('https://', '').replace('http://', '').rstrip('/')
    _DOMAIN_REPLACEMENTS.append((_domain, 'x.com'))

def _normalize_link(link):
    """将 nitter 域名替换为 x.com [P1-5]"""
    for old_domain, new_domain in _DOMAIN_REPLACEMENTS:
        link = link.replace(old_domain, new_domain)
    return link

def parse_rss(xml_content):
    """解析 RSS XML 内容"""
    root = ET.fromstring(xml_content)
    items = []
    
    for item in root.findall('.//item'):
        try:
            title_elem = item.find('title')
            link_elem = item.find('link')
            pub_date_elem = item.find('pubDate')
            description_elem = item.find('description')
            
            if title_elem is None or link_elem is None:
                continue
            
            title = title_elem.text or ""
            link = link_elem.text or ""
            pub_date = pub_date_elem.text if pub_date_elem is not None else ""
            description = description_elem.text if description_elem is not None else ""
            
            link = _normalize_link(link)
            
            items.append({
                'title': title,
                'link': link,
                'pub_date': pub_date,
                'description': description
            })
        except Exception as e:
            print(f"⚠️  解析单条推文失败: {e}")
            continue
    
    return items

def _is_instance_error(error_msg: str) -> bool:
    """判断是否是实例级错误（应进入冷却期）。
    账号级错误（404/403）不应标记实例为失败。
    """
    account_errors = ['404', '403', 'Not Found', 'Forbidden']
    return not any(e in error_msg for e in account_errors)


def _is_instance_available(instance: str, instance_fail_time: dict) -> bool:
    """检查实例是否可用（冷却期外则自动恢复）。"""
    fail_ts = instance_fail_time.get(instance)
    if fail_ts is None:
        return True
    if time.time() - fail_ts >= INSTANCE_COOLDOWN:
        # 冷却期已过，清除记录，恢复可用
        instance_fail_time.pop(instance, None)
        return True
    return False

def fetch_with_fallback(username, instance_fail_time: dict):
    """使用多实例 fallback 机制获取推文（Nitter → RSSHub）。
    实例失败后进入冷却期（INSTANCE_COOLDOWN 秒），冷却后自动恢复，
    不再永久封禁，解决扫描尾部连锁失败问题。
    """
    # 第一层：尝试 Nitter 实例
    for instance in NITTER_INSTANCES:
        if not _is_instance_available(instance, instance_fail_time):
            remaining = int(INSTANCE_COOLDOWN - (time.time() - instance_fail_time.get(instance, 0)))
            print(f"  ⏳ @{username} 跳过 {instance}（冷却中，剩余 {remaining}s）")
            continue
        sem = _get_semaphore(instance)
        with sem:
            for attempt in range(MAX_RETRIES):
                try:
                    time.sleep(random.uniform(JITTER_MIN, JITTER_MAX))
                    xml_content = fetch_rss(username, instance)
                    items = parse_rss(xml_content)
                    print(f"  ✅ @{username} [Nitter/{instance.split('/')[-1]}] {len(items)}条")
                    return items, None
                except Exception as e:
                    error_msg = str(e)
                    if attempt == MAX_RETRIES - 1:
                        print(f"  ❌ @{username} {instance} 失败: {error_msg}")
                        if _is_instance_error(error_msg):
                            # 记录失败时间（冷却期后自动恢复，不永久封禁）
                            instance_fail_time[instance] = time.time()
                        else:
                            break  # 账号级错误（404/403），不计入实例失败
                    else:
                        time.sleep(random.uniform(1.0, 2.0))

    # 第二层：Nitter 全部不可用，尝试 RSSHub
    for instance in RSSHUB_INSTANCES:
        if not _is_instance_available(instance, instance_fail_time):
            remaining = int(INSTANCE_COOLDOWN - (time.time() - instance_fail_time.get(instance, 0)))
            print(f"  ⏳ @{username} 跳过 RSSHub（冷却中，剩余 {remaining}s）")
            continue
        sem = _get_semaphore(instance)
        with sem:
            for attempt in range(MAX_RETRIES):
                try:
                    time.sleep(random.uniform(JITTER_MIN, JITTER_MAX))
                    xml_content = fetch_rsshub(username, instance)
                    items = parse_rss(xml_content)
                    print(f"  ✅ @{username} [RSSHub] {len(items)}条")
                    return items, None
                except Exception as e:
                    error_msg = str(e)
                    if attempt == MAX_RETRIES - 1:
                        print(f"  ❌ @{username} {instance} 失败: {error_msg}")
                        if _is_instance_error(error_msg):
                            instance_fail_time[instance] = time.time()
                        else:
                            break
                    else:
                        time.sleep(random.uniform(1.0, 2.0))

    return None, f"Nitter 和 RSSHub 所有实例均失败"

def filter_new_items(items, seen_records, seen_set, source_account):
    """过滤出新推文，并记录元数据到 seen_records"""
    new_items = []
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    for item in items:
        if item['link'] not in seen_set:
            new_items.append(item)
            # 写入富记录
            record = {
                'url': item['link'],
                'source': source_account,
                'type': _classify_type(item['title']),
                'author': _extract_original_author(item['link']),
                'seen_at': now_str
            }
            seen_records.append(record)
            seen_set.add(item['link'])
    return new_items

def _is_original_tweet(title):
    """判断是否为原创推文（排除 RT、回复、置顶）"""
    if title.startswith('RT ') or title.startswith('RT by @'):
        return False
    if title.startswith('R to @'):
        return False
    if title.startswith('Pinned:'):
        return False
    return True

def append_to_ideas(new_items, username):
    """将原创推文追加到 ideas.md（紧凑、结构化、无噪音）"""
    if not new_items:
        return
    
    # 只保留原创推文
    original_items = [item for item in new_items if _is_original_tweet(item['title'])]
    skipped = len(new_items) - len(original_items)
    
    if skipped > 0:
        print(f"  ® 过滤: {len(original_items)} 条原创 / {skipped} 条 RT/回复/置顶已跳过")
    
    # 过滤无信息量条目（纯链接、纯图片等）
    useful_items = [item for item in original_items if _is_useful_title(item['title'])]
    low_value = len(original_items) - len(useful_items)
    if low_value > 0:
        print(f"  ✂ 跳过 {low_value} 条无信息量推文（纯链接/纯图片）")
    
    if not useful_items:
        return
    
    try:
        with open(IDEAS_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n## @{username} - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            for item in useful_items:
                # 标题：第一行 + 去 emoji + 截断 80 字符
                title_line = strip_emoji(item['title'].split('\n')[0].strip())
                if len(title_line) > 80:
                    title_line = title_line[:77] + '…'
                
                f.write(f"- **{title_line}**\n")
                f.write(f"  - 链接: {item['link']}\n")
                f.write(f"  - 时间: {item['pub_date']}\n")
                
                # 摘要：单行、无 emoji、去重
                if item['description']:
                    summary = _extract_summary(item['title'], item['description'])
                    if summary:
                        f.write(f"  - 摘要: {summary}\n")
                
                f.write("\n")
    except Exception as e:
        print(f"⚠️  写入 ideas.md 失败: {e}")

def cleanup_old_ideas():
    """清理超过 KEEP_DAYS 天的旧推文（真正按日期删除）[P0-1]"""
    if not os.path.exists(IDEAS_FILE):
        return
    
    try:
        cutoff_date = datetime.now() - timedelta(days=KEEP_DAYS)
        with open(IDEAS_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 按 ## 标题行分段，解析日期决定保留/丢弃
        kept_lines = []
        keep_section = True
        removed_count = 0
        
        for line in lines:
            # 跳过旧文件头（会重新生成）
            if line.startswith('# X 创意雷达') or line.startswith('> 保留最近') or line.startswith('> 最后更新'):
                continue
            
            if line.startswith('## '):
                # 尝试解析: ## username - YYYY-MM-DD HH:MM
                match = re.search(r'- (\d{4}-\d{2}-\d{2})', line)
                if match:
                    try:
                        section_date = datetime.strptime(match.group(1), '%Y-%m-%d')
                        keep_section = section_date >= cutoff_date
                        if not keep_section:
                            removed_count += 1
                    except ValueError:
                        keep_section = True  # 解析失败则保留
                else:
                    keep_section = True
            
            if keep_section:
                kept_lines.append(line)
        
        # 生成新文件头 + 保留的内容
        header = f"# X 创意雷达 - 推文存档\n\n> 保留最近 {KEEP_DAYS} 天的推文\n> 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        content_str = "".join(kept_lines).strip()
        
        # 原子写入 [P0-3]
        tmp_file = IDEAS_FILE + ".tmp"
        with open(tmp_file, 'w', encoding='utf-8') as f:
            f.write(header)
            if content_str:
                f.write(content_str + "\n")
        os.replace(tmp_file, IDEAS_FILE)
        
        if removed_count > 0:
            print(f"🗑️  清理了 {removed_count} 个过期段落")
    except Exception as e:
        print(f"⚠️  清理旧推文失败: {e}")

def generate_summary(all_new_items, total_accounts, failed_accounts):
    """生成摘要报告（JSON 格式）"""
    # 第一步：过滤出有信息量的原创推文
    candidates = []
    for item in all_new_items:
        if not _is_original_tweet(item["title"]):
            continue
        title_line = strip_emoji(item["title"].split('\n')[0].strip())
        if not _is_useful_title(title_line):
            continue
        entry = {
            "title": title_line[:80] + '\u2026' if len(title_line) > 80 else title_line,
            "link": item["link"],
            "time": item["pub_date"],
            "account": item.get("_account", ""),
        }
        if item.get("description"):
            s = _extract_summary(item["title"], item["description"])
            if s:
                entry["summary"] = s
        candidates.append(entry)

    # 第二步：按账号多样性采样（每账号最多 3 条，取最新）
    # 避免单账号刷屏，控制 RESULT.json 体积，确保 Agent 能完整读取不 token 爆炸
    
    from collections import defaultdict
    account_buckets = defaultdict(list)
    for entry in candidates:
        account_buckets[entry["account"]].append(entry)

    new_ideas_preview = []
    for account, items in account_buckets.items():
        items_sorted = sorted(items, key=lambda x: x["time"], reverse=True)
        new_ideas_preview.extend(items_sorted[:MAX_PER_ACCOUNT])

    # 第三步：整体按时间倒序，最新推文优先
    new_ideas_preview.sort(key=lambda x: x["time"], reverse=True)

    return {
        "title": "X 创意雷达扫描报告",
        "scan_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "account_stats": {
            "total": total_accounts,
            "success": total_accounts - len(failed_accounts),
            "failed": len(failed_accounts)
        },
        "new_tweets_count": len(all_new_items),
        "new_originals_count": len(candidates),
        "sampled_preview_count": len(new_ideas_preview),
        "failed_accounts": failed_accounts,
        "status": "no_new" if not all_new_items else "has_new",
        "new_ideas_preview": new_ideas_preview
    }

# ============================================================================
# 主函数
# ============================================================================

def main():
    """主执行流程"""
    start_time = time.time()  # 记录启动时间

    # 确保目录存在（log() 依赖此步骤）
    ensure_dirs()

    log('=' * 48)
    log(f'X 创意雷达启动  账号数:{len(TARGET_ACCOUNTS)}')
    log(f'数据源: Nitter({len(NITTER_INSTANCES)}) + RSSHub({len(RSSHUB_INSTANCES)})')

    # 加载已见过的 URL
    seen_list, seen_set = load_seen_urls()
    log(f'已记录 URL 数: {len(seen_set)}')

    # 账号顺序随机打乱（避免每次以相同规律访问）
    accounts = list(dict.fromkeys(TARGET_ACCOUNTS))  # 顺带去重
    random.shuffle(accounts)
    log(f'并发模式: workers={MAX_WORKERS}  每实例≤{CONCURRENT_PER_INSTANCE}并发  jitter={JITTER_MIN}-{JITTER_MAX}s')
    print()

    # 并发扫描所有账号
    all_new_items = []
    failed_accounts = []
    instance_fail_time: dict = {}        # 实例失败时间戳（冷却恢复机制，GIL 保护 dict 操作）
    seen_lock = threading.Lock()         # 保护 seen_list / seen_set 的写操作
    ideas_lock = threading.Lock()        # 保护 ideas.md 文件写操作
    results_lock = threading.Lock()      # 保护 all_new_items / failed_accounts
    counter = [0]                        # 完成计数器（列表使闭包可写）
    total = len(accounts)

    def scan_one(username):
        """单账号扫描任务（在线程池中执行）"""
        items, error = fetch_with_fallback(username, instance_fail_time)

        with results_lock:
            counter[0] += 1
            idx = counter[0]

        if items is None:
            log(f'FAIL [{idx}/{total}] @{username}: {error}', 'ERROR')
            with results_lock:
                failed_accounts.append(username)
            return

        # 过滤新推文（需要锁保护 seen_set）
        with seen_lock:
            new_items = filter_new_items(items, seen_list, seen_set, username)

        log(f'OK   [{idx}/{total}] @{username}: 获取{len(items)}条, 新增{len(new_items)}条')

        if new_items:
            for ni in new_items:
                ni['_account'] = username
            with ideas_lock:
                append_to_ideas(new_items, username)
            with results_lock:
                all_new_items.extend(new_items)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scan_one, u): u for u in accounts}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                uname = futures[future]
                log(f'FAIL @{uname} 未捕获异常: {e}', 'ERROR')
                with results_lock:
                    failed_accounts.append(uname)

    print()

    # 保存 seen 记录
    save_seen_urls(seen_list)

    # 清理旧推文
    cleanup_old_ideas()

    # 生成摘要
    summary = generate_summary(all_new_items, len(TARGET_ACCOUNTS), failed_accounts)

    elapsed = time.time() - start_time
    elapsed_str = f'{int(elapsed // 60)}m{int(elapsed % 60)}s'

    # 持久化本次运行关键指标
    log(f'扫描完成  成功:{len(TARGET_ACCOUNTS)-len(failed_accounts)}/{len(TARGET_ACCOUNTS)}  '
        f'新推文:{len(all_new_items)}  原创:{summary["new_originals_count"]}  '
        f'耗时:{elapsed_str}')
    if failed_accounts:
        log(f'失败账号: {", ".join(failed_accounts)}', 'WARN')
    log('=' * 48)

    # 输出 JSON 结果供 OpenClaw 解析
    result = {
        "success": True,
        "total_accounts": len(TARGET_ACCOUNTS),
        "successful_accounts": len(TARGET_ACCOUNTS) - len(failed_accounts),
        "failed_accounts": failed_accounts,
        "new_items_count": len(all_new_items),
        "elapsed_seconds": round(elapsed, 1),
        "elapsed_str": elapsed_str,
        "summary": summary
    }

    result_json_str = json.dumps(result, ensure_ascii=False, indent=2)
    print("\n" + "=" * 50)
    print("RESULT JSON:")
    print(result_json_str)
    print("=" * 50)
    print("\n")

    # 同时写入文件，供 Cron Agent 通过 read_file 工具可靠读取
    result_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RESULT.json')
    try:
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(result_json_str)
        log(f'RESULT.json 已写入: {result_file}')
    except Exception as e:
        log(f'写入 RESULT.json 失败: {e}', 'WARN')

    # 额外保存一份天级结果快照，便于按天回看扫描结果
    try:
        day_result_file = _day_result_path()
        with open(day_result_file, 'w', encoding='utf-8') as f:
            f.write(result_json_str)
        log(f'当日结果快照已写入: {day_result_file}')
    except Exception as e:
        log(f'写入当日结果快照失败: {e}', 'WARN')

    if len(failed_accounts) == len(TARGET_ACCOUNTS):
        return 1
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 致命错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
