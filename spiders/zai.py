"""Z.ai（智谱国际站）价格采集。

价格页 https://docs.z.ai/guides/overview/pricing 为文档站，价格以「$X」表述。
解析策略：按模型名 + Input/输出关键词匹配（复用 base.find_io_prices）。

内置参考价基于官方公开定价整理，仅作兜底展示，请以官网为准。
"""
from spiders.base import Spider, find_io_prices


class ZaiSpider(Spider):
    provider = "Z.ai"
    pricing_url = "https://docs.z.ai/guides/overview/pricing"

    # 单位：USD / 百万 Token
    MODEL_CATALOG = {
        "GLM-5.3": {"category": "LLM", "context_window": 200000, "input_price": 1.4, "output_price": 4.4, "currency": "USD"},
    }

    def parse(self, html: str) -> list:
        text = self.plain_text(html)
        prices = []
        for model, meta in self.MODEL_CATALOG.items():
            inp, out = find_io_prices(text, model)
            if inp is not None and out is not None:
                prices.append(self._official_entry(model, meta, inp, out, currency="USD"))
        return prices
