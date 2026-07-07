# AI 热点洞察 Agent 平台 — 项目规划

## Context

构建一个专注于**计算机技术领域**的 AI Agent 平台，自动从 B站、小红书、知乎、GitHub 等平台抓取编程、AI、编程语言、框架工具等技术主题的热门内容。支持自然语言交互查询热度趋势、**定时自动生成日报推送至飞书**、Web 仪表盘可视化呈现。**不做泛化全品类热点追踪，只聚焦计算机技术。**

---

## 1. 系统架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                       前端 (Vue 3)                           │
│               仪表盘 / 对话界面 / 折线图 / 日报预览             │
└─────────────────────┬────────────────────────────────────────┘
                      │ REST API (JSON)
┌─────────────────────▼────────────────────────────────────────┐
│                    API 网关 (FastAPI)                         │
│    /api/chat   /api/trends   /api/topics   /api/reports       │
└──────┬───────────────────────────────────┬───────────────────┘
       │                                   │
┌──────▼──────────┐               ┌───────▼──────────────┐
│   Agent 引擎     │               │   数据分析服务         │
│  (LangGraph)    │──────调用─────▶│   (Pandas)           │
│  意图识别        │               │   趋势计算             │
│  任务规划        │               │   热度标准化           │
│  对话记忆        │               │   情感分析             │
└──────┬──────────┘               └───────┬──────────────┘
       │                                  │
       │ 调用                              │ 查询
┌──────▼──────────────────────────────────▼──────────────────┐
│                    数据访问层 (Repository)                    │
│                  SQLite / PostgreSQL                        │
└──────┬──────────────────────────────────┬──────────────────┘
       │                                  │
┌──────▼──────────┐               ┌───────▼──────────────┐
│  采集调度器       │               │   定时任务引擎         │
│  (Supervisor)   │               │  (APScheduler)       │
│  关键词采集       │               │   每日日报生成         │
│  去重/限流       │               │   飞书消息推送         │
└──────┬──────────┘               └───────┬──────────────┘
       │                                  │
┌──────▼──────┐ ┌──────▼──────┐ ┌────────▼───────────────┐
│ B站/小红书/  │ │   GitHub    │ │    飞书 Bot 推送        │
│ 知乎采集器   │ │  Trending   │ │  ┌─────────────────┐   │
│(MediaCrawler)│ │ (mcp-github)│ │  │ 日报 / 突发热点  │   │
└─────────────┘ └─────────────┘ │  │ 自定义订阅推送   │   │
                                 │  └─────────────────┘   │
                                 └────────────────────────┘
```

**模块间通信原则**：所有跨模块调用走 REST API，不直接 import。每个模块可独立部署、独立替换、独立用更适合的语言重写。

---

## 1.5 项目目标

- 自动采集多平台**计算机技术类**热点内容与互动数据
- 提供自然语言交互式 Agent 查询能力（限定计算机技术领域）
- **定时自动生成技术热点日报，推送至飞书群聊**
- **突发热点实时告警 + 用户自定义主题订阅推送**
- 以热度折线图为核心的 Web 数据仪表盘
- 支持用户自定义技术关键词/主题监测（如 "Rust"、"大模型"、"GEO" 等）

---

## 2. 语言选择：每个模块用什么、为什么

| 模块 | 语言 | 理由 | 未来可替换为 |
|------|------|------|-------------|
| **Agent 引擎** | Python | LangChain/LangGraph 生态唯一选择 | 无（生态锁定） |
| **API 网关** | Python / FastAPI | 与 Agent 同进程调用，零序列化开销 | Go + Gin（高并发场景） |
| **数据采集调度器** | Python (MVP) | 直接调用 MediaCrawler 子进程；调度逻辑简单 | **Go（首选重构目标）** |
| **各平台采集器** | Python (MediaCrawler) | MediaCrawler 已解决反爬难题 | Go + Rod/Playwright-Go |
| **数据分析** | Python / Pandas | 数据分析事实标准 | Rust + Polars（极致性能） |
| **定时任务 + 飞书推送** | Python / APScheduler | 轻量级调度；飞书 SDK 生态成熟 | — |
| **前端** | TypeScript / Vue 3 | Web 前端唯一选择 | — |

### 2.1 关键判断：为什么采集层最终应该用 Go？

| 维度 | Python (MediaCrawler) | Go 重写后 |
|------|----------------------|-----------|
| 并发模型 | asyncio，单进程瓶颈 | goroutine，天然高并发 |
| 内存占用 | Playwright 每平台一个浏览器实例，~500MB+ | Rod 轻量级浏览器控制，~100MB |
| 部署复杂度 | 需安装 Chromium、Python 依赖 | 单二进制 + Chromium |
| 采集速度 | 串行/有限并发 | 多平台并行采集 |
| **结论** | **MVP 阶段用 Python 快速验证** | **生产化后 Go 重写采集层** |

**策略**：从 Day 1 起，采集层通过 **独立进程 + REST API** 与服务端解耦。后续 Go 重写时，API 契约不变，其他模块无感切换。

---

## 3. 模块详细设计

### 3.1 模块一：数据采集层

**目录**：`collector/`

**职责**：从各平台获取计算机技术相关热门内容，清洗后写入数据库。

**核心接口 — DataSource 抽象**：
```python
class DataSource(ABC):
    """每个平台实现此接口"""
    platform: str                          # "bilibili" | "xiaohongshu" | "zhihu" | "github"

    async def search(keyword: str, limit: int = 50) -> list[RawPost]
    async def fetch_detail(post_id: str) -> PostDetail
    async def fetch_trending(topic: str, hours: int = 24) -> list[RawPost]

class RawPost(TypedDict):
    platform: str
    post_id: str
    title: str
    url: str
    author: str
    publish_time: datetime
    metrics: PlatformMetrics            # 平台特有指标
    content_summary: str
    tags: list[str]

class PlatformMetrics(TypedDict):
    views: int | None
    likes: int | None
    comments: int | None
    shares: int | None
    stars: int | None                  # GitHub 专属
```

**各平台实现**：
| 平台 | 采集方式 | 搜索策略 |
|------|---------|---------|
| B站 | MediaCrawler (Playwright) | 关键词搜索科技区 + 编程区热门 |
| 小红书 | MediaCrawler (Playwright) | 技术关键词搜索笔记 |
| 知乎 | MediaCrawler (Playwright) | 话题广场 + 关键词搜索问答 |
| GitHub | mcp-github-trending (HTTP API) | Trending daily/weekly + 按语言过滤 |

**采集调度器**：
- 定时任务：每 N 小时对白名单关键词执行一轮搜索（N 可配置，默认 6h）
- 去重：`(platform, post_id)` 唯一索引去重
- 限流：每个平台最小请求间隔，防封 IP
- 代理：MediaCrawler 自带 IP 代理池

**技术关键词白名单**（初始版本）：
```
AI/大模型, GPT, Claude, LLM, LangChain, Agent, RAG,
Python, Go, Rust, TypeScript, JavaScript, Java, C++, Zig,
React, Vue, Svelte, Next.js, Nuxt,
Kubernetes, Docker, Terraform, CI/CD,
数据库, Redis, PostgreSQL, MySQL, MongoDB,
开源, 前端, 后端, 架构, 性能优化, 系统设计
```

### 3.2 模块二：数据存储与访问层

**目录**：`repository/`

**数据库表设计**：

```sql
-- 原始采集数据
CREATE TABLE raw_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,           -- bilibili|xiaohongshu|zhihu|github
    post_id TEXT NOT NULL,
    keyword TEXT NOT NULL,            -- 通过哪个关键词搜到的
    title TEXT,
    url TEXT,
    author TEXT,
    publish_time DATETIME,
    view_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    share_count INTEGER,
    star_count INTEGER,              -- GitHub
    content_summary TEXT,
    tags JSON,                        -- ["Python", "AI", ...]
    raw_data JSON,                    -- 原始 JSON，备用
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, post_id, fetched_at)  -- 同一帖子可被多次采集(追踪热度变化)
);

-- 每日热度快照（聚合后的标准化数据）
CREATE TABLE daily_hotness (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,              -- 主题名，如 "GEO", "Rust", "LangChain"
    platform TEXT NOT NULL,
    date DATE NOT NULL,
    hotness_score REAL NOT NULL,      -- [0, 100] 标准化热度分
    post_count INTEGER,              -- 当日相关帖子数
    total_views INTEGER,
    total_likes INTEGER,
    total_comments INTEGER,
    top_posts JSON,                  -- 热度最高的前 5 条帖子 ID
    UNIQUE(topic, platform, date)
);

-- 用户自定义监测主题
CREATE TABLE monitored_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    keywords TEXT NOT NULL,           -- 搜索时用的关键词，逗号分隔
    platforms TEXT NOT NULL,          -- 监测平台，逗号分隔
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT 1
);

-- 对话历史
CREATE TABLE conversation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,               -- user | assistant
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 日报记录
CREATE TABLE daily_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date DATE NOT NULL UNIQUE,
    title TEXT NOT NULL,               -- "2026-07-07 技术热点日报"
    summary TEXT NOT NULL,             -- AI 生成的日报摘要（Markdown）
    top_topics JSON,                   -- 当日 TOP 10 主题及热度分
    platform_highlights JSON,          -- 各平台亮点
    rising_topics JSON,                -- 热度上升最快的主题
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 飞书推送配置
CREATE TABLE feishu_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    webhook_url TEXT NOT NULL,         -- 飞书机器人 Webhook 地址
    push_daily_report BOOLEAN DEFAULT 1,  -- 是否推送日报
    push_breaking BOOLEAN DEFAULT 1,      -- 是否推送突发热点
    breaking_threshold REAL DEFAULT 30,   -- 突发热点阈值(热度变化%)
    push_time TIME DEFAULT '09:00',       -- 日报推送时间
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 用户自定义订阅（飞书推送）
CREATE TABLE alert_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,               -- 订阅主题
    platforms TEXT NOT NULL,           -- 关注平台
    frequency TEXT DEFAULT 'daily',    -- daily | weekly | realtime
    push_channel TEXT DEFAULT 'feishu', -- feishu | web | email(预留)
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Repository 层接口**：
```python
class PostRepository:
    async def upsert_posts(posts: list[RawPost]) -> int     # 返回新增数量
    async def query(topic: str, platform: str, days: int) -> list[RawPost]
    async def get_top_posts(topic: str, limit: int) -> list[RawPost]

class HotnessRepository:
    async def save_snapshot(snapshot: DailyHotness) -> None
    async def get_trend(topic: str, days: int) -> list[DailyHotness]  # 给折线图用
    async def get_ranking(date: str, platform: str, limit: int) -> list[DailyHotness]

class TopicRepository:
    async def list_active() -> list[MonitoredTopic]
    async def add(topic: MonitoredTopic) -> int
    async def deactivate(topic_id: int) -> None

class ReportRepository:
    async def save_report(report: DailyReport) -> int
    async def get_latest() -> DailyReport | None
    async def get_by_date_range(start: date, end: date) -> list[DailyReport]

class SubscriptionRepository:
    async def list_active() -> list[AlertSubscription]
    async def add(sub: AlertSubscription) -> int
    async def deactivate(sub_id: int) -> None
```

### 3.3 模块三：Agent 引擎

**目录**：`agent/`

**职责**：接收自然语言查询 → 意图识别 → 任务规划 → 调用工具执行 → 生成回复。

**LangGraph 工作流设计**：

```
用户输入: "最近一周 GEO 在小红书上热度怎么样？"
    │
    ▼
[意图识别节点]
    │ 提取: topic="GEO", time_range="7d", platforms=["xiaohongshu"], action="trend_query"
    │
    ▼
[任务规划节点]
    │ 生成任务列表:
    │   1. 查询 daily_hotness 表获取 GEO+小红书 最近 7 天的数据
    │   2. 如果数据不足/过期 → 触发采集任务
    │   3. 计算趋势（上升/下降/平稳）
    │   4. 生成自然语言总结 + 折线图数据
    │
    ▼
[工具调用节点] ◄──── 循环直至任务完成
    │ 可用工具:
    │   - search_topic(topic, platforms, days)  → 查询数据库
    │   - trigger_collection(topic, platforms)  → 触发采集
    │   - get_trend_data(topic, platforms, days) → 取趋势数据
    │   - compare_topics(topics, platform, days) → 多主题对比
    │   - list_hot_topics(platform, limit)      → 当前热门主题
    │
    ▼
[回复生成节点]
    │ 输出: 自然语言总结 + 结构化 chart_data (给前端渲染折线图)
```

**Agent 工具定义**（LangChain Tool 格式）：
```python
tools = [
    StructuredTool.from_function(
        func=search_topic_hotness,
        name="search_topic_hotness",
        description="查询某个技术主题在指定平台的热度数据。topic 如 'GEO', 'Rust', '大模型'",
        args_schema=TopicQuerySchema,
    ),
    StructuredTool.from_function(
        func=trigger_collection,
        name="trigger_collection",
        description="当数据库中没有足够数据时，触发对指定主题的实时采集",
        args_schema=TriggerCollectSchema,
    ),
    StructuredTool.from_function(
        func=get_top_topics,
        name="get_top_topics",
        description="获取指定平台当前最热门的计算机技术主题",
        args_schema=TopTopicsSchema,
    ),
]
```

**限定域策略**：Agent 的 system prompt 限定只回答计算机技术相关问题，非技术问题礼貌拒绝。

### 3.4 模块四：数据分析层

**目录**：`analyzer/`

**职责**：对采集到的原始数据进行标准化处理和趋势计算。

**热度标准化算法**：
```
单平台热度分 = 0-100 归一化（基于该平台内所有技术类帖子的指标分布）

平台指标权重（可调整）：
  B站:     0.3*播放量_分位 + 0.25*点赞_分位 + 0.25*评论_分位 + 0.2*分享_分位
  小红书:   0.2*阅读量_分位 + 0.3*点赞_分位 + 0.3*评论_分位 + 0.2*收藏_分位
  知乎:     0.3*阅读量_分位 + 0.35*赞同_分位 + 0.35*评论_分位
  GitHub:   0.5*stars_分位 + 0.3*forks_分位 + 0.2*最近活跃度

每日热度分 = Σ(该主题下所有帖子的单帖热度分 × 时间衰减因子)
时间衰减因子 = e^(-λt)  其中 t=发布距今小时数, λ 控制衰减速度
```

**趋势判定**：
- 对比前一周均值，变化 >20% → "显著上升/下降"
- 变化 5%~20% → "小幅上升/下降"
- 变化 <5% → "热度平稳"

### 3.5 模块五：API 网关

**目录**：`api/`

**核心端点**：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | Agent 对话入口，接收 `{message, session_id?}`，返回流式/非流式回复 |
| `/api/trends` | GET | 获取趋势数据，`?topic=GEO&platforms=xiaohongshu&days=30` |
| `/api/topics/hot` | GET | 当前热门主题排行，`?platform=bilibili&limit=20` |
| `/api/topics/monitor` | CRUD | 管理自定义监测主题 |
| `/api/dashboard` | GET | 仪表盘聚合数据（折线图数据 + 热门排行 + 趋势摘要） |
| `/api/reports/latest` | GET | 获取最新一期日报 |
| `/api/reports` | GET | 日报历史列表，`?from=2026-07-01&to=2026-07-07` |
| `/api/reports/generate` | POST | 手动触发日报生成（调试用） |
| `/api/config/feishu` | PUT/GET | 配置飞书 Webhook URL、推送时间、阈值 |
| `/api/subscriptions` | CRUD | 管理飞书订阅：关注特定主题，自动推送 |
| `/api/subscriptions/test` | POST | 发送测试消息到飞书，验证 Webhook 是否正常 |

**chat 端点响应格式**：
```json
{
  "reply": "最近一周 GEO 在小红书上热度处于上升趋势，相关笔记共 23 篇，总互动量较前一周增长 35%...",
  "chart_data": {
    "type": "line",
    "title": "GEO 在小红书的近 30 天热度趋势",
    "xAxis": ["2026-06-07", "2026-06-08", ...],
    "series": [
      {"name": "热度分", "data": [45, 48, 52, 50, 58, 62, 68, ...]},
      {"name": "笔记数", "data": [3, 5, 4, 6, 5, 8, 10, ...]}
    ]
  },
  "sources": [
    {"platform": "xiaohongshu", "url": "https://...", "title": "..."}
  ]
}
```

### 3.6 模块六：前端

**目录**：`web/`

**页面结构**：
```
/                    主仪表盘（概览页）
  ├── 顶部搜索栏     自然语言输入 + 快捷提问示例
  ├── 热度总览卡片   各平台当前最热主题 TOP 5
  ├── 趋势折线图     选定主题的多平台热度折线图对比
  └── 最新热点列表   按时间线展示最新热门内容

/monitor             自定义监测管理
  ├── 已监测主题列表
  ├── 添加新主题     输入主题名 + 关键词 + 选择平台
  └── 热度报告        每个监测主题的趋势报告

/chat                对话详情页
  └── 对话历史 + 当前对话
```

**组件树**：
```
App.vue
├── SearchBar.vue          自然语言搜索框
├── Dashboard.vue          仪表盘主页
│   ├── HotTopicCard.vue   热度 TOP 5 卡片
│   ├── TrendChart.vue     ECharts 折线图（核心组件）
│   └── PostList.vue       内容列表
├── MonitorPanel.vue       监测管理
│   ├── TopicForm.vue      添加主题表单
│   └── TopicReport.vue    单主题报告
└── ChatView.vue           对话视图
    └── MessageBubble.vue  消息气泡
```

### 3.7 模块七：定时任务与飞书推送

**目录**：`notifier/`

**职责**：定时生成技术热点日报，通过飞书 Bot 推送到群聊；突发热度告警。

#### 3.7.1 定时任务引擎 (APScheduler)

```
┌──────────────────────────────────────────────────┐
│                 APScheduler                       │
│                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │ 采集定时任务  │  │ 日报生成任务  │  │ 飞书推送   │ │
│  │ 每 6h 执行   │  │ 每日 9:00   │  │ 日报推送   │ │
│  │ 全量关键词    │  │ 生成前一日   │  │ 突发告警   │ │
│  │ 多平台采集    │  │ 热点汇总     │  │ 订阅推送   │ │
│  └─────────────┘  └─────────────┘  └───────────┘ │
└──────────────────────────────────────────────────┘
```

**任务清单**：

| 任务 | 频率 | 说明 |
|------|------|------|
| `collect_all` | 每 6h | 对白名单关键词在所有平台执行采集 |
| `generate_daily_report` | 每日 09:00 | 汇总前 24h 数据，生成日报 |
| `push_to_feishu` | 日报生成后 | 将日报推送到飞书群 |
| `check_breaking` | 每 1h | 检测是否有主题热度异动，触发突发告警 |
| `cleanup_old_data` | 每周日凌晨 | 清理 N 天前的 raw_posts（保留 daily_hotness 快照） |

#### 3.7.2 日报生成流程

```
[定时触发 09:00]
    │
    ▼
[数据聚合]
    │ 查询 daily_hotness（date = 昨天）
    │ 计算每个主题的热度分变化（vs 前日）
    │ 筛选 TOP 10 热度主题 + TOP 5 上升最快主题
    │
    ▼
[LLM 生成日报]
    │ 输入: 结构化数据(Top 主题、各平台亮点、上升趋势)
    │ Prompt: "你是技术热点日报编辑，根据以下数据生成一篇简洁的日报"
    │ 输出: Markdown 格式日报（标题、摘要、各平台热点、趋势分析）
    │
    ▼
[存储 + 推送]
    │ 写入 daily_reports 表
    │ 调用飞书 Webhook 发送 Markdown 消息
    │ 如果 Web 端在线 → 同步推送到前端通知
```

#### 3.7.3 日报内容模板

```markdown
# 🔥 技术热点日报 | 2026-07-07

> 今日概览：AI 大模型热度持续走高，"GEO" 话题在小红书异军突起

## 📊 TOP 5 热度主题
1. **大模型** 🔥 92分（↑ 15%）— 多平台热议
2. **GEO** 🆕 85分（↑ 68%）— 小红书爆发
3. **Rust** 78分（→ 平稳）— 知乎讨论活跃
4. **LangChain** 72分（↓ 8%）— 热度小幅回落
5. **Kubernetes** 68分（↑ 5%）— B站教程增多

## 📈 上升最快
- **GEO** ↑68% — 小红书多篇爆款笔记
- **Zig** ↑35% — GitHub 新项目引发关注
- **WebAssembly** ↑28% — 知乎深度文章推荐

## 🗂 各平台亮点
- **B站**: Rust 系列教程播放量破 10 万
- **小红书**: "程序员工资" 话题引发热议
- **知乎**: "2026 年该学什么语言" 成热门问答
- **GitHub**: ziglang/zig 项目周增 500+ stars

---
🤖 由 AI 热点洞察 Agent 自动生成 | [查看详情](http://localhost:5173)
```

#### 3.7.4 飞书集成方案

**接入方式**：飞书自定义机器人 Webhook（最简单，零成本）

**配置步骤**：
1. 在飞书群聊中 → 群设置 → 群机器人 → 添加自定义机器人
2. 复制 Webhook URL → 填入平台配置 `/api/config/feishu`
3. 可选：配置签名校验（安全设置）

**推送消息类型**：

| 场景 | 消息格式 | 触发条件 |
|------|---------|---------|
| 每日日报 | Markdown 消息（丰富格式） | 每日 09:00 定时 |
| 突发热点告警 | 文本消息 + @所有人 | 某主题热度变化 > 阈值 |
| 订阅推送 | 文本消息 | 用户订阅的主题有新动态 |

**飞书 SDK 封装**：
```python
class FeishuNotifier:
    """飞书机器人推送"""
    def __init__(self, webhook_url: str, secret: str | None = None):
        ...

    async def send_markdown(self, title: str, content: str) -> bool:
        """发送 Markdown 格式消息"""

    async def send_text(self, text: str, at_all: bool = False) -> bool:
        """发送文本消息，可选 @所有人"""

    async def send_card(self, card: dict) -> bool:
        """发送富卡片消息（折线图截图/数据卡片）"""
```

#### 3.7.5 突发热点告警逻辑

```
每小时检查一次:
  1. 计算当前小时各主题的热度分
  2. 对比前 24h 同时段热度分
  3. 变化率 > breaking_threshold（默认 30%）→ 触发告警
  4. 同一主题 24h 内不重复告警
```

---

## 4. 项目目录结构

```
agent/
├── backend/                     # Python 后端
│   ├── api/                     # FastAPI 路由
│   │   ├── __init__.py
│   │   ├── chat.py              # /api/chat
│   │   ├── trends.py            # /api/trends
│   │   ├── topics.py            # /api/topics
│   │   └── dashboard.py         # /api/dashboard
│   ├── agent/                   # Agent 引擎
│   │   ├── __init__.py
│   │   ├── graph.py             # LangGraph 工作流定义
│   │   ├── tools.py             # Agent 工具集
│   │   ├── prompts.py           # System prompt 模板
│   │   └── memory.py            # 对话记忆管理
│   ├── collector/               # 数据采集层
│   │   ├── __init__.py
│   │   ├── base.py              # DataSource 抽象基类
│   │   ├── supervisor.py        # 采集调度器(定时+限流)
│   │   ├── bilibili.py          # B站采集实现
│   │   ├── xiaohongshu.py       # 小红书采集实现
│   │   ├── zhihu.py             # 知乎采集实现
│   │   ├── github.py            # GitHub 采集实现
│   │   └── keywords.py          # 关键词白名单管理
│   ├── analyzer/                # 数据分析
│   │   ├── __init__.py
│   │   ├── normalizer.py        # 热度标准化
│   │   ├── trend.py             # 趋势计算
│   │   └── sentiment.py         # 基础情感分析
│   ├── notifier/                # 定时任务 & 飞书推送
│   │   ├── __init__.py
│   │   ├── scheduler.py         # APScheduler 定时任务注册
│   │   ├── report_generator.py  # 日报生成（聚合 + LLM 撰写）
│   │   ├── feishu.py            # 飞书 Bot SDK 封装
│   │   ├── breaking.py          # 突发热点检测
│   │   └── templates.py         # 日报/告警消息模板
│   ├── repository/              # 数据访问层
│   │   ├── __init__.py
│   │   ├── posts.py             # raw_posts CRUD
│   │   ├── hotness.py           # daily_hotness CRUD
│   │   ├── topics.py            # monitored_topics CRUD
│   │   ├── reports.py           # daily_reports CRUD
│   │   └── subscriptions.py     # alert_subscriptions CRUD
│   ├── models/                  # Pydantic 数据模型
│   │   ├── __init__.py
│   │   ├── post.py
│   │   ├── hotness.py
│   │   ├── report.py
│   │   └── chat.py
│   ├── db.py                    # 数据库连接管理
│   ├── config.py                # 配置管理
│   └── main.py                  # FastAPI 入口
├── web/                         # Vue 3 前端
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── api/                 # 后端 API 调用封装
│   │   ├── stores/              # Pinia 状态管理
│   │   └── router/
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml           # 本地开发环境
├── Dockerfile.backend
├── Dockerfile.web
├── Makefile                     # 常用命令快捷方式
└── README.md
```

---

## 5. 开发阶段与里程碑

### 阶段一：核心概念验证 (2-3 周)

**目标**：跑通 GitHub + 一个中文平台（B站）的双源全链路。

| 任务 | 产出 |
|------|------|
| 项目骨架搭建 | 目录结构 + FastAPI 入口 + Vue 脚手架 + Docker 开发环境 |
| DB 建表 + Repository 层 | SQLite 表创建 + 基础 CRUD |
| GitHub 数据源 | mcp-github-trending 集成 + 写入 raw_posts |
| B站数据源 | MediaCrawler 本地部署 + 关键词搜索验证 + 写入 raw_posts |
| 数据标准化 + 趋势计算 | 单平台热度分计算 + 日快照生成 |
| 最简 API | `/api/topics/hot`、`/api/trends` 可返回数据 |
| 最简前端 | 一个页面：搜索框 + 数据列表表格 |
| Agent 端点 | `/api/chat` 能回答 "今天 GitHub 上最热的 Python 项目是什么？" |

**Agent 能回答的示例问题**：
- "今天 GitHub 上最热的 Go 项目是什么？"
- "最近 B站上 AI 相关的热门视频有哪些？"

**交付物**：`docker-compose up` 一键启动，浏览器访问 localhost 可看到数据列表，可对话查询。

### 阶段二：最小可用产品 (4-6 周)

| 任务 | 产出 |
|------|------|
| 扩展至 3 中文平台 | 小红书 + 知乎采集器 |
| 采集调度器 | 定时任务 + 去重 + 限流 |
| **定时任务引擎** | APScheduler 集成，每日日报自动生成 |
| **飞书推送** | 飞书 Bot Webhook 接入，日报定时推送至群聊 |
| Agent 工具完善 | search_topic、trigger_collection、get_top_topics 全部就位 |
| 对话记忆 | 会话 ID + 上下文关联 |
| 热度折线图 | ECharts TrendChart 组件 |
| 仪表盘页面 | 搜索栏 + 热门卡片 + 折线图 + 内容列表 |
| 对话页面 | 聊天界面 + chart_data 渲染 |
| 日报预览页 | Web 端查看/回溯历史日报 |

**Agent 能回答的示例问题**：
- "最近一周 Rust 在知乎上的热度趋势怎么样？"
- "对比一下 Python 和 Go 在 B站上的热度"
- "小红书最近有什么新出的 AI 工具推荐？"
- "给我生成一份昨天的技术热点日报"

**飞书推送效果**：
- 每日 09:00 自动推送 Markdown 格式日报到飞书群
- 支持手动触发："把今天的热点日报推送到飞书"

**交付物**：可内测的 MVP，三平台 + GitHub，折线图 + 对话 + 仪表盘 + 飞书日报推送，完整闭环。

### 阶段三：功能完善与优化 (3-4 周)

| 任务 | 产出 |
|------|------|
| 自定义监测主题 | CRUD + 每个主题的趋势报告 |
| **飞书订阅推送** | 用户自定义订阅特定主题，飞书自动推送动态 |
| **突发热点告警** | 热度异动检测 + 飞书 @提醒 |
| 多平台对比折线图 | 同一主题跨平台趋势对比 |
| Agent 意图识别优化 | prompt tuning + few-shot examples |
| 情感分析 | 对热点内容的评论做正负面判断 |
| 性能优化 | 数据库索引 + API 响应缓存 |
| 日志 + 异常追踪 | structlog + Sentry 集成 |

**交付物**：功能完整的 β 版本，飞书日报 + 突发告警 + 订阅推送全覆盖，可对外邀测。

### 阶段四：架构演进与部署（视情况）

- 识别性能瓶颈（大概率是采集层）
- 采集层 Go 重写：独立服务 + gRPC API，替换 Python collector
- Docker 容器化生产部署 + Nginx 反向代理
- 公测

---

## 6. 关键风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| MediaCrawler 封禁/停更 | 中文平台采集全部失效 | 各平台 DataSource 独立接口，可随时替换为自研实现或官方 API |
| 平台反爬升级 | 采集成功率下降 | MediaCrawler 自带 IP 代理池；降低采集频率；关注上游更新 |
| 非技术内容噪音大 | 搜索结果中夹杂非技术内容 | 关键词白名单 + 标题/标签做技术术语匹配 + LLM 二次过滤 |
| 跨平台热度不可比 | 折线图跨平台对比无意义 | 只做平台内百分位排名；跨平台时标注"平台内热度"，不做绝对值对比 |
| 飞书 Webhook 限频 | 消息推送失败 | 合并短时间内的多条告警；失败重试+降级通知 |
| 时间预估偏乐观 | 延期 | 每阶段预留 50% buffer；Phase 内优先交付核心链路，次要功能可降级 |
| LangChain 版本迭代快 | API 不兼容导致构建失败 | 锁定版本号（requirements.txt pin 版本）；升级前本地验证 |

---

## 7. 验证方式

| 阶段 | 验证方法 |
|------|----------|
| 阶段一 | `docker-compose up` → 浏览器访问 → 搜索框看到 GitHub Trending 列表 → 对话问"今天最热的 Go 项目"获得回复 → 数据库 raw_posts 表有新数据 |
| 阶段二 | 仪表盘折线图展示近 30 天趋势 → Agent 能处理复合查询（时间+平台+主题） → 三平台数据正常采集 → **飞书群收到每日 09:00 日报推送** → Web 端可查看历史日报 |
| 阶段三 | 自定义添加"GEO"监测主题 → 查看专属趋势报告 → 情感分析结果合理 → **热度异动时飞书收到突发告警** → 订阅主题有更新时收到飞书推送 |
| 阶段四 | `docker-compose up` 生产部署 → 公网可访问 → 7×24 稳定运行 |

---

## 8. 下一步行动

1. 搭建项目骨架（目录结构、FastAPI 入口、Vue 3 脚手架、docker-compose.yml）
2. Clone MediaCrawler 并本地跑通 B站关键词搜索
3. 集成 mcp-github-trending 验证 GitHub 数据获取
4. 实现 DataSource 抽象基类 + 各平台实现
5. 建 SQLite 表（含 report/subscription 表） + Repository 层
6. 实现 `/api/chat` + Agent 最简工作流，跑通"提问→采集→回答"闭环
7. 飞书机器人创建 + Webhook 配置 + 测试消息推送验证
