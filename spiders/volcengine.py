"""火山引擎方舟（豆包）价格采集。

价格页 https://www.volcengine.com/pricing 为动态加载页面，模型单价在
控制台（ai.volcengine.com 模型广场）内，静态解析成功率低，主要依赖
内置参考价兜底。解析策略：在纯文本中匹配模型名与「X元」表述。

内置参考价基于官方公开定价整理，仅作兜底展示，请以官网为准。
"""
import re

from spiders.base import Spider


class VolcengineSpider(Spider):
    provider = "火山引擎"
    pricing_url = "https://www.volcengine.com/pricing?tab=1&product=ark_subscription"

    # 单位：CNY / 百万 Token
    MODEL_CATALOG = {
        "豆包2.1 Pro": {"category": "LLM", "context_window": 262144, "input_price": 6.0, "output_price": 30.0, "currency": "CNY"},
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
