"""邮件推送 sink：把 AI 润色文章发到指定邮箱，便于人工再发布到公众号。

走标准 SMTP（QQ/163/Gmail 等均可），无 IP 白名单限制，可直接在 CI 运行。
配置（GitHub Secrets 或环境变量）：
  EMAIL_TO      收件人（必填，仅从 Secrets 读取，代码中不出现明文邮箱）
  EMAIL_FROM    发件人邮箱（不填则默认等于 EMAIL_TO，即发给自己）
  EMAIL_PASSWORD 邮箱"授权码"（注意：不是登录密码！QQ/163 需在邮箱设置里开启 SMTP 后生成）
  EMAIL_SMTP_HOST  SMTP 服务器（默认 smtp.qq.com）
  EMAIL_SMTP_PORT  SMTP 端口（默认 465，SSL）

邮件内容：HTML 正文（标题/摘要/正文/FAQ）+ 末尾附"源 Markdown"方便一键复制。
遵循失败降级：无凭据 / 发送失败 → 打印日志跳过，不阻断流水线。
依赖：标准库 smtplib/ssl/email + publisher.sinks.wechat.md_to_html（复用 MD→HTML）。
"""
import argparse
import email.utils
import json
import os
import smtplib
import ssl
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crawler.config import DATA_DIR
from publisher.sinks.wechat import md_to_html


def _find_article_json(explicit=None):
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p
    candidates = sorted(DATA_DIR.glob("article_*.json"))
    return candidates[-1] if candidates else None


def send_email(article):
    host = os.environ.get("EMAIL_SMTP_HOST", "smtp.qq.com")
    port = int(os.environ.get("EMAIL_SMTP_PORT", "465"))
    user = os.environ.get("EMAIL_FROM") or os.environ.get("EMAIL_TO")
    pwd = os.environ.get("EMAIL_PASSWORD")
    to = os.environ.get("EMAIL_TO")

    if not to:
        print("[email] 未配置 EMAIL_TO（收件人），跳过邮件发送。请在 GitHub Secrets 中设置 EMAIL_TO。")
        return
    if not (user and pwd):
        print("[email] 未配置 EMAIL_FROM/EMAIL_PASSWORD，跳过邮件发送。")
        return

    subject = article.get("title") or "AI 大模型价格日报"
    digest = article.get("meta_description", "")
    body_html = md_to_html(article.get("article", ""))

    faqs = article.get("faq") or []
    if faqs:
        body_html += "<h2>常见问题（FAQ）</h2><ul>"
        for f in faqs:
            body_html += (
                f"<li><strong>{f.get('q', '')}</strong><br>{f.get('a', '')}</li>"
            )
        body_html += "</ul>"

    # 末尾附源 Markdown，方便手动复制发布到公众号
    raw_md = article.get("article", "")
    body_html += (
        "<hr><h3>源 Markdown（可直接复制）</h3>"
        f"<pre style='white-space:pre-wrap;word-break:break-all;'>{raw_md}</pre>"
    )

    html_msg = f"""\
<html><body>
<p>{digest}</p>
{body_html}
</body></html>"""

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = user
    message["To"] = to
    message["Date"] = email.utils.formatdate(localtime=True)
    message.attach(MIMEText(html_msg, "html", "utf-8"))
    # 纯文本兜底（含源 Markdown，便于复制）
    message.attach(MIMEText(raw_md or digest, "plain", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context) as server:
        server.login(user, pwd)
        server.send_message(message)
    print(f"[email] 已发送文章《{subject}》至 {to}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article", default=None)
    args = ap.parse_args()

    to = os.environ.get("EMAIL_TO")
    if not to:
        print("[email] 未配置 EMAIL_TO（收件人），跳过邮件发送。请在 GitHub Secrets 中设置 EMAIL_TO。")
        return
    user = os.environ.get("EMAIL_FROM") or to
    if not (user and os.environ.get("EMAIL_PASSWORD")):
        print("[email] 未配置 EMAIL_FROM/EMAIL_PASSWORD，跳过邮件发送（不阻断流程）。")
        return

    path = _find_article_json(args.article)
    if not path:
        print("[email] 未找到 article_*.json，跳过邮件发送。")
        return

    article = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        send_email(article)
    except Exception as exc:
        print(f"[email] 邮件发送失败，跳过: {exc}")


if __name__ == "__main__":
    main()
