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

CATEGORIES = ["Biotechnology", "Politics"]
MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """Use web_search to find real news from the last 24-48 hours. \
For each item write: FACT (1 sentence, what happened), CONTEXT (1-2 sentences, background \
a beginner needs, plain language, no jargon), CONSEQUENCE (1 sentence, what happens next). \
Only real news you found via search. Return ONLY this JSON, no other text:

{"biotechnology": [{"headline":"...","fact":"...","context":"...","consequence":"...","source_url":"..."}], "politics": [...]}

Exactly 3 items per category."""

USER_PROMPT = """Top India Biotechnology and Politics news today ({date}). 3 items each. JSON only."""


def get_region_news(client, today):
    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": USER_PROMPT.format(date=today)}],
    )

    text_parts = [block.text for block in response.content if block.type == "text"]
    full_text = "\n".join(text_parts).strip()

    # Strip accidental markdown fences just in case
    full_text = re.sub(r"^```json\s*|\s*```$", "", full_text.strip())

    # If the model appended stray text after the JSON object, isolate the object itself
    start = full_text.find("{")
    end = full_text.rfind("}")
    if start != -1 and end != -1:
        full_text = full_text[start:end + 1]

    return json.loads(full_text)


def get_news():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    today = datetime.now().strftime("%A, %B %d, %Y")

    return {"india": get_region_news(client, today)}


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


def format_region_html(region_data):
    cat_labels = {
        "biotechnology": "Biotechnology",
        "politics": "Politics",
    }
    html = ""
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
    body += f'<h1 style="font-size:22px; color:#111;">India Daily Digest — {today}</h1>'
    body += format_region_html(news_json.get("india", {}))
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
