"""腾讯云混元大模型价格采集。

价格页 https://cloud.tencent.com/document/product/1729/97731 为计费说明文档，
价格以「X元」表述。解析策略：按模型名 + Input/输出关键词匹配。

内置参考价基于官方公开定价整理，仅作兜底展示，请以官网为准。
"""
from spiders.base import Spider, find_io_prices


class TencentSpider(Spider):
    provider = "腾讯云"
    pricing_url = "https://cloud.tencent.com/document/product/1729/97731"

    # 单位：CNY / 百万 Token
    MODEL_CATALOG = {
        "混元 Hy3": {"category": "LLM", "context_window": 256000, "input_price": 1.0, "output_price": 4.0, "currency": "CNY"},
    }

    def parse(self, html: str) -> list:
        text = self.plain_text(html)
        prices = []
        for model, meta in self.MODEL_CATALOG.items():
            inp, out = find_io_prices(text, model)
            if inp is not None and out is not None:
                prices.append(self._official_entry(model, meta, inp, out, currency="CNY"))
        return prices
