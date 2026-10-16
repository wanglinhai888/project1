"""智谱 AI（GLM）价格采集。

价格页 https://open.bigmodel.cn/pricing 为静态页面，价格以「X元」表述。
解析策略：按「模型名 + Input/输出关键词」匹配价格。

内置参考价基于官方公开定价整理，仅作兜底展示，请以官网为准。
"""
from spiders.base import Spider, find_io_prices


class ZhipuSpider(Spider):
    provider = "Bigmodel (智谱AI)"
    pricing_url = "https://open.bigmodel.cn/pricing"

    # 单位：CNY / 百万 Token
    MODEL_CATALOG = {
        "GLM-5.2": {"category": "LLM", "context_window": 128000, "input_price": 8.0, "output_price": 28.0, "currency": "CNY"},
        "GLM-5-Turbo": {"category": "LLM", "context_window": 128000, "input_price": 5.0, "output_price": 22.0, "currency": "CNY"},
        "GLM-4.5": {"category": "LLM", "context_window": 128000, "input_price": 5.0, "output_price": 15.0, "currency": "CNY"},
        "GLM-4.5-Air": {"category": "LLM", "context_window": 128000, "input_price": 1.0, "output_price": 3.0, "currency": "CNY"},
        "GLM-4.1": {"category": "LLM", "context_window": 128000, "input_price": 2.0, "output_price": 8.0, "currency": "CNY"},
        "GLM-4-Plus": {"category": "LLM", "context_window": 128000, "input_price": 5.0, "output_price": 15.0, "currency": "CNY"},
        "GLM-4-Flash": {"category": "LLM", "context_window": 128000, "input_price": 0.0, "output_price": 0.0, "currency": "CNY"},
        "GLM-4V-Plus": {"category": "Multimodal", "context_window": 8192, "input_price": 20.0, "output_price": 20.0, "currency": "CNY"},
    }

    def parse(self, html: str) -> list:
        text = self.plain_text(html)
        prices = []
        for model, meta in self.MODEL_CATALOG.items():
            inp, out = find_io_prices(text, model)
            if inp is not None and out is not None:
                prices.append(self._official_entry(model, meta, inp, out, currency="CNY"))
        return prices
