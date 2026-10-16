# AI 大模型价格雷达 V1.0

自动采集全球主流 AI 大模型 API 价格，每天北京时间 08:00 更新一次，并在网页上以图表形式展示当前价格、每日价格变化和历史价格趋势。**零服务器成本**：由 GitHub Actions 定时执行采集，数据以 JSON 文件形式提交到仓库，由 Cloudflare Pages 免费托管静态网站。

## 功能特性

- 覆盖 6 家厂商、30+ 个主流模型（OpenAI、Anthropic、Google、DeepSeek、阿里百炼、智谱 AI）
- 每日自动采集价格，自动识别**涨价 / 降价 / 新模型**变化
- 价格趋势折线图（ECharts），支持按模型查看历史走势
- 网页支持模型搜索与厂商筛选
- 采集失败自动回退到内置参考价并明确标注「参考」，不影响站点可用性
- 全静态托管，零服务器成本

## 技术架构

```
GitHub Actions (定时 08:00 北京时间)
        │  python crawler/main.py
        ▼
Python 爬虫 (spiders/ 6 家厂商)
        │
        ▼
数据处理 (processors/) 价格比较 + JSON 导出
        │
        ▼
data/ 目录 JSON 数据（含网站副本 website/data/）
        │  git commit & push
        ▼
Cloudflare Pages 自动部署 website/ → 静态站点
```

## 目录结构

```
AIPriceRadar/
├── crawler/
│   ├── main.py              # 主流程入口
│   ├── config.py            # 全局配置（URL、超时、路径）
│   └── requirements.txt     # Python 依赖
├── spiders/
│   ├── base.py              # 爬虫基类 + 通用解析工具 + 兜底机制
│   ├── openai.py            # OpenAI
│   ├── claude.py            # Anthropic Claude
│   ├── gemini.py            # Google Gemini
│   ├── deepseek.py          # DeepSeek
│   ├── qwen.py              # 阿里云百炼（通义千问）
│   └── zhipu.py             # 智谱 AI（GLM）
├── processors/
│   ├── price_compare.py     # 价格变化分析
│   └── json_export.py       # JSON 导出与网站数据同步
├── data/                    # 数据仓库（git 提交，长期积累）
│   ├── today.json           # 当天数据（价格表 + 变化）
│   ├── history.json         # 历史价格快照（按天追加）
│   ├── models.json          # 模型基础信息
│   └── promotions.json      # 优惠活动（可人工维护）
├── website/                 # 静态网站（Cloudflare Pages 发布目录）
│   ├── index.html           # 页面结构（Vue3 + ECharts）
│   ├── app.js               # 展示逻辑
│   ├── style.css            # 样式
│   └── data/                # 数据副本（crawler 自动同步）
└── .github/workflows/
    └── daily_update.yml     # 每日自动更新工作流
```

## 快速开始（本地）

```bash
# 1. 安装依赖（需要 Python 3.10+）
pip install -r crawler/requirements.txt

# 2. 运行采集程序（联网抓取官网价格）
python crawler/main.py

# 2'. 离线模式：跳过网络抓取，使用内置参考价快速验证流程
python crawler/main.py --offline

# 3. 本地预览网站
cd website
python -m http.server 8765
# 浏览器打开 http://localhost:8765
```

## 部署指南

### 1. 推送到 GitHub 仓库

把项目推送到 GitHub，`daily_update.yml` 会在每天 UTC 00:00（北京时间 08:00）自动执行采集并提交数据。

手动触发一次：仓库 **Actions** 页面 → **Daily Price Update** → **Run workflow**。

### 2. Cloudflare Pages 免费托管

1. Cloudflare 控制台 → **Workers & Pages** → **创建** → **Pages** → **连接到 Git**
2. 选择本仓库
3. 构建设置：
   - **构建命令**：`cp -r data website/data`（可选，crawler 已自动同步 `website/data/`）
   - **构建输出目录**：`website`
4. 保存并部署。之后每次提交（含每日自动更新提交）都会自动重新部署。

## 数据说明

- 价格为**每百万 Token（1M tokens）**的 API 调用价格，单位为美元(USD)或人民币(CNY)
- 价格来源为各厂商官网公开价格页，每天自动抓取
- 表格中标注「官网」表示当天抓取成功；标注「参考」表示抓取失败时使用的内置参考价（基于官方公开定价整理），请以厂商官网为准
- `history.json` 从部署之日起按天积累，趋势图需要数天数据后才有完整曲线

## 维护与扩展

- **增加新模型**：修改对应 `spiders/<厂商>.py` 中的 `MODEL_CATALOG`，参考价格页格式编写解析逻辑
- **增加新厂商**：在 `spiders/` 新建爬虫类（继承 `spiders/base.py` 的 `Spider`），并在 `crawler/config.py` 的 `SPIDER_MODULES` 中注册
- **维护优惠活动**：直接编辑 `data/promotions.json` 提交即可（支持多行，`date`、`description`、`url` 可选）
- **调整抓取频率**：修改 `.github/workflows/daily_update.yml` 中的 `cron` 表达式

## 免责声明

本项目数据仅用于价格参考，实际调用价格以各厂商官方发布为准。
