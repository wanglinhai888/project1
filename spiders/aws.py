"""AWS Amazon Nova 价格采集。

价格页 https://aws.amazon.com/nova/pricing/ 列出 Nova 系列模型美元价格。
该页为动态加载，解析成功率低，主要依赖内置参考价兜底。
解析策略：在纯文本中匹配模型名与「$X」表述。

内置参考价基于官方公开定价整理，仅作兜底展示，请以官网为准。
"""
import re

from spiders.base import Spider


class AWSSpider(Spider):
    provider = "AWS"
    pricing_url = "https://aws.amazon.com/nova/pricing/"

    # 单位：USD / 百万 Token
    MODEL_CATALOG = {
        "Amazon Nova Pro": {"category": "LLM", "context_window": 300000, "input_price": 0.8, "output_price": 3.2, "currency": "USD"},
    }

    def parse(self, html: str) -> list:
        text = self.plain_text(html)
        prices = []
        for model, meta in self.MODEL_CATALOG.items():
            idx = text.find(model)
            if idx == -1:
                continue
            seg = text[idx: idx + 2000]
            nums = re.findall(r"\$\s?([\d][\d.,]*)", seg)
            if len(nums) >= 2:
                prices.append(self._official_entry(
                    model, meta, self._to_float(nums[0]), self._to_float(nums[1]), currency="USD"))
        return prices
