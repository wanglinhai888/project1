"""小米 MiMo 价格采集。

价格页 https://mimo.mi.com/models/zh-CN/mimo-v2.5 为官网模型介绍页，
价格以「X元」表述。解析策略：在纯文本中匹配模型名与「X元」表述。

内置参考价基于官方公开定价整理，仅作兜底展示，请以官网为准。
"""
import re

from spiders.base import Spider


class XiaomiSpider(Spider):
    provider = "Xiaomi MIMO"
    pricing_url = "https://mimo.mi.com/models/zh-CN/mimo-v2.5"

    # 单位：CNY / 百万 Token
    MODEL_CATALOG = {
        "MiMo-V2.5 Pro": {"category": "LLM", "context_window": 200000, "input_price": 3.0, "output_price": 6.0, "currency": "CNY"},
        "MiMo-V2.5 (标准版)": {"category": "LLM", "context_window": 200000, "input_price": 1.0, "output_price": 2.0, "currency": "CNY"},
    }

    def parse(self, html: str) -> list:
        text = self.plain_text(html)
        prices = []
        for model, meta in self.MODEL_CATALOG.items():
            idx = text.find(model)
            if idx == -1:
                continue
            seg = text[idx: idx + 2000]
            nums = re.findall(r"([\d][\d.,]*)\s*元", seg)
            if len(nums) >= 2:
                prices.append(self._official_entry(
                    model, meta, self._to_float(nums[0]), self._to_float(nums[1]), currency="CNY"))
        return prices
