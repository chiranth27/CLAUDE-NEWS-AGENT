# Daily News Agent

Sources 3 news items each across 5 categories (Technology, Biotechnology, Finance,
Trade & Economics, Politics) for both Global and India news, using Claude + web_search.
Every item is written as Fact -> Context -> Consequence for a beginner reader.
Runs daily at 8:00 AM IST via GitHub Actions and emails the digest.

## Setup

1. **Push this repo to GitHub** (public or private, either works with Actions).

2. **Add repo secrets** - Settings → Secrets and variables → Actions → New repository secret:
   - `ANTHROPIC_API_KEY` - from console.anthropic.com
   - `GMAIL_ADDRESS` - the Gmail address sending the digest
   - `GMAIL_APP_PASSWORD` - 16-char app password (myaccount.google.com/apppasswords)
   - `RECIPIENT_EMAIL` - where the digest should be sent (can be the same Gmail address)

3. **Test it manually**: Go to the Actions tab → "Daily News Digest" workflow →
   "Run workflow" button. Check your inbox after ~1-2 minutes.

4. Once confirmed working, it will run automatically every day at 8:00 AM IST
   (2:30 AM UTC cron schedule).

## Local testing (optional, before pushing)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
export GMAIL_ADDRESS=you@gmail.com
export GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
export RECIPIENT_EMAIL=you@gmail.com
python news_agent.py
```

## Notes

- GitHub Actions free tier includes 2,000 minutes/month for private repos (unlimited
  for public repos) - this job takes ~1-2 minutes/day, well within limits.
- Anthropic API usage cost for one run is small (single call with web_search across
  10 topic buckets) - expect a few cents per day, check console.anthropic.com for pricing.
- GitHub Actions cron schedules can be delayed by a few minutes during high load -
  this is a GitHub-side limitation, not something in our control.
