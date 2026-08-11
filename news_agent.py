"""
Daily News Agent
- Calls Claude (with web_search) to source India news: Biotechnology + Politics, 3 stories each.
- Claude writes the newspaper-style HTML directly (Fact -> Context -> Consequence per story).
- Emails the digest via Gmail SMTP.
"""

import os
import json
import smtplib
import re
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import anthropic

# ---------- Config ----------

CATEGORIES = ["Biotechnology", "Politics"]
MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """You are a newspaper editor. Use web_search to find real India news from the \
last 24-48 hours across two sections: Biotechnology and Politics (3 stories each).

For each story write three short parts, in plain language a complete beginner can follow, \
no unexplained jargon:
- What happened (1 sentence)
- Background/context (1-2 sentences) - why it matters, what led here
- What's next (1 sentence) - the likely consequence or what to watch

Return a complete, self-contained HTML snippet (no <html>/<head>/<body> tags, just the \
content) styled like a clean newspaper section, using this exact structure per story:

<div style="margin-bottom:18px; padding-bottom:18px; border-bottom:1px solid #ddd;">
  <div style="font-weight:700; font-size:16px; color:#111; margin-bottom:6px;">HEADLINE</div>
  <div style="font-size:13px; color:#333; margin-bottom:4px;">WHAT HAPPENED sentence.</div>
  <div style="font-size:13px; color:#333; margin-bottom:4px;">CONTEXT sentences.</div>
  <div style="font-size:13px; color:#333; margin-bottom:4px;"><em>What's next:</em> CONSEQUENCE sentence.</div>
  <div style="font-size:11px; margin-top:4px;"><a href="SOURCE_URL" style="color:#2563eb;">Source</a></div>
</div>

Precede each section with: <h2 style="font-size:20px; color:#111; border-bottom:2px solid #111; padding-bottom:6px;">SECTION NAME</h2>

Return ONLY the HTML. No markdown fences, no explanation, no preamble or closing remarks."""

USER_PROMPT = """Write today's ({date}) India news digest: Biotechnology and Politics, \
3 stories each, per the format and rules given."""


def get_news_html():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    today = datetime.now().strftime("%A, %B %d, %Y")

    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": USER_PROMPT.format(date=today)}],
    )

    text_parts = [block.text for block in response.content if block.type == "text"]
    html = "\n".join(text_parts).strip()

    # Strip accidental markdown fences just in case
    html = re.sub(r"^```html\s*|^```\s*|\s*```$", "", html.strip())

    return html


def build_email_html(news_html):
    today = datetime.now().strftime("%A, %B %d, %Y")
    return f"""
    <div style="font-family: -apple-system, Arial, sans-serif; max-width:640px; margin:0 auto;">
      <h1 style="font-size:22px; color:#111;">India Daily Digest — {today}</h1>
      {news_html}
    </div>
    """


def send_email(html_body):
    sender = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ["RECIPIENT_EMAIL"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Daily News Digest — {datetime.now().strftime('%b %d, %Y')}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())


def main():
    news_html = get_news_html()
    html_body = build_email_html(news_html)
    send_email(html_body)
    print("Digest sent successfully.")


if __name__ == "__main__":
    main()
