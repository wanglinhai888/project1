# AI大模型价格雷达 V1.0 开发计划

版本：V1.0\
项目名称：AI Price Radar

## 1. 项目目标

开发一个零成本运行的 AI 大模型价格监控网站：

-   每天北京时间 08:00 自动运行
-   自动采集主流大模型价格
-   检测价格变化
-   收集优惠活动和新模型信息
-   自动生成网站数据
-   使用免费托管发布网站

目标用户： 个人使用，后续可扩展为公开 AI 情报网站。

------------------------------------------------------------------------

# 2. 技术路线

整体架构：

    用户浏览器
        |
    Cloudflare Pages
        |
    静态网站(Vue3 + ECharts)
        |
    GitHub仓库
        |
    GitHub Actions
        |
    Python数据采集程序
        |
    AI厂商官网

技术栈：

  模块       技术
  ---------- ---------------------------------------
  数据采集   Python 3.12
  网页解析   Requests + BeautifulSoup + Playwright
  数据格式   JSON
  网站       Vue3 + ECharts
  托管       Cloudflare Pages
  自动任务   GitHub Actions

------------------------------------------------------------------------

# 3. 项目目录

    AIPriceRadar

    ├── crawler
    │   ├── main.py
    │   ├── config.py
    │   └── requirements.txt
    │
    ├── spiders
    │   ├── openai.py
    │   ├── claude.py
    │   ├── gemini.py
    │   └── deepseek.py
    │
    ├── processors
    │   ├── price_compare.py
    │   └── json_export.py
    │
    ├── data
    │   ├── today.json
    │   └── history.json
    │
    ├── website
    │   ├── index.html
    │   ├── app.js
    │   └── style.css
    │
    └── .github
        └── workflows
            └── daily_update.yml

------------------------------------------------------------------------

# 4. 数据设计

## Model

保存模型基础信息：

-   厂商
-   模型名称
-   类型
-   上下文长度

示例：

``` json
{
  "provider":"OpenAI",
  "name":"GPT-5",
  "context":200000
}
```

------------------------------------------------------------------------

## PriceHistory

保存每日价格：

``` json
{
  "model":"GPT-5",
  "input_price":1,
  "output_price":5,
  "currency":"USD",
  "date":"2026-08-22"
}
```

规则：

-   不覆盖历史
-   每天生成快照

------------------------------------------------------------------------

# 5. 数据采集模块

第一阶段支持：

## 国际

-   OpenAI
-   Anthropic Claude
-   Google Gemini

## 国内

-   DeepSeek
-   阿里百炼
-   智谱AI

每个厂商独立爬虫：

    spiders
     |
     ├── openai.py
     ├── claude.py
     └── deepseek.py

统一接口：

``` python
class Spider:
    def crawl(self):
        return data
```

------------------------------------------------------------------------

# 6. 自动更新流程

每天 08:00：

    GitHub Actions启动

    ↓

    安装Python环境

    ↓

    执行爬虫

    ↓

    获取最新价格

    ↓

    比较历史数据

    ↓

    生成JSON

    ↓

    提交GitHub

    ↓

    Cloudflare自动部署

------------------------------------------------------------------------

# 7. 网站功能

首页展示：

## 今日价格变化

例如：

-   GPT-5 降价20%
-   DeepSeek 新模型发布
-   Gemini 免费额度增加

## 当前价格表

显示：

-   模型
-   输入价格
-   输出价格

## 历史趋势

使用 ECharts：

-   7天价格趋势
-   30天价格趋势
-   历史变化曲线

------------------------------------------------------------------------

# 8. 开发任务

## TASK-001

初始化GitHub项目

完成：

-   创建仓库
-   添加README

## TASK-002

搭建Python环境

完成：

-   requirements.txt
-   基础运行环境

## TASK-003

定义数据结构

完成：

-   Model
-   Price
-   History

## TASK-004

实现OpenAI价格采集

## TASK-005

实现Claude价格采集

## TASK-006

实现DeepSeek价格采集

## TASK-007

实现价格变化分析

## TASK-008

生成JSON数据

## TASK-009

开发网站首页

## TASK-010

接入趋势图

## TASK-011

配置GitHub Actions

## TASK-012

部署Cloudflare Pages

------------------------------------------------------------------------

# 9. V1.0完成标准

系统每天自动：

    采集价格
        |
    分析变化
        |
    生成数据
        |
    更新网站

网站可以查看：

-   当前模型价格
-   历史价格
-   降价信息
-   新模型信息

------------------------------------------------------------------------

# 10. 后续规划

## V1.1

增加：

-   免费额度监控
-   模型排行榜

## V1.2

增加：

AI成本计算器

## V2.0

增加：

-   AI日报自动生成
-   模型能力评分
-   性价比排行

------------------------------------------------------------------------

# AI开发要求

请严格按照本文档实现：

1.  使用Python开发采集程序。
2.  使用GitHub Actions每天北京时间8点运行。
3.  使用Cloudflare Pages部署网站。
4.  不使用服务器。
5.  不使用数据库。
6.  使用JSON保存数据。
7.  代码模块化。
8.  添加完整README。
9.  第一阶段先支持OpenAI、Claude、DeepSeek。
