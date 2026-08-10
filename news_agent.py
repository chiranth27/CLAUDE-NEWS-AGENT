"""
Daily News Agent
- Calls Claude (with web_search) to source news across Global + India,
  5 categories each, 3 items per category.
- Formats each item as: Fact -> Context -> Consequence (beginner-friendly).
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

CATEGORIES = ["Technology", "Biotechnology", "Finance", "Trade & Economics", "Politics"]
REGIONS = ["Global", "India"]
MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """You are a news research agent. You will use the web_search tool to find \
recent, real news (from the last 24-48 hours) and produce a structured digest.

For EVERY news item, you must write it using this exact three-part framework, written so a \
complete beginner with no background knowledge can understand it:

1. FACT: What happened. One or two plain, concrete sentences. No jargon.
2. CONTEXT: The background needed to understand why this matters or how we got here. \
Explain any technical/political/financial terms in simple language.
3. CONSEQUENCE: What this means going forward - the likely impact or what to watch next.

Rules:
- Only include real, verifiable news you found via web_search. Never invent stories.
- Prioritize the most recent and most significant items.
- Keep each of Fact/Context/Consequence to 1-3 short sentences. No filler.
- Write for a "noob" - avoid unexplained acronyms and insider jargon.
- Return ONLY valid JSON, no markdown fences, no preamble, matching this schema exactly:

{
  "global": {
    "technology": [{"headline": "...", "fact": "...", "context": "...", "consequence": "...", "source_url": "..."}],
    "biotechnology": [...],
    "finance": [...],
    "trade_economics": [...],
    "politics": [...]
  },
  "india": {
    "technology": [...],
    "biotechnology": [...],
    "finance": [...],
    "trade_economics": [...],
    "politics": [...]
  }
}

Each category array must have exactly 3 items. "india" items must be India-specific news; \
"global" items should be the most important world news (can include any country, but avoid \
duplicating the India-specific stories)."""

USER_PROMPT = """Source today's top news for a daily digest. Search across all 10 buckets \
(2 regions x 5 categories), 3 items each. Today's date: {date}. Return only the JSON object \
per the schema."""


def get_news():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    today = datetime.now().strftime("%A, %B %d, %Y")

    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": USER_PROMPT.format(date=today)}],
    )

    # Concatenate all text blocks (final answer may follow tool_use/tool_result blocks)
    text_parts = [block.text for block in response.content if block.type == "text"]
    full_text = "\n".join(text_parts).strip()

    # Strip accidental markdown fences just in case
    full_text = re.sub(r"^```json\s*|\s*```$", "", full_text.strip())

    return json.loads(full_text)


def format_item_html(item):
    return f"""
    <div style="margin-bottom:16px; padding-bottom:16px; border-bottom:1px solid #e5e5e5;">
      <div style="font-weight:600; font-size:15px; color:#111; margin-bottom:6px;">{item['headline']}</div>
      <div style="font-size:13px; color:#333; margin-bottom:4px;"><strong>What happened:</strong> {item['fact']}</div>
      <div style="font-size:13px; color:#333; margin-bottom:4px;"><strong>Context:</strong> {item['context']}</div>
      <div style="font-size:13px; color:#333; margin-bottom:4px;"><strong>What to watch:</strong> {item['consequence']}</div>
      <div style="font-size:11px;"><a href="{item.get('source_url','#')}" style="color:#2563eb;">Source</a></div>
    </div>
    """


def format_region_html(region_name, region_data):
    cat_labels = {
        "technology": "Technology",
        "biotechnology": "Biotechnology",
        "finance": "Finance",
        "trade_economics": "Trade & Economics",
        "politics": "Politics",
    }
    html = f'<h2 style="font-size:20px; color:#111; margin-top:32px; border-bottom:2px solid #111; padding-bottom:6px;">{region_name}</h2>'
    for key, label in cat_labels.items():
        items = region_data.get(key, [])
        if not items:
            continue
        html += f'<h3 style="font-size:16px; color:#444; margin-top:20px;">{label}</h3>'
        for item in items:
            html += format_item_html(item)
    return html


def build_email_html(news_json):
    today = datetime.now().strftime("%A, %B %d, %Y")
    body = f'<div style="font-family: -apple-system, Arial, sans-serif; max-width:640px; margin:0 auto;">'
    body += f'<h1 style="font-size:22px; color:#111;">Daily Digest — {today}</h1>'
    body += format_region_html("Global", news_json.get("global", {}))
    body += format_region_html("India", news_json.get("india", {}))
    body += "</div>"
    return body


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
    news_json = get_news()
    html_body = build_email_html(news_json)
    send_email(html_body)
    print("Digest sent successfully.")


if __name__ == "__main__":
    main()