"""OpenRouter 官方 API 价格采集（真实价格源）。

使用 OpenRouter 公开 API（https://openrouter.ai/api/v1/models）获取全量模型的
实时价格。该接口返回 JSON，价格为 USD / token，乘以 1e6 即每百万 Token 计价。
覆盖数百个模型，含国内厂商（DeepSeek / Qwen / GLM / Kimi / MiniMax / 腾讯 / 字节 等）
的转售真实价。

这是爬虫体系的「真实价格基座」：所有能从此 API 拿到的模型都标记为 source=openrouter_api，
官网爬虫的 official 结果会覆盖同名模型，官网爬虫的 fallback（写死参考价）仅在该模型
未被 API 覆盖时保留，避免假价与真价并存。
"""
import logging

import requests

from spiders.base import Spider

logger = logging.getLogger(__name__)

API_URL = "https://openrouter.ai/api/v1/models"

# 厂商 id -> 展示名（与官网爬虫命名尽量对齐）
_PROVIDER_NAMES = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "google": "Google",
    "meta": "Meta",
    "deepseek": "DeepSeek",
    "qwen": "Alibaba",
    "z-ai": "Z.ai",
    "moonshotai": "Kimi",
    "minimax": "MiniMax",
    "tencent": "Tencent",
    "bytedance-seed": "ByteDance Seed",
    "bytedance": "ByteDance",
    "stepfun": "StepFun",
    "x-ai": "xAI",
    "mistralai": "Mistral",
    "cohere": "Cohere",
    "amazon": "AWS",
}

# 厂商 id -> 真实官网（优先官方定价页）。命中则 official_page 指向厂商官网；
# 未命中（小众/社区模型往往无独立官网）回退到 OpenRouter 模型页，由前端标注为「OpenRouter」而非「官网」。
_PROVIDER_OFFICIAL = {
    "openai": "https://openai.com/api/pricing/",
    "anthropic": "https://www.anthropic.com/pricing",
    "google": "https://ai.google.dev/pricing",
    "meta": "https://www.llama.com/",
    "meta-llama": "https://www.llama.com/",
    "deepseek": "https://api-docs.deepseek.com/quick_start/pricing",
    "qwen": "https://help.aliyun.com/zh/model-studio/models",
    "alibaba": "https://help.aliyun.com/zh/model-studio/models",
    "z-ai": "https://z.ai/",
    "moonshotai": "https://platform.moonshot.cn/",
    "minimax": "https://platform.minimax.io/",
    "tencent": "https://cloud.tencent.com/product/hunyuan",
    "bytedance-seed": "https://volcengine.com/product/doubao",
    "bytedance": "https://volcengine.com/product/doubao",
    "stepfun": "https://platform.stepfun.com/",
    "x-ai": "https://x.ai/api",
    "mistralai": "https://mistral.ai/products/pricing",
    "cohere": "https://cohere.com/pricing",
    "amazon": "https://aws.amazon.com/bedrock/pricing/",
    "aws": "https://aws.amazon.com/bedrock/pricing/",
    "microsoft": "https://azure.microsoft.com/en-us/products/ai-services/openai-service",
    "nvidia": "https://build.nvidia.com/",
    "perplexity": "https://www.perplexity.ai/pricing",
    "xiaomi": "https://mimo.mi.com/",
    "fireworks": "https://fireworks.ai/pricing",
    "upstage": "https://upstage.ai/",
    "sakana": "https://sakana.ai/",
    "rekaai": "https://www.reka.ai/",
    "ibm-granite": "https://www.ibm.com/products/watsonx/ai/models",
    "ibm": "https://www.ibm.com/products/watsonx/ai/models",
    "poolside": "https://poolside.ai/",
    "writer": "https://writer.com/api",
    "arcee-ai": "https://www.arcee.ai/",
    "nousresearch": "https://nousresearch.com/",
    "meituan": "https://www.meituan.com/",
    "baichuan": "https://www.baichuan-ai.com/",
    # 小众 / 社区模型：确有官方站点（公司站或 HuggingFace 组织页）的指向官网；
    # 无独立官网的（aion-labs / perceptron / mancer）保留 OpenRouter 模型页，前端标黄「OpenRouter ↗」。
    "scaledown": "https://scaledown.ai/",
    "unbiased": "https://unbiased.ai/",
    "prism-ml": "https://prismml.com/",
    "inference-net": "https://inference.net/",
    "inclusionai": "https://huggingface.co/inclusionAI",
    "inception": "https://www.inceptionlabs.ai/",
    "nex-agi": "https://huggingface.co/nex-agi",
    "thinkingmachines": "https://www.thinkingmachines.ai/",
    "relace": "https://relace.ai/",
    "thedrummer": "https://huggingface.co/TheDrummer",
    "cognitivecomputations": "https://huggingface.co/cognitivecomputations",
    "morph": "https://www.morphllm.com/",
    "sao10k": "https://huggingface.co/Sao10K",
    "anthracite-org": "https://huggingface.co/anthracite-org",
    "undi95": "https://huggingface.co/Undi95",
    "gryphe": "https://huggingface.co/Gryphe",
}


class OpenRouterSpider(Spider):
    provider = "OpenRouter"
    pricing_url = "https://openrouter.ai/models"

    def crawl(self):
        """调用 OpenRouter API 获取全量真实价格（覆盖基类 HTML 抓取流程）。"""
        if self.offline:
            logger.info("[OpenRouter] 离线模式跳过 API 请求")
            return []
        try:
            resp = requests.get(
                API_URL,
                timeout=30,
                headers={"User-Agent": self.session.headers.get("User-Agent", "")},
            )
            resp.raise_for_status()
            models = resp.json().get("data", [])
        except Exception as exc:
            logger.warning("[OpenRouter] API 请求失败，放弃该真实价源: %s", exc)
            return []

        prices = []
        for m in models:
            mid = m.get("id", "")
            if "/" not in mid:
                continue
            prov_raw, model = mid.split("/", 1)
            prov = _PROVIDER_NAMES.get(prov_raw.strip().lower(), prov_raw.strip().title())
            pricing = m.get("pricing", {})
            try:
                inp = float(pricing.get("prompt", 0) or 0) * 1_000_000
                out = float(pricing.get("completion", 0) or 0) * 1_000_000
            except (TypeError, ValueError):
                continue
            if inp <= 0 and out <= 0:
                continue
            prices.append({
                "provider": prov,
                "model": model,
                "category": "LLM",
                "context_window": m.get("context_length"),
                "input_price": round(inp, 4),
                "output_price": round(out, 4),
                "currency": "USD",
                "unit": "per_1M_tokens",
                "source": "openrouter_api",
                "official_page": _PROVIDER_OFFICIAL.get(
                    prov_raw.strip().lower().lstrip("~"),
                    "https://openrouter.ai/models/" + mid,
                ),
            })
        logger.info("[OpenRouter] API 获取 %d 个真实价格", len(prices))
        return prices

    def parse(self, html: str) -> list:
        # 本爬虫走 API（crawl 已重写），不使用 HTML 解析；保留空实现以满足抽象基类要求
        return []
