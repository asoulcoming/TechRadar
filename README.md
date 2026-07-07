# TechRadar — AI 热点洞察 Agent 平台

专注于**计算机技术领域**的 AI Agent 平台，自动从 B站、小红书、知乎、GitHub 抓取技术热点内容，定时生成日报推送至飞书。

> 详细项目规划见 [docs/plan.md](docs/plan.md) | 开发过程记录见 [process_md/](process_md/)

## 快速开始

### 环境要求

- Python 3.9+ (推荐 3.10+)
- Node.js 22+
- (可选) Docker

### 本地开发

```bash
# 安装依赖
make install

# 启动后端 (http://localhost:8000)
make dev

# 另开终端，启动前端 (http://localhost:5173)
make web
```

### Docker 部署

```bash
make docker
```

访问 http://localhost:5173

## 项目结构

```
TechRadar/
├── backend/          # Python 后端 (FastAPI + LangGraph)
│   ├── api/          # REST API 路由
│   ├── agent/        # Agent 引擎
│   ├── collector/    # 数据采集层 (MediaCrawler)
│   ├── analyzer/     # 数据分析 (热度标准化)
│   ├── notifier/     # 定时任务 + 飞书推送
│   ├── repository/   # 数据访问层
│   └── models/       # Pydantic 模型
├── web/              # Vue 3 前端
├── docs/             # 项目规划文档
├── process_md/       # 开发过程记录
└── docker-compose.yml
```

## API 端点

| 端点 | 说明 |
|------|------|
| `POST /api/chat` | Agent 对话 |
| `GET /api/trends` | 趋势数据 |
| `GET /api/topics/hot` | 热门主题 |
| `GET /api/dashboard` | 仪表盘数据 |
| `GET /api/reports/latest` | 最新日报 |
| `POST /api/reports/generate` | 手动生成日报 |
