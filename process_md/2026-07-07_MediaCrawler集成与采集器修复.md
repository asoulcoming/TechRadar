# 2026-07-07 MediaCrawler 集成与采集器修复

## 做了什么

### MediaCrawler Clone & 环境搭建
- Clone [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 到 `/Users/liujiongjun/work/private/MediaCrawler`（与 TechRadar 同级目录）
- 创建独立 venv 并安装全部依赖（含 Playwright + Chromium）
- 验证 `python main.py --help` 正常执行

### 修复采集器与 MediaCrawler 实际接口的 4 处差异

| 差异 | 修复前 | 修复后 |
|------|--------|--------|
| B站 platform ID | `--platform bilibili` ❌ | `--platform bili` ✅ |
| 输出路径 | `data/bilibili/search_{keyword}.json` | `data/bili/search_contents_{date}.jsonl` |
| 输出格式 | JSON | JSONL (MediaCrawler 默认) |
| 缺失参数 | 无 | `--headless true --save_data_option jsonl --crawler_max_notes_count N` |
| python 路径 | 系统 `python`（找不到依赖） | MediaCrawler `.venv/bin/python` ✅ |

### 添加 CDP 预检机制
- 问题：MediaCrawler 默认 CDP 模式连接 Chrome 9222 端口，无 Chrome 时等待 60s 超时
- 解决：调用 MediaCrawler 前 `socket.create_connection(('localhost', 9222), timeout=0.5)` 快速检测
- CDP 不可用时直接走 Mock 降级，**从 60s+ 超时降到毫秒级响应**
- `_can_crawl()` 方法：`available(MediaCrawler已安装) AND _is_cdp_available()`

### 修复错误处理
- `_run_mediacrawler_search` 失败时 raise 异常 → `search()` 的 try/except 捕获 → Mock 降级
- 输出文件不存在时 raise `FileNotFoundError`（而非静默返回空）
- 三个平台（B站/小红书/知乎）统一行为

## 技术决策
- **MediaCrawler 始终需要 Chrome**：无论 CDP 模式还是 Playwright 标准模式，MediaCrawler 底层都是 `channel="chrome"`，依赖系统安装的 Chrome 浏览器。已通过 `brew install --cask google-chrome` 安装。
- **Playwright 标准模式替代 CDP 模式**：通过 `run_search.py` 适配器设置 `ENABLE_CDP_MODE = False`，使用 Playwright 启动 Chrome（而非连接已有 CDP），无需手动开启远程调试。
- **首次登录需扫码，后续免登**：登录态缓存在 `MediaCrawler/browser_data/`，后续 headless 运行自动复用。
- **Mock 降级保持开发流畅**：无登录态或 Chrome 不可用时，采集器自动返回 Mock 数据，全链路可调试。

## 验证结果
- B站/小红书/知乎三个采集器 `available: True` ✅
- `run_search.py` 适配器正常工作 ✅
- 首次扫码登录成功 ✅
- 登录态缓存复用成功（`Use cache login state get web interface successfull!`）✅
- Headless 模式采集完成 ✅
- 38 条真实 B站数据写入 JSONL ✅
- 解析器字段映射修复（`nickname` → `author`）✅
- Mock 降级秒级响应 ✅

## 下一步
- [ ] 用同样方式扫码登录小红书、知乎（各只需一次）
- [ ] 端到端：采集器调用 `run_search.py` → 读取 JSONL → 写入 SQLite → Dashboard 展示
- [ ] 验证 `npm install && npm run dev` 前端启动
- [ ] 配置飞书 Webhook 并测试消息推送
