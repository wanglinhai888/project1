"""发布层入口：生成每日价格变化摘要（第 0 步，无外部依赖 / 凭据）。

用法:
    python publisher/main.py                  # 纯文本打印到控制台
    python publisher/main.py --format markdown
    python publisher/main.py --format both --out publisher/output   # 保存 txt + md

后续接渠道时，各 sink 直接 import build_summary / load_today 即可复用本模块。
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Windows 控制台默认 GBK，无法输出 emoji/中文，强制 UTF-8 避免 UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from publisher.summary import build_summary, load_today


def main():
    parser = argparse.ArgumentParser(description="生成每日价格变化发布摘要")
    parser.add_argument(
        "--format", choices=["text", "markdown", "both"], default="text",
        help="输出格式（默认 text）",
    )
    parser.add_argument("--out", default=None, help="输出目录，保存摘要文件")
    parser.add_argument("--today", default=None, help="指定 today.json 路径（默认用配置路径）")
    args = parser.parse_args()

    today = load_today(args.today)
    result = build_summary(today)

    if args.format in ("text", "both"):
        print(result["text"])
    if args.format == "markdown":
        print(result["markdown"])
    elif args.format == "both":
        print("\n------ Markdown ------\n")
        print(result["markdown"])

    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        if args.format in ("text", "both"):
            (out_dir / f"summary_{result['date']}.txt").write_text(
                result["text"], encoding="utf-8")
            saved.append("txt")
        if args.format in ("markdown", "both"):
            (out_dir / f"summary_{result['date']}.md").write_text(
                result["markdown"], encoding="utf-8")
            saved.append("md")
        print(f"\n已保存到 {out_dir}（{', '.join(saved)}）")


if __name__ == "__main__":
    main()
