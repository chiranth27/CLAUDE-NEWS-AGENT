"""
Daily News Agent
- Calls Gemini (with built-in Google Search grounding) to source news across
  Global + India, 5 categories each (Technology, Biotechnology, Finance,
  Trade & Economics, Politics), 3 stories per category.
- Gemini writes the newspaper-style HTML directly (Fact -> Context -> Consequence per story).
- Emails the digest via Gmail SMTP.
"""

import os
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google import genai
from google.genai import types

# ---------- Config ----------

CATEGORIES = ["Technology", "Biotechnology", "Finance", "Trade & Economics", "Politics"]
REGIONS = ["Global", "India"]
MODEL = "gemini-flash-latest"

SYSTEM_PROMPT = """You are a newspaper editor. Use Google Search to find real news from the \
last 24-48 hours for ONE region at a time, across five sections: Technology, Biotechnology, \
Finance, Trade & Economics, and Politics (3 stories each).

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

Precede each of the 5 sections with: <h3 style="font-size:16px; color:#444; margin-top:20px;">SECTION NAME</h3>

Return ONLY the HTML. No markdown fences, no explanation, no preamble or closing remarks."""

USER_PROMPT = """Write today's ({date}) {region} news digest across all 5 categories \
(Technology, Biotechnology, Finance, Trade & Economics, Politics), 3 stories each, per the \
format and rules given. {region_note}"""

REGION_NOTES = {
    "Global": "Cover the most important world news across these categories (any country).",
    "India": "Cover India-specific news only across these categories.",
}


def get_region_html(client, region, today):
    response = client.models.generate_content(
        model=MODEL,
        contents=USER_PROMPT.format(date=today, region=region, region_note=REGION_NOTES[region]),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            max_output_tokens=4000,
        ),
    )

    html = (response.text or "").strip()

    # Strip accidental markdown fences just in case
    html = re.sub(r"^```html\s*|^```\s*|\s*```$", "", html)

    return html


def get_news_html():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    today = datetime.now().strftime("%A, %B %d, %Y")

    sections = []
    for region in REGIONS:
        region_html = get_region_html(client, region, today)
        sections.append(
            f'<h2 style="font-size:20px; color:#111; margin-top:32px; '
            f'border-bottom:2px solid #111; padding-bottom:6px;">{region}</h2>'
            f"{region_html}"
        )

    return "\n".join(sections)


def build_email_html(news_html):
    today = datetime.now().strftime("%A, %B %d, %Y")
    return f"""
    <div style="font-family: -apple-system, Arial, sans-serif; max-width:640px; margin:0 auto;">
      <h1 style="font-size:22px; color:#111;">Daily Digest — {today}</h1>
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
