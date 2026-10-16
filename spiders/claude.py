"""Anthropic Claude 价格采集。

价格页 https://www.claude.com/pricing（原 www.anthropic.com/pricing 会重定向至此）
为服务端渲染，页面文本形如 "$5 per million input tokens" / "$25 per million output tokens"，
按「模型名 + Input/Output 关键词」匹配价格。

内置参考价基于官方公开定价整理，仅作兜底展示，请以官网为准。
"""
from spiders.base import Spider, find_io_prices


class ClaudeSpider(Spider):
    provider = "Anthropic"
    pricing_url = "https://www.claude.com/pricing"

    # 单位：USD / 百万 Token
    MODEL_CATALOG = {
        "Claude Opus 4.5": {"category": "LLM", "context_window": 200000, "input_price": 5.00, "output_price": 25.00},
        "Claude Opus 4.1": {"category": "LLM", "context_window": 200000, "input_price": 15.00, "output_price": 75.00},
        "Claude Sonnet 4.5": {"category": "LLM", "context_window": 200000, "input_price": 3.00, "output_price": 15.00},
        "Claude Sonnet 4": {"category": "LLM", "context_window": 200000, "input_price": 3.00, "output_price": 15.00},
        "Claude Haiku 4.5": {"category": "LLM", "context_window": 200000, "input_price": 1.00, "output_price": 5.00},
        "Claude Haiku 3.5": {"category": "LLM", "context_window": 200000, "input_price": 0.80, "output_price": 4.00},
    }

    def parse(self, html: str) -> list:
        text = self.plain_text(html)
        prices = []
        for model, meta in self.MODEL_CATALOG.items():
            inp, out = find_io_prices(text, model)
            if inp is not None and out is not None:
                prices.append(self._official_entry(model, meta, inp, out))
        return prices
