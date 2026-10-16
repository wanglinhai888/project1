# AI大模型价格雷达 V1.0 数据库替代方案（JSON数据结构）说明

版本：V1.0

---

# 1. 设计背景

传统系统通常采用：

- MySQL
- PostgreSQL
- SQLite

保存模型价格数据。

但是本项目：

- 每天只更新一次
- 数据量较小
- 无复杂查询
- 个人使用

因此V1.0采用：

> JSON文件作为数据存储方案

---

# 2. JSON存储结构


目录：

```
data

├── models.json

├── today.json

├── history.json

└── promotions.json

```

---

# 3. models.json


保存模型基础信息。


示例：

```json
[
 {
   "provider":"OpenAI",
   "model":"GPT-5",
   "category":"LLM",
   "context_window":200000
 }
]
```

字段：

|字段|说明|
|-|-|
|provider|厂商|
|model|模型名称|
|category|模型类型|
|context_window|上下文长度|

---

# 4. history.json


保存历史价格。


示例：

```json
[
 {
  "date":"2026-08-22",
  "model":"GPT-5",
  "input_price":1,
  "output_price":5,
  "currency":"USD"
 }
]
```

特点：

- 永久保存
- 不覆盖旧数据
- 支持趋势分析


---

# 5. today.json


保存当天数据。


示例：

```json
{
 "date":"2026-08-22",

 "changes":[
  {
   "model":"GPT-5",
   "type":"price_down",
   "change":"20%"
  }
 ]
}
```

网站首页优先读取该文件。

---

# 6. promotions.json


保存优惠活动。


示例：

```json
[
 {
  "provider":"Google",
  "title":"Gemini免费额度增加",
  "date":"2026-08-22"
 }
]
```

---

# 7. 数据更新流程


```
官网

↓

Python爬虫

↓

标准数据模型

↓

读取history.json

↓

计算变化

↓

生成today.json

↓

提交GitHub

```

---

# 8. JSON方案优点


## 成本

0元。


## 部署

无需数据库服务器。


## 维护

Git自动保存历史。


## 扩展

未来可以：

JSON

↓

SQLite

↓

PostgreSQL


平滑迁移。

---

# 9. JSON方案限制


不适合：

- 大量用户查询
- 实时搜索
- 多用户修改


如果未来公开访问量增加：

升级数据库即可。

---

# 10. V1.0结论


采用：

```
JSON + Git历史版本

```

满足：

- 个人使用
- 免费运行
- 自动更新
- 长期数据积累