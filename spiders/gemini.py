"""Google Gemini 价格采集。

价格页 https://ai.google.dev/gemini-api/docs/pricing 为文档站，
价格以表格形式展示。解析策略：
1. 页面纯文本按「模型名 + Input/Output 关键词」匹配；
2. 匹配不到时解析表格，取模型行中前两个 $ 价格作为输入/输出价。

注意：Gemini 2.5 Pro 等模型存在按上下文分段定价，此处取基础档。
内置参考价基于官方公开定价整理，仅作兜底展示，请以官网为准。
"""
import re

from spiders.base import Spider, find_io_prices


class GeminiSpider(Spider):
    provider = "Google"
    pricing_url = "https://ai.google.dev/gemini-api/docs/pricing"

    # 单位：USD / 百万 Token
    MODEL_CATALOG = {
        "Gemini 2.5 Pro": {"category": "LLM", "context_window": 200000, "input_price": 1.25, "output_price": 10.00},
        "Gemini 2.5 Flash": {"category": "LLM", "context_window": 1000000, "input_price": 0.30, "output_price": 2.50},
        "Gemini 2.5 Flash-Lite": {"category": "LLM", "context_window": 1000000, "input_price": 0.10, "output_price": 0.40},
        "Gemini 2.5 Flash Image": {"category": "Multimodal", "context_window": 1000000, "input_price": 0.30, "output_price": 3.50},
        "Gemini 2.0 Flash": {"category": "LLM", "context_window": 1000000, "input_price": 0.10, "output_price": 0.40},
    }

    def parse(self, html: str) -> list:
        soup = self.soup(html)
        text = self.plain_text(html)
        prices = []

        # 策略 1：文本关键词匹配
        for model, meta in self.MODEL_CATALOG.items():
            inp, out = find_io_prices(text, model)
            if inp is not None and out is not None:
                prices.append(self._official_entry(model, meta, inp, out))

        # 策略 2：表格行匹配（文本匹配未覆盖的模型）
        found = {(p["provider"], p["model"]) for p in prices}
        for row in self.parse_tables(soup):
            joined = " ".join(row)
            for model, meta in self.MODEL_CATALOG.items():
                if (self.provider, model) in found:
                    continue
                if not re.search(re.escape(model), joined, re.I):
                    continue
                dollars = re.findall(r"\$\s?([\d][\d.,]*)", joined)
                if len(dollars) >= 2:
                    prices.append(self._official_entry(
                        model, meta, self._to_float(dollars[0]), self._to_float(dollars[1])))
                    found.add((self.provider, model))
        return prices
