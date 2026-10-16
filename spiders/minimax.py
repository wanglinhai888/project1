"""MiniMax 价格采集。

国内站 https://platform.minimaxi.com/subscribe/token-plan 与国际站
https://platform.minimax.io/subscribe/token-plan 均为 SPA 页面，静态解析
成功率低，主要依赖内置参考价兜底。解析策略：在纯文本中匹配模型名与
「X元 / $X」表述。

内置参考价基于官方公开定价整理，仅作兜底展示，请以官网为准。
"""
import re

from spiders.base import Spider


class MiniMaxCNSpider(Spider):
    """MiniMax 国内站（人民币计价）。"""
    provider = "MiniMax CN"
    pricing_url = "https://platform.minimaxi.com/subscribe/token-plan?tab=api-enterprise"

    # 单位：CNY / 百万 Token
    MODEL_CATALOG = {
        "MiniMax-M2.7": {"category": "LLM", "context_window": 262144, "input_price": 2.1, "output_price": 8.4, "currency": "CNY"},
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


class MiniMaxGlobalSpider(Spider):
    """MiniMax 国际站（美元计价）。"""
    provider = "MiniMax Global"
    pricing_url = "https://platform.minimax.io/subscribe/token-plan?tab=api-enterprise"

    # 单位：USD / 百万 Token
    MODEL_CATALOG = {
        "MiniMax-M2.7": {"category": "LLM", "context_window": 262144, "input_price": 0.3, "output_price": 1.2, "currency": "USD"},
    }

    def parse(self, html: str) -> list:
        text = self.plain_text(html)
        prices = []
        for model, meta in self.MODEL_CATALOG.items():
            idx = text.find(model)
            if idx == -1:
                continue
            seg = text[idx: idx + 2000]
            m = re.search(r"\$\s?([\d][\d.,]*)", seg)
            if not m:
                continue
            m2 = re.search(r"\$\s?([\d][\d.,]*)", seg[m.end(): m.end() + 500])
            if m2:
                prices.append(self._official_entry(
                    model, meta, self._to_float(m.group(1)), self._to_float(m2.group(1)), currency="USD"))
        return prices
