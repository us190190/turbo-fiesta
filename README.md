# Market 20/50 SMA Swing Trader

A Dockerised Python service that:
1. Checks market daily candles for a 20/50 SMA crossover (EOD, Mon–Fri)
2. Sends a WhatsApp message to you via Twilio with signal details + confirm/reject links
3. Places the order on Zerodha Kite Connect **only after you click Confirm**

---

## Project Structure

```
market-trader/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── app/
    ├── config.py           # all config from env vars
    ├── kite_client.py      # Kite connect session
    ├── market_data.py      # fetch market daily OHLCV
    ├── strategy.py         # 20/50 SMA crossover logic
    ├── notifier.py         # Twilio WhatsApp send
    ├── order_executor.py   # Kite place_order wrapper
    └── main.py             # FastAPI app + APScheduler
```

---

## Quick Start

### 1. Prerequisites
- Zerodha Kite Connect API subscription (₹2000/month)
- Twilio account with WhatsApp sandbox or approved sender

### 2. Configure
```bash
cp .env.example .env
# Fill in all values in .env
```

### 3. Daily Kite Login (access_token refresh)
Kite access tokens expire daily. You need to:
- Open `https://kite.trade/connect/login?api_key=YOUR_API_KEY`
- Login and grab the `request_token` from the redirect URL
- Exchange it:
  ```python
  from kiteconnect import KiteConnect
  kite = KiteConnect(api_key="YOUR_API_KEY")
  data = kite.generate_session("REQUEST_TOKEN", api_secret="YOUR_SECRET")
  print(data["access_token"])  # put this in .env as KITE_ACCESS_TOKEN
  ```
- Update `.env` and `docker compose up -d` to restart with the new token.

> 💡 This can be automated using a headless browser (Selenium/Playwright) + a morning cron job.

### 4. Run
```bash
docker compose up -d
```

### 5. Expose publicly (for WhatsApp links)
The confirmation links in the WhatsApp message must point to a publicly reachable URL.
Options:
- Deploy on a VPS (DigitalOcean, Hetzner, AWS EC2)
- Use ngrok for local testing: `ngrok http 8000` → set `APP_BASE_URL` to ngrok URL

---

## How the Signal Flow Works

```
15:35 IST (Mon–Fri)
      │
      ▼
fetch_daily_ohlcv()   ← Kite historical_data API
      │
      ▼
compute_signals()     ← 20-day SMA, 50-day SMA, crossover diff
      │
   signal?
    /   \
  YES    NO → done
   │
   ▼
send_whatsapp_confirmation()  ← Twilio → your WhatsApp
   │
   ▼
WhatsApp message with:
  ✅ /confirm?signal_id=...&token=...
  ❌ /reject?signal_id=...&token=...
   │
   ├─ You click ✅ → place_order() via Kite
   └─ You click ❌ → signal marked rejected, no order
```

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/confirm?signal_id=&token=` | Confirm and place order |
| GET | `/reject?signal_id=&token=` | Reject signal |
| GET | `/health` | Health check |

---

## Customisation

| What | Where |
|------|-------|
| Change SMA periods (e.g., 9/21) | `config.py` → `SMA_FAST`, `SMA_SLOW` |
| Change trade quantity | `config.py` → `TRADE_QUANTITY` |
| Switch CNC ↔ MIS (intraday) | `order_executor.py` → `product=` |
| Add stop-loss / trailing SL | `order_executor.py` → use `place_order` with `trigger_price` |
| Add more filters (RSI, 200 SMA) | `strategy.py` → `get_latest_signal()` |
| Change scheduling time | `main.py` → `scheduler.add_job(..., hour=, minute=)` |
| Persist pending signals across restarts | Replace `PENDING` dict with SQLite/Redis |

---

## Security Notes
- Never commit `.env` to git — add it to `.gitignore`
- Confirmation tokens are HMAC-SHA256 so they cannot be guessed
- Each signal can only be confirmed or rejected once (idempotent)
- Run behind HTTPS in production (use Caddy/nginx + Let's Encrypt)
