# AI大模型价格雷达 V1.0 GitHub Actions自动化部署说明

版本：V1.0

---

# 1. 目标

利用 GitHub Actions 实现：

每天北京时间08:00：

自动运行价格采集程序。

流程：

```
定时触发

↓

运行Python程序

↓

采集模型价格

↓

生成JSON

↓

提交GitHub

↓

Cloudflare Pages自动部署

```

---

# 2. 工作流程


```
GitHub Actions Scheduler

            |

            ↓

Python Environment

            |

            ↓

Crawler

            |

            ↓

JSON Generator

            |

            ↓

Git Commit

            |

            ↓

Cloudflare Deploy

```

---

# 3. Workflow文件


路径：

```
.github/workflows/daily_update.yml
```

---

# 4. 执行步骤


## Step 1

拉取代码：

```
checkout repository
```


---

## Step 2

安装Python环境：

版本：

```
Python 3.12
```

---

## Step 3

安装依赖：

```
pip install -r requirements.txt
```

---

## Step 4

运行程序：

```
python crawler/main.py
```

---

## Step 5

提交更新：

```
git add data

git commit

git push
```

---

# 5. 定时规则


目标：

每天北京时间08:00。


GitHub Actions使用UTC时间。


北京时间：

UTC+8


因此：

```
00:00 UTC

=

08:00 北京时间

```

---

# 6. 失败处理


增加：

- 日志输出
- 错误捕获
- 重试机制


例如：

```
OpenAI采集失败

↓

记录日志

↓

继续执行Claude

↓

最终生成报告

```

---

# 7. Cloudflare Pages部署


流程：

```
GitHub Repository

        |

        ↓

Cloudflare Pages

        |

        ↓

Static Website

```

---

# 8. 部署配置


项目：

```
AIPriceRadar
```


网站目录：

```
website
```


构建方式：

静态部署。


---

# 9. 免费运行成本


组件：

|组件|费用|
|-|-|
|GitHub|免费|
|GitHub Actions|免费额度|
|Cloudflare Pages|免费|
|数据库|无|

总成本：

0元。

---

# 10. 后续升级


未来可以增加：

- 多时间任务
- 邮件通知
- Telegram通知
- AI日报生成
- 自动发现新模型

---

# 11. 最终运行效果


每天：

08:00

↓

自动抓取

↓

自动分析

↓

自动更新网站

↓

用户访问最新AI价格信息