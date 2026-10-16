"""Kimi（月之暗面 / Moonshot）价格采集。

国内站 https://platform.kimi.com/docs/pricing/chat-k3 与国际站
https://platform.kimi.ai/docs/pricing/chat-k3 均为文档站，价格以「X元 / $X」表述。
解析策略：按模型名 + 输入/输出关键词匹配（复用 base.find_io_prices）。

内置参考价基于官方公开定价整理，仅作兜底展示，请以官网为准。
"""
from spiders.base import Spider, find_io_prices


class KimiCNSpider(Spider):
    """Kimi 国内站（人民币计价）。"""
    provider = "Kimi CN"
    pricing_url = "https://platform.kimi.com/docs/pricing/chat-k3"

    # 单位：CNY / 百万 Token
    MODEL_CATALOG = {
        "Kimi-K3": {"category": "LLM", "context_window": 1048576, "input_price": 20.0, "output_price": 100.0, "currency": "CNY"},
    }

    def parse(self, html: str) -> list:
        text = self.plain_text(html)
        prices = []
        for model, meta in self.MODEL_CATALOG.items():
            inp, out = find_io_prices(text, model)
            if inp is not None and out is not None:
                prices.append(self._official_entry(model, meta, inp, out, currency="CNY"))
        return prices


class KimiGlobalSpider(Spider):
    """Kimi 国际站（美元计价）。"""
    provider = "Kimi Global"
    pricing_url = "https://platform.kimi.ai/docs/pricing/chat-k3"

    # 单位：USD / 百万 Token
    MODEL_CATALOG = {
        "Kimi-K3": {"category": "LLM", "context_window": 1048576, "input_price": 3.0, "output_price": 15.0, "currency": "USD"},
    }

    def parse(self, html: str) -> list:
        text = self.plain_text(html)
        prices = []
        for model, meta in self.MODEL_CATALOG.items():
            inp, out = find_io_prices(text, model)
            if inp is not None and out is not None:
                prices.append(self._official_entry(model, meta, inp, out, currency="USD"))
        return prices
