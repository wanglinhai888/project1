"""AI 大模型价格雷达 - 发布层。

把 crawler 已经生成的 today.json（含 changes / summary）渲染成可发布文本，
供公众号、Telegram、邮件等渠道复用。第 0 步只做"内容生成"，不含任何平台凭据。
"""
