"""阿里云百炼（通义千问）价格采集。

价格页 https://help.aliyun.com/zh/model-studio/models 为动态加载页面，
静态解析成功率较低，主要依赖内置参考价兜底。
解析策略：表格行中同时包含模型名与「X元」表述时，取前两个人民币价格。

内置参考价基于官方公开定价整理，仅作兜底展示，请以官网为准。
"""
import re

from spiders.base import Spider


class QwenSpider(Spider):
    provider = "阿里云"
    pricing_url = "https://help.aliyun.com/zh/model-studio/models"

    # 单位：CNY / 百万 Token
    MODEL_CATALOG = {
        "Qwen3.8-Max": {"category": "LLM", "context_window": 128000, "input_price": 12.0, "output_price": 36.0, "currency": "CNY"},
        "qwen3-max": {"category": "LLM", "context_window": 128000, "input_price": 3.0, "output_price": 25.0, "currency": "CNY"},
        "qwen-max": {"category": "LLM", "context_window": 32768, "input_price": 16.8, "output_price": 67.2, "currency": "CNY"},
        "qwen-plus": {"category": "LLM", "context_window": 131072, "input_price": 0.8, "output_price": 2.0, "currency": "CNY"},
        "qwen-turbo": {"category": "LLM", "context_window": 1000000, "input_price": 0.3, "output_price": 0.6, "currency": "CNY"},
        "qwen-long": {"category": "LLM", "context_window": 10000000, "input_price": 0.5, "output_price": 2.0, "currency": "CNY"},
        "qwen3-coder-plus": {"category": "LLM", "context_window": 262144, "input_price": 0.5, "output_price": 2.0, "currency": "CNY"},
    }

    def parse(self, html: str) -> list:
        soup = self.soup(html)
        prices = []
        for row in self.parse_tables(soup):
            joined = " ".join(row)
            for model, meta in self.MODEL_CATALOG.items():
                if model not in joined or "元" not in joined:
                    continue
                nums = re.findall(r"([\d][\d.,]*)\s*元", joined)
                if len(nums) >= 2:
                    prices.append(self._official_entry(
                        model, meta, self._to_float(nums[0]), self._to_float(nums[1]), currency="CNY"))
        return prices
