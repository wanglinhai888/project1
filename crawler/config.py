"""全局配置：厂商 URL、请求参数、数据目录。

所有路径、URL、超时等参数集中在此，避免散落硬编码。
"""
from pathlib import Path

# 项目根目录（crawler/config.py -> 项目根）
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 数据目录（git 提交，用于长期积累历史）
DATA_DIR = PROJECT_ROOT / "data"

# 网站数据目录（crawler 运行后同步，Cloudflare Pages 直接发布 website/）
WEBSITE_DATA_DIR = PROJECT_ROOT / "website" / "data"

# 请求参数
REQUEST_TIMEOUT = 20          # 单次请求超时（秒）
RETRY_TIMES = 3               # 请求失败重试次数
RETRY_BACKOFF = 2             # 重试退避基数（秒）
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# 价格变化判定阈值：相对变化超过 0.5% 记为一次价格变动
PRICE_CHANGE_THRESHOLD = 0.005

# 数据文件
DATA_FILES = {
    "models": DATA_DIR / "models.json",
    "today": DATA_DIR / "today.json",
    "history": DATA_DIR / "history.json",
    "promotions": DATA_DIR / "promotions.json",
}

# 默认时区（北京时间）
TIMEZONE = "Asia/Shanghai"

# 爬虫注册表：模块路径字符串，由 main.py 动态加载
SPIDER_MODULES = [
    "spiders.openai.OpenAISpider",
    "spiders.claude.ClaudeSpider",
    "spiders.gemini.GeminiSpider",
    "spiders.deepseek.DeepSeekSpider",
    "spiders.qwen.QwenSpider",
    "spiders.zhipu.ZhipuSpider",
    "spiders.moonshot.KimiCNSpider",
    "spiders.moonshot.KimiGlobalSpider",
    "spiders.volcengine.VolcengineSpider",
    "spiders.minimax.MiniMaxCNSpider",
    "spiders.minimax.MiniMaxGlobalSpider",
    "spiders.zai.ZaiSpider",
    "spiders.xiaomi.XiaomiSpider",
    "spiders.tencent.TencentSpider",
    "spiders.openrouter.OpenRouterSpider",
    "spiders.siliconflow.SiliconFlowSpider",
    "spiders.byteplus.BytePlusSpider",
    "spiders.aws.AWSSpider",
    "spiders.modelark.ModelArkSpider",
]
