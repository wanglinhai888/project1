"""硅基流动（SiliconFlow）聚合平台价格采集。

价格页 https://cloud.siliconflow.cn/pricing 为动态加载页面，价格按模型浮动。
该平台无统一价目表，解析成功率低，主要依赖内置参考价兜底。
解析策略：表格行中同时包含模型名与「X元」表述时提取价格。

内置参考价基于官方公开定价整理，仅作兜底展示，请以官网为准。
"""
import re

from spiders.base import Spider


class SiliconFlowSpider(Spider):
    provider = "硅基流动"
    pricing_url = "https://cloud.siliconflow.cn/pricing"

    # 单位：CNY / 百万 Token；聚合平台价格因模型而异，以下为主流模型参考价
    MODEL_CATALOG = {
        "DeepSeek-V4-Flash": {"category": "LLM", "context_window": 1000000, "input_price": 1.2, "output_price": 3.0, "currency": "CNY"},
        "Qwen3-Max": {"category": "LLM", "context_window": 128000, "input_price": 2.4, "output_price": 8.0, "currency": "CNY"},
    }

    def parse(self, html: str) -> list:
        rows = self.parse_tables(self.soup(html))
        prices = []
        for row in rows:
            joined = " ".join(row)
            for model, meta in self.MODEL_CATALOG.items():
                if model not in joined or "元" not in joined:
                    continue
                nums = re.findall(r"([\d][\d.,]*)\s*元", joined)
                if len(nums) >= 2:
                    prices.append(self._official_entry(
                        model, meta, self._to_float(nums[0]), self._to_float(nums[1]), currency="CNY"))
        return prices
