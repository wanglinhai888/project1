"""BytePlus（字节跳动海外）价格采集。

价格页 https://docs.byteplus.com/ja/docs/aidap/Billing_items_and_prices_of_large_model_access
为大模型计费说明文档，价格以「$X」表述，部分模型采用阶梯定价。
解析策略：按模型名 + Input/输出关键词匹配（复用 base.find_io_prices）。

内置参考价基于官方公开定价整理，仅作兜底展示，请以官网为准。
"""
from spiders.base import Spider, find_io_prices


class BytePlusSpider(Spider):
    provider = "BytePlus"
    pricing_url = "https://docs.byteplus.com/ja/docs/aidap/Billing_items_and_prices_of_large_model_access"

    # 单位：USD / 百万 Token
    MODEL_CATALOG = {
        "Seed 2.0 Lite": {"category": "LLM", "context_window": 200000, "input_price": 0.25, "output_price": 1.0, "currency": "USD"},
    }

    def parse(self, html: str) -> list:
        text = self.plain_text(html)
        prices = []
        for model, meta in self.MODEL_CATALOG.items():
            inp, out = find_io_prices(text, model)
            if inp is not None and out is not None:
                prices.append(self._official_entry(model, meta, inp, out, currency="USD"))
        return prices
