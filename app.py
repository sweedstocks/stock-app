import os
import json
import time
import threading
from datetime import datetime

import requests
import yfinance as yf
from flask import Flask, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# ---------- Settings (from environment variables, set on Render) ----------
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
CHECK_MINUTES = int(os.environ.get("CHECK_MINUTES", "15"))

# ---------- Load watchlists ----------
def load_json(filename, default):
    try:
        with open(filename) as f:
            return json.load(f)
    except Exception:
        return default

WATCHLIST = load_json("watchlist.json", {})
NEWS_WATCHLIST = load_json("news_watchlist.json", {})
SECTOR_KEYWORDS = load_json("sector_keywords.json", {})

# ---------- In-memory state (shown on the phone page) ----------
STATE = {
    "last_checked": None,
    "prices": {},       # symbol -> {price, change_pct, status}
    "alerts": [],        # list of recent alert strings (newest first)
    "last_error": None,
}
SENT = set()  # remembers alerts already sent so you don't get repeats
STATE_LOCK = threading.Lock()


def send_push(title, message):
    """Send a push notification via ntfy.sh (free, no account needed)."""
    if not NTFY_TOPIC:
        print("[PUSH NOT CONFIGURED] would have sent:", title, message)
        return
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={"Title": title, "Priority": "high"},
            timeout=10,
        )
    except Exception as e:
        print("Push failed:", e)


def record_alert(text):
    with STATE_LOCK:
        STATE["alerts"].insert(0, {"time": datetime.now().strftime("%Y-%m-%d %H:%M"), "text": text})
        STATE["alerts"] = STATE["alerts"][:50]  # keep last 50


def check_prices():
    for symbol, rules in WATCHLIST.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if hist.empty or len(hist) < 2:
                continue
            prev_close = hist["Close"].iloc[-2]
            price = hist["Close"].iloc[-1]
            change_pct = ((price - prev_close) / prev_close) * 100

            status = "normal"
            buy_at = rules.get("buy_below_pct")
            sell_at = rules.get("sell_above_pct")

            today = datetime.now().strftime("%Y-%m-%d")
            if buy_at is not None and change_pct <= -abs(buy_at):
                status = "buy"
                key = (symbol, "buy", today)
                if key not in SENT:
                    SENT.add(key)
                    msg = f"{symbol} is down {change_pct:.2f}% — buy alert threshold hit (${price:.2f})"
                    send_push(f"BUY signal: {symbol}", msg)
                    record_alert(msg)
            elif sell_at is not None and change_pct >= abs(sell_at):
                status = "sell"
                key = (symbol, "sell", today)
                if key not in SENT:
                    SENT.add(key)
                    msg = f"{symbol} is up {change_pct:.2f}% — sell alert threshold hit (${price:.2f})"
                    send_push(f"SELL signal: {symbol}", msg)
                    record_alert(msg)

            with STATE_LOCK:
                STATE["prices"][symbol] = {
                    "price": round(float(price), 2),
                    "change_pct": round(float(change_pct), 2),
                    "status": status,
                }
        except Exception as e:
            print(f"Error checking {symbol}: {e}")
            with STATE_LOCK:
                STATE["last_error"] = f"{symbol}: {e}"


def check_news():
    # Simple headline scan using free Yahoo Finance news feed per symbol.
    keywords = set(k.lower() for k in NEWS_WATCHLIST.get("keywords", []))
    watch_trump = NEWS_WATCHLIST.get("watch_trump_mentions", True)
    if watch_trump:
        keywords.add("trump")

    for symbol in WATCHLIST.keys():
        try:
            ticker = yf.Ticker(symbol)
            news_items = ticker.news or []
            for item in news_items[:5]:
                raw_title = item.get("title") or (item.get("content") or {}).get("title") or ""
                title = raw_title.lower()
                hit = [kw for kw in keywords if kw in title]
                if hit and (symbol, raw_title) not in SENT:
                    SENT.add((symbol, raw_title))
                    msg = f"{symbol} news mentions '{hit[0]}': {raw_title}"
                    send_push(f"News alert: {symbol}", msg)
                    record_alert(msg)
        except Exception as e:
            print(f"Error checking news for {symbol}: {e}")


def run_check():
    print(f"[{datetime.now()}] Running check...")
    with STATE_LOCK:
        STATE["last_error"] = None
    try:
        check_prices()
        check_news()
        err = None
    except Exception as e:
        err = str(e)
        print("Check failed:", e)
    with STATE_LOCK:
        if err:
            STATE["last_error"] = err
        STATE["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- Scheduler: runs the check automatically, forever ----------
scheduler = BackgroundScheduler()
scheduler.add_job(run_check, "interval", minutes=CHECK_MINUTES, next_run_time=datetime.now())
scheduler.start()


# ---------- Web page (works great on phones, installable to home screen) ----------
PAGE = """
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Stock Alerts</title>
  <link rel="manifest" href="/manifest.json">
  <style>
    body { font-family: -apple-system, sans-serif; background: #111; color: #eee; margin: 0; padding: 16px; }
    h1 { font-size: 20px; }
    .card { background: #1c1c1e; border-radius: 12px; padding: 12px 16px; margin-bottom: 10px; }
    .buy { border-left: 4px solid #34c759; }
    .sell { border-left: 4px solid #ff3b30; }
    .normal { border-left: 4px solid #555; }
    .price { font-size: 22px; font-weight: bold; }
    .change-up { color: #34c759; }
    .change-down { color: #ff3b30; }
    .alert-item { font-size: 13px; padding: 6px 0; border-bottom: 1px solid #333; }
    .muted { color: #888; font-size: 12px; }
  </style>
</head>
<body>
  <h1>📈 Stock Alerts</h1>
  <p class="muted">Last checked: {{ last_checked or "not yet" }} — checks every {{ check_minutes }} min</p>

  {% if last_error %}<p class="muted">Problem: {{ last_error }}</p>{% endif %}
  {% for symbol, info in prices.items() %}
    <div class="card {{ info.status }}">
      <div>{{ symbol }}</div>
      <div class="price">${{ info.price }}
        <span class="{{ 'change-up' if info.change_pct >= 0 else 'change-down' }}">
          {{ "%.2f"|format(info.change_pct) }}%
        </span>
      </div>
    </div>
  {% else %}
    <p class="muted">No price data yet — first check runs shortly after startup.</p>
  {% endfor %}

  <h2>Recent alerts</h2>
  {% for a in alerts %}
    <div class="alert-item"><b>{{ a.time }}</b> — {{ a.text }}</div>
  {% else %}
    <p class="muted">No alerts yet.</p>
  {% endfor %}
</body>
</html>
"""

MANIFEST = {
    "name": "Stock Alerts",
    "short_name": "Stocks",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#111111",
    "theme_color": "#111111",
    "icons": []
}


@app.route("/")
def home():
    with STATE_LOCK:
        return render_template_string(
            PAGE,
            prices=STATE["prices"],
            alerts=STATE["alerts"],
            last_checked=STATE["last_checked"],
            last_error=STATE["last_error"],
            check_minutes=CHECK_MINUTES,
        )


@app.route("/manifest.json")
def manifest():
    return MANIFEST


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
